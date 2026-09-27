"""RAG runtime configuration for IP-SAKTI Sahayak.

Loads factory defaults from the environment and exposes a process-wide
``runtime`` dict that the ``/rag/configure`` endpoint can mutate at runtime.
Every RAG service reads values lazily through :func:`get` so configuration
changes take effect on the next request without a restart.
"""

from __future__ import annotations

import os
import threading
from typing import Any

RAG_TYPES: list[str] = ["hybrid", "production", "graph", "agentic"]

_ENV_TEMPLATE = {
    "default": "IPSAKTI_RAG_DEFAULT",
    "cache_ttl": "IPSAKTI_RAG_CACHE_TTL",
    "rate_limit": "IPSAKTI_RAG_RATE_LIMIT",
    "redis_url": "REDIS_URL",
    "neo4j_uri": "NEO4J_URI",
    "neo4j_user": "NEO4J_USER",
    "neo4j_password": "NEO4J_PASSWORD",
    "qdrant_url": "QDRANT_URL",
}

_DEFAULTS: dict[str, Any] = {
    "default": "hybrid",
    "cache_ttl": int(os.environ.get("IPSAKTI_RAG_CACHE_TTL", "3600")),
    "rate_limit": int(os.environ.get("IPSAKTI_RAG_RATE_LIMIT", "60")),
    "redis_url": os.environ.get("REDIS_URL", ""),
    "neo4j_uri": os.environ.get("NEO4J_URI", ""),
    "neo4j_user": os.environ.get("NEO4J_USER", "neo4j"),
    "neo4j_password": os.environ.get("NEO4J_PASSWORD", ""),
    "qdrant_url": os.environ.get("QDRANT_URL", "http://localhost:6333"),
    "rate_window_sec": 60,
    "user_key": "anonymous",
}

# Process-wide mutable configuration (updated by POST /rag/configure). Guarded
# by a lock; values fall back to the environment-derived defaults.
runtime: dict[str, Any] = dict(_DEFAULTS)
_runtime_lock = threading.Lock()


def get(key: str, default: Any = None) -> Any:
    """Read a runtime configuration value (thread-safe)."""
    with _runtime_lock:
        val = runtime.get(key, _DEFAULTS.get(key, default))
    if val is None and default is not None:
        return default
    return val


def update(values: dict[str, Any]) -> dict[str, Any]:
    """Apply a validated patch to the runtime config; returns the diff applied."""
    changed: dict[str, Any] = {}
    with _runtime_lock:
        for key, value in values.items():
            if key not in _DEFAULTS:
                continue
            if key == "default" and value not in RAG_TYPES and value != "auto":
                continue
            if key == "cache_ttl":
                value = max(0, min(86400, int(value)))
            if key == "rate_limit":
                value = max(1, min(10000, int(value)))
            if value != runtime.get(key):
                runtime[key] = value
                changed[key] = value
    return changed


def snapshot() -> dict[str, Any]:
    """Return a copy of the full runtime config (safe to serialize)."""
    with _runtime_lock:
        return dict(runtime)


def reset_runtime() -> None:
    """Restore all runtime values to their environment-derived defaults."""
    global runtime
    with _runtime_lock:
        runtime = dict(_DEFAULTS)