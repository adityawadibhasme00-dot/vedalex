"""Populate the vector index before the API starts serving.

Free-tier hosts hand out an ephemeral disk, so the Qdrant store is empty on
every cold start and a fresh clone has no index at all. This script makes the
index self-healing: it reindexes only when the store is missing or empty, and
it never blocks boot -- on any failure it warns and exits 0, because the API
degrades to an in-memory store rather than refusing to start.

Run it as a Render start-command prefix:

    python scripts/ensure_index.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import logging
import os
import sys
import time

# Default to the light path so the container never pulls the multi-GB model
# stack. Real env values (if the host sets them) win.
os.environ.setdefault("IPSAKTI_USE_BGE_M3", "0")
os.environ.setdefault("IPSAKTI_USE_RERANKER", "0")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ensure_index")

MIN_POINTS = 1


def _current_points() -> int:
    """Best-effort point count across the configured collections."""
    try:
        from app.rag.qdrant_store import QdrantVectorStore

        stats = QdrantVectorStore().get_collection_stats()
    except Exception as exc:  # noqa: BLE001 - never block boot on this
        log.warning("could not read collection stats (%s); assuming empty", exc)
        return 0

    if not isinstance(stats, dict) or stats.get("status") != "available":
        return 0

    # get_collection_stats() reports an aggregate "total_points" at the top
    # level, with a per-collection breakdown under "collections".
    total = stats.get("total_points")
    if isinstance(total, int):
        return total

    per_collection = stats.get("collections")
    if isinstance(per_collection, list):
        return sum(
            entry.get("total_points", 0)
            for entry in per_collection
            if isinstance(entry, dict)
        )
    return 0


def main() -> int:
    force = os.environ.get("IPSAKTI_FORCE_REINDEX", "").lower() in {"1", "true", "yes"}
    started = time.time()

    if not force:
        points = _current_points()
        if points >= MIN_POINTS:
            log.info("index already populated (%d points, %.1fs) - skipping reindex", points, time.time() - started)
            return 0
        log.info("index empty - rebuilding from the curated corpus")

    from app.rag.retrieval_pipeline import HybridRetriever

    stats = HybridRetriever.reindex_all()
    log.info(
        "reindexed %s docs into Qdrant (bm25=%s) in %.1fs",
        stats.get("total_documents"),
        stats.get("bm25_index_size"),
        time.time() - started,
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - boot must survive
        log.warning("index build failed (%s); starting anyway with a degraded store", exc)
        sys.exit(0)
