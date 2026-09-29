"""Single-process entrypoint: build the vector index, then serve.

Why this exists instead of running ensure_index.py as a separate start-command
step: the embedded Qdrant client takes an exclusive lock on its storage folder.
A second process that has exited does not always release it, so a chained
``ensure_index.py && uvicorn ...`` made the API fall back to an in-memory store
("already accessed by another instance of Qdrant client"). Building the index
and running the server inside one process keeps a single client alive, so both
Qdrant and BM25 are genuinely available to requests.

The index is only built when the store is empty or missing, which on an
ephemeral free-tier disk means every cold start. Any failure here is logged and
ignored -- the API still starts, degraded to BM25 plus live-web retrieval.
"""

from __future__ import annotations

import logging
import os
import sys

os.environ.setdefault("IPSAKTI_USE_BGE_M3", "0")
os.environ.setdefault("IPSAKTI_USE_RERANKER", "0")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("serve")


def prepare_index() -> None:
    try:
        import ensure_index

        ensure_index.main()
    except Exception as exc:  # noqa: BLE001 - the server must still come up
        log.warning("index build skipped (%s); serving with a degraded store", exc)


def main() -> int:
    prepare_index()

    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
