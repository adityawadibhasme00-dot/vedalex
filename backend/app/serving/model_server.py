"""Model-serving sidecar for BGE-M3 embeddings and the BGE cross-encoder.

Why this exists
---------------
``EmbeddingEngine`` and ``Reranker`` are process-level singletons that each load
multi-gigabyte models into the web process.  Every extra uvicorn worker, and
every extra backend replica, pays that memory again — which is the single
hardest wall on horizontal scale: 10 workers means 10 copies of the same
weights, serving 10 identical requests.

Moving the models into their own process fixes the economics:

  * **one** copy of the weights, shared by N web replicas;
  * the web tier becomes stateless, so it can be scaled on request count;
  * the model process can be given a GPU, more RAM, or a different host without
    touching application code;
  * the web replicas stay small enough to autoscale aggressively, since a scale-up
    no longer costs 4GB of warm weights and a slow first request.

The sidecar is intentionally a small FastAPI app rather than a dependency on a
specific inference runtime, so the same code path works locally (one process,
``IPSAKTI_MODEL_SERVER_URL`` unset, in-process fallback) and in production.

Endpoints
---------
``GET  /health``   readiness + which models are loaded
``POST /embed``    ``{"texts": [...]}`` -> normalised float32 vectors
``POST /rerank``   ``{"query": str, "documents": [...], "top_k": int}`` -> scores

The clients (``app/rag/embeddings.py``, ``app/rag/reranker.py``) call this
automatically when ``IPSAKTI_MODEL_SERVER_URL`` is set and fall back to
in-process models if the sidecar is unreachable, so a sidecar outage degrades
to the current single-process behaviour instead of failing requests.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=os.environ.get("IPSAKTI_LOG_LEVEL", "INFO"))
logger = logging.getLogger("ipsakti.model_server")

BGE_M3_DIM = 1024
DEFAULT_EMBED_MODEL = "BAAI/bge-m3"
DEFAULT_RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
MAX_BATCH = int(os.environ.get("IPSAKTI_MODEL_MAX_BATCH", "64"))


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    normalize: bool = True


class EmbedResponse(BaseModel):
    dim: int
    vectors: list[list[float]]
    model: str
    elapsed_ms: float


class RerankRequest(BaseModel):
    query: str
    documents: list[str] = Field(..., min_length=1)
    top_k: int = 10


class RerankResponse(BaseModel):
    scores: list[float]
    order: list[int]
    model: str
    elapsed_ms: float


class _Models:
    """Lazily-loaded model handles, shared by every request."""

    def __init__(self) -> None:
        self.embedder: Any = None
        self.embedder_name: str = ""
        self.reranker: Any = None
        self.reranker_name: str = ""
        self.device: str = os.environ.get("IPSAKTI_MODEL_DEVICE", "cpu")

    def load_embedder(self) -> None:
        if self.embedder is not None:
            return
        from sentence_transformers import SentenceTransformer

        name = os.environ.get("IPSAKTI_EMBEDDING_MODEL", DEFAULT_EMBED_MODEL)
        started = time.perf_counter()
        logger.info("loading embedding model %s on %s", name, self.device)
        self.embedder = SentenceTransformer(name, device=self.device)
        self.embedder_name = name
        logger.info(
            "embedding model ready in %.1fs", time.perf_counter() - started
        )

    def load_reranker(self) -> None:
        if self.reranker is not None:
            return
        if os.environ.get("IPSAKTI_USE_RERANKER", "1").lower() == "0":
            logger.info("reranker disabled via IPSAKTI_USE_RERANKER=0")
            return
        from sentence_transformers import CrossEncoder

        name = os.environ.get("IPSAKTI_RERANKER_MODEL", DEFAULT_RERANK_MODEL)
        started = time.perf_counter()
        logger.info("loading reranker model %s on %s", name, self.device)
        self.reranker = CrossEncoder(name, max_length=512, device=self.device)
        self.reranker_name = name
        logger.info("reranker model ready in %.1fs", time.perf_counter() - started)

    def status(self) -> dict[str, Any]:
        return {
            "embedder": self.embedder_name or None,
            "embedder_loaded": self.embedder is not None,
            "reranker": self.reranker_name or None,
            "reranker_loaded": self.reranker is not None,
            "device": self.device,
        }


MODELS = _Models()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Warm the models before serving so the first real request does not pay a
    # multi-second load, and so a broken model surfaces at startup rather than
    # as a user-facing timeout.
    try:
        MODELS.load_embedder()
    except Exception as exc:  # noqa: BLE001
        logger.error("embedding model failed to load: %s", exc)
    try:
        MODELS.load_reranker()
    except Exception as exc:  # noqa: BLE001
        logger.warning("reranker model failed to load: %s", exc)
    yield


app = FastAPI(
    title="IP-SAKTI Model Server",
    version="1.0.0",
    description=(
        "Holds BGE-M3 and the BGE cross-encoder so the web tier does not have to. "
        "Set IPSAKTI_MODEL_SERVER_URL on the backend to use it."
    ),
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", **MODELS.status()}


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    if MODELS.embedder is None:
        try:
            MODELS.load_embedder()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(503, f"embedding model unavailable: {exc}") from exc
    texts = req.texts[:MAX_BATCH]
    started = time.perf_counter()
    # torch releases the GIL inside encode(), so a plain def endpoint keeps the
    # event loop responsive while a batch is being encoded.
    vectors = MODELS.embedder.encode(
        texts,
        normalize_embeddings=req.normalize,
        show_progress_bar=False,
        batch_size=int(os.environ.get("IPSAKTI_EMBED_BATCH", "32")),
    )
    array = np.asarray(vectors, dtype=np.float32)
    return EmbedResponse(
        dim=int(array.shape[1]),
        vectors=array.tolist(),
        model=MODELS.embedder_name,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
    )


@app.post("/rerank", response_model=RerankResponse)
def rerank(req: RerankRequest) -> RerankResponse:
    if MODELS.reranker is None:
        raise HTTPException(503, "reranker model unavailable")
    started = time.perf_counter()
    pairs = [(req.query, doc[:512]) for doc in req.documents]
    scores = MODELS.reranker.predict(pairs, show_progress_bar=False)
    score_list = [float(s) for s in scores]
    order = sorted(range(len(score_list)), key=lambda i: score_list[i], reverse=True)
    return RerankResponse(
        scores=score_list,
        order=order[: max(1, req.top_k)],
        model=MODELS.reranker_name,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("IPSAKTI_MODEL_HOST", "0.0.0.0"),
        port=int(os.environ.get("IPSAKTI_MODEL_PORT", "8081")),
        workers=1,  # one process holds the weights; scale with replicas, not workers
    )
