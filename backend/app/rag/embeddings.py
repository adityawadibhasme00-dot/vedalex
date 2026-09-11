"""
Multi-provider embedding engine for VEDALEX RAG pipeline.

Supports:
  1. BAAI/bge-m3 (open-source, multilingual, 1024-dim) — default
  2. OpenAI text-embedding-3-large (1536-dim, cloud) — fallback
  3. Hashing-fallback (192-dim) — last resort, never blocks startup

Why BGE-M3?
  - Supports 100+ languages (critical for Hindi/Marathi/Tamil/Sanskrit queries)
  - 1024-dim representation captures fine-grained Ayurveda terminology
  - Open-source, runs locally, no API costs
  - Produces both dense + sparse embeddings for hybrid search
"""

import os
import hashlib
import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Dimension constants
BGE_M3_DIM = 1024
OPENAI_3_LARGE_DIM = 1536
HASH_DIM = 192


class EmbeddingEngine:
    """
    Singleton embedding engine with provider fallback chain:
      BGE-M3 -> OpenAI -> Hashing
    """

    _instance: Optional["EmbeddingEngine"] = None
    _provider: str = "unknown"
    _dim: int = 0
    _model = None
    _openai_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_provider(cls) -> str:
        if cls._instance is None:
            cls()
        return cls._instance._provider if cls._instance else "unknown"

    @classmethod
    def get_dim(cls) -> int:
        if cls._instance is None:
            cls()
        return cls._instance._dim if cls._instance else 0

    def __init__(self):
        if self._provider != "unknown":
            return
        self._init_provider()

    def _init_provider(self):
        # Priority 1: BGE-M3 via sentence-transformers
        if os.environ.get("IPSAKTI_USE_BGE_M3", "1").lower() != "0":
            try:
                from sentence_transformers import SentenceTransformer
                model_name = os.environ.get("IPSAKTI_EMBEDDING_MODEL", "BAAI/bge-m3")
                logger.info(f"Loading embedding model: {model_name}")
                self._model = SentenceTransformer(model_name)
                self._provider = "bge-m3"
                self._dim = BGE_M3_DIM
                logger.info(f"Embedding engine ready: {self._provider} (dim={self._dim})")
                return
            except Exception as e:
                logger.warning(f"BGE-M3 load failed: {e}")

        # Priority 2: OpenAI text-embedding-3-large
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=api_key)
                self._provider = "openai-3-large"
                self._dim = OPENAI_3_LARGE_DIM
                logger.info(f"Embedding engine ready: {self._provider} (dim={self._dim})")
                return
            except Exception as e:
                logger.warning(f"OpenAI client init failed: {e}")

        # Priority 3: Hashing fallback (always works)
        self._provider = "hashing-fallback"
        self._dim = HASH_DIM
        logger.warning(
            "Using hashing-fallback embeddings — semantic quality degraded. "
            "Set IPSAKTI_USE_BGE_M3=1 or provide OPENAI_API_KEY for real embeddings."
        )

    def embed(self, texts: List[str]) -> np.ndarray:
        """Embed a batch of texts and return (N, dim) float32 array."""
        if self._provider == "bge-m3" and self._model is not None:
            return self._embed_bge(texts)
        elif self._provider == "openai-3-large" and self._openai_client is not None:
            return self._embed_openai(texts)
        else:
            return self._embed_hashing(texts)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string. Returns (1, dim) array."""
        return self.embed([query])

    def _embed_bge(self, texts: List[str]) -> np.ndarray:
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return np.array(embeddings, dtype=np.float32)

    def _embed_openai(self, texts: List[str]) -> np.ndarray:
        """OpenAI API has a batch limit of 2048 texts."""
        all_embeddings = []
        batch_size = 200
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self._openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        return np.array(all_embeddings, dtype=np.float32)

    def _hash_embedding(self, text: str) -> np.ndarray:
        """Deterministic hashing trick — Dimension-Space Bag of Words."""
        vec = np.zeros(HASH_DIM, dtype=np.float32)
        tokens = text.lower().split()
        if not tokens:
            return vec
        for tok in tokens:
            for gram in [tok, tok[:5]]:
                h = int(hashlib.md5(gram.encode()).hexdigest(), 16)
                idx = h % HASH_DIM
                sign = 1.0 if (h >> 4) % 2 == 0 else -1.0
                vec[idx] += sign
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def _embed_hashing(self, texts: List[str]) -> np.ndarray:
        return np.array([self._hash_embedding(t) for t in texts], dtype=np.float32)
