"""Process-shared cache facade (Redis-backed, in-memory fallback).

Why
---
Several hot data structures in IP-SAKTI were plain module-level dicts:

  * ``rag/official_web_retriever.py``  - fetched page text, 6h TTL
  * ``rag/boolean_search.py``          - the whole searchable corpus
  * ``rag/semantic_entailment.py``     - evidence embedding vectors

A module-level dict is per-process.  With a single uvicorn worker that happens
to work, but the moment the backend is replicated each replica pays for its own
copy, re-fetches the same government pages, and answers rate-limit refusals or
stale pages after a restart.  Worse, the caches are invisible to the operator
because they live in the heap.

This module puts them behind one interface with two backends:

  * **Redis** when ``REDIS_URL`` is set and reachable — shared across replicas,
    survives restarts, visible via ``stats()``.
  * **In-process LRU** otherwise — identical semantics, single-replica scope, so
    local development and the offline demo keep working with no Redis at all.

Every operation degrades to the in-memory path if Redis errors, so a Redis
outage costs cache hit rate, never availability.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

KEY_PREFIX = "ipsk:cache"
REDIS_SOCKET_TIMEOUT = 1.0


def _redis_url() -> str:
    return (os.environ.get("REDIS_URL") or "").strip()


class _RedisHandle:
    """Lazily-connected, process-wide Redis client. Probed exactly once."""

    def __init__(self) -> None:
        self._client: Any = None
        self._checked = False
        self._lock = threading.Lock()

    def get(self) -> Any:
        if self._checked:
            return self._client
        with self._lock:
            if self._checked:
                return self._client
            self._checked = True
            url = _redis_url()
            if not url:
                return None
            try:
                import redis as _redis

                client = _redis.Redis.from_url(
                    url,
                    socket_connect_timeout=REDIS_SOCKET_TIMEOUT,
                    socket_timeout=REDIS_SOCKET_TIMEOUT,
                    decode_responses=True,
                )
                client.ping()
                self._client = client
                logger.info("Shared cache: using Redis at %s", url)
            except Exception as exc:  # noqa: BLE001 — cache must never be fatal
                logger.warning(
                    "Shared cache: Redis unavailable (%s) — in-memory only", exc
                )
                self._client = None
        return self._client


_REDIS = _RedisHandle()


class SharedCache:
    """Namespaced cache with TTL, JSON payloads and bounded in-memory size."""

    def __init__(self, namespace: str, default_ttl: float = 3600.0,
                 max_memory_entries: int = 512) -> None:
        self.namespace = namespace
        self.default_ttl = float(default_ttl)
        self.max_memory_entries = max_memory_entries
        self._mem: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.writes = 0

    # -- keys ---------------------------------------------------------------

    def _redis_key(self, key: str) -> str:
        return f"{KEY_PREFIX}:{self.namespace}:{key}"

    def _mem_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    @staticmethod
    def _jsonable(value: Any) -> Any:
        """Make ``value`` JSON-encodable without silently stringifying numbers.

        ``json.dumps(..., default=str)`` turns a NumPy vector into its ``repr``,
        so a value that works in one replica comes back from Redis as a *string*
        and every downstream float() on it raises.  Converting arrays to lists
        keeps the payload numerically identical on both sides of Redis.
        """
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        tolist = getattr(value, "tolist", None)  # ndarray, torch.Tensor
        if callable(tolist):
            return tolist()
        if isinstance(value, dict):
            return {k: SharedCache._jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [SharedCache._jsonable(v) for v in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value)

    @classmethod
    def _encode(cls, value: Any) -> str:
        return json.dumps(cls._jsonable(value))

    @staticmethod
    def _hash(payload: Any) -> str:
        raw = json.dumps(SharedCache._jsonable(payload), sort_keys=True,
                         default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def make_key(cls, *parts: Any) -> str:
        """Stable key from arbitrary parts, hashed to bound key length."""
        return cls._hash(list(parts))

    # -- reads / writes -----------------------------------------------------

    def get(self, key: str) -> Any | None:
        client = _REDIS.get()
        if client is not None:
            try:
                raw = client.get(self._redis_key(key))
                if raw is not None:
                    self.hits += 1
                    return json.loads(raw)
            except Exception:  # noqa: BLE001 — fall through to memory
                pass
        with self._lock:
            entry = self._mem.get(self._mem_key(key))
            if entry is None:
                self.misses += 1
                return None
            expires_at, value = entry
            if expires_at and expires_at < time.time():
                self._mem.pop(self._mem_key(key), None)
                self.misses += 1
                return None
            self._mem.move_to_end(self._mem_key(key))
            self.hits += 1
            return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> Any:
        effective_ttl = self.default_ttl if ttl is None else float(ttl)
        # Normalise once, then store the *same* shape in both backends.  Without
        # this, a NumPy vector is returned as an array on the memory path but as
        # a list on the Redis path, and callers behave differently depending on
        # whether Redis happens to be up.
        value = self._jsonable(value)
        client = _REDIS.get()
        if client is not None:
            try:
                payload = self._encode(value)
                if effective_ttl > 0:
                    client.setex(self._redis_key(key), int(effective_ttl), payload)
                else:
                    # ttl=0 means "no expiry", not "memory only".  Shared
                    # counters (e.g. the boolean-search corpus generation) rely
                    # on this: a replica that only wrote locally would keep
                    # answering from a stale index after another replica
                    # re-indexed the corpus.
                    client.set(self._redis_key(key), payload)
            except Exception:  # noqa: BLE001 — fall through to memory
                pass
        expires_at = time.time() + effective_ttl if effective_ttl > 0 else 0.0
        with self._lock:
            self._mem[self._mem_key(key)] = (expires_at, value)
            self._mem.move_to_end(self._mem_key(key))
            while len(self._mem) > self.max_memory_entries:
                self._mem.popitem(last=False)
            self.writes += 1
        return value

    def delete(self, key: str) -> None:
        client = _REDIS.get()
        if client is not None:
            try:
                client.delete(self._redis_key(key))
            except Exception:  # noqa: BLE001
                pass
        with self._lock:
            self._mem.pop(self._mem_key(key), None)

    def clear(self) -> None:
        client = _REDIS.get()
        if client is not None:
            try:
                for found in client.scan_iter(
                    match=f"{KEY_PREFIX}:{self.namespace}:*", count=500
                ):
                    client.delete(found)
            except Exception:  # noqa: BLE001
                pass
        with self._lock:
            self._mem.clear()

    def invalidate_prefix(self, prefix: str) -> int:
        """Drop every key starting with ``prefix``; returns keys removed.

        Used to invalidate a family of derived entries (e.g. all cached query
        results for one corpus generation) without tracking them one by one.
        """
        pattern = f"{self._redis_key(prefix)}*"
        removed = 0
        client = _REDIS.get()
        if client is not None:
            try:
                batch: list[str] = []
                for found in client.scan_iter(match=pattern, count=500):
                    batch.append(found)
                    if len(batch) >= 500:
                        removed += client.delete(*batch)
                        batch = []
                if batch:
                    removed += client.delete(*batch)
            except Exception:  # noqa: BLE001
                removed = 0
        needle = self._mem_key(prefix)
        with self._lock:
            stale = [k for k in self._mem if k.startswith(needle)]
            for key in stale:
                self._mem.pop(key, None)
            removed += len(stale)
        return removed

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    # -- introspection ------------------------------------------------------

    def backend(self) -> str:
        return "redis" if _REDIS.get() is not None else "memory"

    def stats(self) -> dict[str, Any]:
        total = self.hits + self.misses
        return {
            "namespace": self.namespace,
            "backend": self.backend(),
            "hits": self.hits,
            "misses": self.misses,
            "writes": self.writes,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
            "memory_entries": len(self._mem),
            "default_ttl_sec": self.default_ttl,
        }


_REGISTRY: dict[str, SharedCache] = {}
_REGISTRY_LOCK = threading.Lock()


def get_cache(namespace: str, default_ttl: float = 3600.0,
              max_memory_entries: int = 512) -> SharedCache:
    """Return the process-wide cache instance for ``namespace``."""
    with _REGISTRY_LOCK:
        cache = _REGISTRY.get(namespace)
        if cache is None:
            cache = SharedCache(namespace, default_ttl, max_memory_entries)
            _REGISTRY[namespace] = cache
        return cache


def all_stats() -> list[dict[str, Any]]:
    with _REGISTRY_LOCK:
        caches = list(_REGISTRY.values())
    return [c.stats() for c in caches]


def invalidate_prefix(namespace: str, prefix: str) -> int:
    """Invalidate ``prefix`` within ``namespace``. Module-level convenience."""
    return get_cache(namespace).invalidate_prefix(prefix)
