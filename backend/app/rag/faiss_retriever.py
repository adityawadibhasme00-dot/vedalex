import os
import json
import pickle
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

class FAISSIndex:
    """
    Hybrid semantic index backed by FAISS.

    Uses BAAI/bge-base-en-v1.5 via sentence-transformers when available.
    Falls back to a deterministic hashing-based embedding when the model
    (or torch) is unavailable / too slow to load, so the RAG pipeline
    never blocks startup.
    """
    def __init__(self, index_dir: str = None):
        if index_dir is None:
            index_dir = os.path.join(os.path.dirname(__file__), "faiss_index")
        self.index_dir = index_dir
        self.index_path = os.path.join(index_dir, "index.faiss")
        self.metadata_path = os.path.join(index_dir, "metadata.pkl")
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        self.model = None
        self.model_loaded = False
        self._dim = 192
        self._vocab_size = 4096

    def _hash_embedding(self, text: str) -> np.ndarray:
        """Deterministic hashing trick embedding (Dimension-Space Bag of Words)."""
        vec = np.zeros(self._dim, dtype=np.float32)
        tokens = text.lower().split()
        if not tokens:
            return vec
        for tok in tokens:
            for gram in [tok, tok[:5]]:
                h = int(hashlib.md5(gram.encode()).hexdigest(), 16)
                idx = h % self._dim
                sign = 1.0 if (h >> 4) % 2 == 0 else -1.0
                vec[idx] += sign
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def _try_load_model(self) -> bool:
        """Attempt to load sentence-transformers; opt-in via env var to avoid slow torch import."""
        if self.model_loaded:
            return True
        if os.environ.get("IPSAKTI_USE_SENTENCE_TRANSFORMERS", "").lower() == "1":
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("BAAI/bge-base-en-v1.5")
                self.model_loaded = True
                self._dim = 768
                return True
            except Exception:
                self.model = None
        else:
            print("Using hashing-fallback embeddings (set IPSAKTI_USE_SENTENCE_TRANSFORMERS=1 to enable BGE model)")
            self.model = None
        return False

    def load_or_build(self, documents: List[Dict[str, Any]] = None):
        import faiss

        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.metadata_path, "rb") as f:
                    self.metadata = pickle.load(f)
                self._try_load_model()
                if self.model is not None and self.index.d != self._dim:
                    print(
                        f"WARNING: loaded index dim {self.index.d} != model dim {self._dim}; "
                        "queries will fall back to keyword ranking"
                    )
                print(f"Loaded FAISS index with {len(self.metadata)} documents")
                return
            except Exception as e:
                print(f"Error loading FAISS index: {e}")

        if documents:
            self.build(documents)

    def build(self, documents: List[Dict[str, Any]]):
        import faiss

        self.metadata = documents
        self._try_load_model()

        texts = [doc.get("content", "") for doc in documents]

        if self.model is not None:
            try:
                embeddings = self.model.encode(texts)
            except Exception:
                self.model = None
                self._dim = 192
                embeddings = self._encode_fallback(texts)
        else:
            embeddings = self._encode_fallback(texts)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype(np.float32))

        os.makedirs(self.index_dir, exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)

        print(f"Built FAISS index with {len(documents)} documents (dim={dimension}, model={'sentence-transformers' if self.model else 'hashing-fallback'})")

    def _encode_fallback(self, texts: List[str]) -> np.ndarray:
        return np.array([self._hash_embedding(t) for t in texts], dtype=np.float32)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        import faiss

        if self.index is None:
            if self.metadata:
                return self._keyword_rank(query, self.metadata, top_k)
            return []

        if self.model is not None:
            try:
                query_embedding = self.model.encode([query])
            except Exception:
                self.model = None
                self._reindex_fallback()
                query_embedding = self._encode_fallback([query])
        else:
            query_embedding = self._encode_fallback([query])

        try:
            distances, indices = self.index.search(query_embedding.astype(np.float32), top_k)
            results = []
            for idx in indices[0]:
                if 0 <= idx < len(self.metadata):
                    results.append(self.metadata[idx])
            if results:
                return results
        except Exception:
            pass

        return self._keyword_rank(query, self.metadata, top_k)

    def _reindex_fallback(self):
        """Recreate index with fallback embeddings if model was unloaded."""
        try:
            import faiss
            self._dim = 192
            embeddings = self._encode_fallback([doc.get("content", "") for doc in self.metadata])
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dim)
            self.index.add(embeddings.astype(np.float32))
        except Exception:
            self.index = None

    def _keyword_rank(self, query: str, docs: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        query_toks = set(query.lower().split())
        scored = []
        for doc in docs:
            content = (doc.get("content", "") + " " + doc.get("source", "")).lower()
            toks = set(content.split())
            overlap = len(query_toks.intersection(toks))
            scored.append((overlap, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for s, d in scored[:top_k] if s > 0] or docs[:top_k]