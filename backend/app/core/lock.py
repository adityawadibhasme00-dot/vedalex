"""Single-writer lock for scheduled background work.

The ingestion scheduler, the law-change sentinel and the corpus reindexer are
started from the FastAPI lifespan, so *every* backend replica runs them.  With
one replica that is a feature; with three it becomes three concurrent scrapers
hitting IP India, India Code and WIPO Patentscope — which is how a deployment
gets itself rate-limited or IP-blocked.  Once the statutory sources start
refusing traffic the Law Sentinel quietly stops detecting amendments, so the
failure is silent and it disables the feature that differentiates the product.

The schedule state file also lives on local disk, so replicas race on it.

This module provides the coordination primitive: one holder at a time, with a
lease that expires on its own so a crashed holder cannot wedge the schedule
forever.  Backed by Redis when available (correct across hosts), and by a
process-local file lock when not (still correct on a single host, which is the
single-replica default).
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from typing import Any

logger = logging.getLogger(__name__)

REDIS_LOCK_PREFIX = "ipsk:lock"


def _redis_client() -> Any:
    url = (os.environ.get("REDIS_URL") or "").strip()
    if not url:
        return None
    try:
        import redis as _redis

        client = _redis.Redis.from_url(
            url,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001 — locking must degrade, not fail
        logger.debug("Lock backend: Redis unavailable (%s)", exc)
        return None


def _lock_dir() -> str:
    path = os.environ.get("IPSAKTI_LOCK_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "locks",
    )
    os.makedirs(path, exist_ok=True)
    return path


def _holder_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def acquire(name: str, ttl: int = 900) -> bool:
    """Try to become the single holder of ``name`` for up to ``ttl`` seconds.

    Returns True when the lock was taken.  The lease is refreshed by the
    caller (see :func:`heartbeat`) for work that legitimately runs longer than
    ``ttl``.
    """
    holder = _holder_id()
    expires_at = time.time() + ttl
    payload = json.dumps({"holder": holder, "expires_at": expires_at})

    client = _redis_client()
    if client is not None:
        key = f"{REDIS_LOCK_PREFIX}:{name}"
        try:
            # SET NX EX is the atomic primitive: exactly one caller can win.
            return bool(client.set(key, payload, nx=True, ex=ttl))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Lock %r: Redis SET failed (%s), using file lock", name, exc)

    path = os.path.join(_lock_dir(), f"{name}.lock")
    try:
        # O_EXCL is the filesystem equivalent of SET NX.
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            with open(path, encoding="utf-8") as handle:
                current = json.load(handle)
            if float(current.get("expires_at", 0)) > time.time():
                return False
        except Exception:  # noqa: BLE001 — unreadable or half-written lock
            pass
        # Lease already expired: the previous holder is gone.  Reclaim it.
        try:
            os.unlink(path)
        except OSError:
            return False
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            return False
    except OSError as exc:
        logger.warning("Lock %r: cannot create lock file (%s)", name, exc)
        return True  # never block the schedule on a filesystem problem

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return True


def heartbeat(name: str, ttl: int = 900) -> None:
    """Extend the lease while long-running work is still in progress."""
    expires_at = time.time() + ttl
    payload = json.dumps({"holder": _holder_id(), "expires_at": expires_at})

    client = _redis_client()
    if client is not None:
        try:
            key = f"{REDIS_LOCK_PREFIX}:{name}"
            # Only extend a lease we still hold, so we cannot resurrect a lock
            # that already expired and was legitimately taken by another replica.
            current = client.get(key)
            if current and json.loads(current).get("holder") == _holder_id():
                client.set(key, payload, ex=ttl)
            return
        except Exception:  # noqa: BLE001
            return

    path = os.path.join(_lock_dir(), f"{name}.lock")
    try:
        with open(path, encoding="utf-8") as handle:
            current = json.load(handle)
        if current.get("holder") == _holder_id():
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(payload)
    except Exception:  # noqa: BLE001
        pass


def release(name: str) -> None:
    """Release the lock if — and only if — this process still holds it."""
    client = _redis_client()
    if client is not None:
        try:
            key = f"{REDIS_LOCK_PREFIX}:{name}"
            current = client.get(key)
            if current and json.loads(current).get("holder") == _holder_id():
                client.delete(key)
            return
        except Exception:  # noqa: BLE001
            return

    path = os.path.join(_lock_dir(), f"{name}.lock")
    try:
        with open(path, encoding="utf-8") as handle:
            current = json.load(handle)
        if current.get("holder") == _holder_id():
            os.unlink(path)
    except Exception:  # noqa: BLE001
        pass


def inspect(name: str) -> dict[str, Any]:
    """Current lock state, for the admin/status endpoints."""
    client = _redis_client()
    raw: str | None = None
    if client is not None:
        try:
            raw = client.get(f"{REDIS_LOCK_PREFIX}:{name}")
        except Exception:  # noqa: BLE001
            raw = None
    if raw is None:
        path = os.path.join(_lock_dir(), f"{name}.lock")
        try:
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
        except OSError:
            raw = None
    if not raw:
        return {"name": name, "held": False, "holder": None, "backend": "file"}
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        return {"name": name, "held": True, "holder": "unknown", "backend": "unknown"}
    return {
        "name": name,
        "held": float(data.get("expires_at", 0)) > time.time(),
        "holder": data.get("holder"),
        "expires_at": data.get("expires_at"),
        "backend": "redis" if client is not None else "file",
    }


class single_writer:
    """Context manager wrapper: acquire on enter, release on exit.

    ``ttl`` should exceed the expected work duration, and long jobs should call
    :func:`heartbeat` periodically.
    """

    def __init__(self, name: str, ttl: int = 900) -> None:
        self.name = name
        self.ttl = ttl
        self.acquired = False

    def __enter__(self) -> bool:
        self.acquired = acquire(self.name, self.ttl)
        if not self.acquired:
            logger.info(
                "Another replica holds the %r lock; skipping this cycle", self.name
            )
        return self.acquired

    def __exit__(self, *exc_info: Any) -> None:
        if self.acquired:
            release(self.name)
