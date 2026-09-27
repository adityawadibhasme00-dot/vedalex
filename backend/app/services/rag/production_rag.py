"""Production RAG — Hybrid RAG + production hardening.

Adds on top of :class:`HybridRAG`:
  1. Result caching (Redis when ``REDIS_URL`` is set, in-memory TTL fallback)
  2. Per-user rate limiting (sliding window, Redis or in-memory fallback)
  3. Query logging with latency + estimated token cost
  4. Monitoring counters exposed via ``/rag/search/stats``

Everything is intercepted with graceful fallbacks — if Redis is unreachable or
uninstalled the service degrades to in-memory behaviour and never raises.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any

from app.services.rag.base_rag import RagResult, _elapsed_ns, register
from app.services.rag.config import get as cfg_get
from app.services.rag.hybrid_rag import HybridRAG

logger = logging.getLogger(__name__)

# Truncation window for cache payloads (keep metrics lean).
_CACHE_PAYLOAD_BUDGET = 4000

MemEntry = dict[str, Any]
RateEntry = dict[str, Any]


@register
class ProductionRAG(HybridRAG):
    rag_type = "production"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._redis: Any = None
        self._redis_checked = False
        self._mem_cache: dict[str, MemEntry] = {}
        self._mem_hits = 0
        self._mem_misses = 0
        self._rate: dict[str, RateEntry] = {}
        self._lock = threading.Lock()
        self.query_log: list[dict[str, Any]] = []
        self._log_lock = threading.Lock()
        self.cost_estimate: dict[str, float] = {"estimated_tokens": 0.0, "estimated_usd": 0.0}

    # ------------------------------------------------------------------
    # Redis (optional, lazy)
    # ------------------------------------------------------------------

    def _redis_client(self):
        url = cfg_get("redis_url") or (self.config or {}).get("redis_url", "")
        if self._redis is None and not self._redis_checked:
            self._redis_checked = True
            if url:
                try:
                    import redis as _redis

                    self._redis = _redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
                    self._redis.ping()
                except Exception as exc:
                    logger.warning("Redis unavailable (%s) — using in-memory fallbacks", exc)
                    self._redis = None
        return self._redis

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _check_rate_limit(self, user_key: str) -> bool:
        limit = int(cfg_get("rate_limit", 60))
        window = int(cfg_get("rate_window_sec", 60))
        client = self._redis_client()
        if client is not None:
            if limit <= 0:
                return True
            key = f"ipsk:rate:{user_key}"
            try:
                now: float = int(time.time())
                pipe = client.pipeline()
                pipe.zremrangebyscore(key, 0, now - window)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, window + 5)
                _results = pipe.execute()
                count = int(_results[1])
                return count <= limit
            except Exception:
                # Redis hiccup — fall through to the in-memory guard below.
                pass

        with self._lock:
            now = time.monotonic()
            entry = self._rate.setdefault(user_key, {"count": 0, "window_start": now})
            if now - entry["window_start"] >= window:
                entry["count"] = 0
                entry["window_start"] = now
            entry["count"] += 1
            return entry["count"] <= limit

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _cache_key(self, query: str, filters: dict[str, Any] | None) -> str:
        parts = [query or "", json.dumps(filters or {}, sort_keys=True, default=str)]
        return hashlib.md5("|".join(parts).encode()).hexdigest()

    def _cache_get(self, key: str) -> RagResult | None:
        client = self._redis_client()
        if client is not None:
            try:
                raw = client.get(f"ipsk:cache:{key}")
                if raw:
                    payload = json.loads(raw)
                    return RagResult(
                        sources=payload.get("sources", []),
                        confidence=payload.get("confidence", 0.05),
                        grounding=payload.get("grounding", {}),
                        should_refuse=payload.get("should_refuse", False),
                        refusal_reason=payload.get("refusal_reason", ""),
                        retrieval_stats=payload.get("retrieval_stats", {}),
                        rag_type=self.rag_type,
                        latency_ms=float(payload.get("latency_ms", 0.0)),
                        meta={"cache_hit": True, **payload.get("meta", {})},
                    )
            except Exception:
                pass
        with self._lock:
            entry = self._mem_cache.get(key)
            if entry and entry["expires"] > time.monotonic():
                self._mem_hits += 1
                return entry["result"]
        self._mem_misses += 1
        return None

    def _cache_set(self, key: str, result: RagResult) -> None:
        ttl = int(cfg_get("cache_ttl", 3600))
        payload = result.to_dict()
        for src in payload.get("sources", []):
            if isinstance(src, dict) and len(json.dumps(src, default=str)) > _CACHE_PAYLOAD_BUDGET:
                limited = {k: (v if k not in ("content", "exact_passage") else str(v)[:1200]) for k, v in src.items()}
                src.clear()
                src.update(limited)
        client = self._redis_client()
        if client is not None and ttl > 0:
            try:
                client.setex(f"ipsk:cache:{key}", ttl, json.dumps(payload, default=str))
            except Exception:
                pass
        if ttl > 0:
            with self._lock:
                self._mem_cache[key] = {"expires": time.monotonic() + ttl, "result": result}

    # ------------------------------------------------------------------
    # Cost tracking
    # ------------------------------------------------------------------

    def _estimate_cost(self, query: str, result: RagResult) -> dict[str, float]:
        query_tokens = max(1, len(query.split()))
        source_tokens = sum(max(1, len(str(s.get("content", ""))[:1200].split())) for s in result.sources)
        total_tokens = query_tokens + source_tokens
        embedding_tokens = total_tokens
        estimated_usd = embedding_tokens * 0.00013 / 1_000_000 + total_tokens * 0.00001
        return {"estimated_tokens": float(total_tokens), "estimated_usd": float(estimated_usd)}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        jurisdiction: str | None = None,
        category: str | None = None,
        top_k: int = 10,
        user_key: str = "anonymous",
        domains: list[str] | None = None,
    ) -> RagResult:
        start = time.perf_counter_ns()

        if not self._check_rate_limit(user_key):
            return RagResult(
                rag_type=self.rag_type,
                latency_ms=_elapsed_ns(start),
                should_refuse=True,
                refusal_reason="Rate limit exceeded. Please try again shortly.",
                meta={"rate_limited": True, "user_key": user_key},
            )

        cache_key = self._cache_key(query, filters)
        cached = self._cache_get(cache_key)
        if cached is not None:
            cached.latency_ms = _elapsed_ns(start)
            cached.meta["cache_hit"] = True
            cached.meta["cache_source"] = "redis" if self._redis is not None else "memory"
            self._record_log(query, user_key, cached, start, cached=True)
            return cached

        result = super().search(query, filters, jurisdiction, category, top_k, user_key, domains)
        result.meta["cache_hit"] = False

        if result.sources and not result.should_refuse:
            self._cache_set(cache_key, result)

        cost = self._estimate_cost(query, result)
        self.cost_estimate = cost
        result.meta["cost"] = cost

        self._record_log(query, user_key, result, start, cached=False)
        return result

    def _record_log(
        self, query: str, user_key: str, result: RagResult, start_ns: int, cached: bool
    ) -> None:
        latency = _elapsed_ns(start_ns)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "user_key": user_key,
            "query": query[:200],
            "rag_type": self.rag_type,
            "sources": len(result.sources),
            "cached": cached,
            "latency_ms": round(latency, 2),
            "confidence": result.confidence,
            "cost": result.meta.get("cost", {}),
        }
        with self._log_lock:
            self.query_log.append(entry)
            if len(self.query_log) > 500:
                self.query_log = self.query_log[-500:]

    def status(self) -> dict[str, Any]:
        base = super().status()
        return {
            **base,
            "cache": {
                "enabled": int(cfg_get("cache_ttl", 3600)) > 0,
                "backend": "redis" if self._redis is not None else "memory",
                "memory_hits": self._mem_hits,
                "memory_misses": self._mem_misses,
            },
            "rate_limit": {
                "per_minute": int(cfg_get("rate_limit", 60)),
                "window_sec": int(cfg_get("rate_window_sec", 60)),
            },
            "cost_estimate": self.cost_estimate,
            "logged_queries": len(self.query_log),
        }