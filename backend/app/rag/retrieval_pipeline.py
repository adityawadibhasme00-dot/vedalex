"""
Unified Hybrid Retrieval Pipeline for VEDALEX RAG.

Combines four retrieval strategies with cascading fallback:
  1. Qdrant semantic search (dense vector similarity)
  2. BM25 lexical search (keyword matching via rank_bm25)
  3. Metadata filtering (source, jurisdiction, authority, patent_number)
  4. BGE Reranker (cross-encoder re-scoring)

Pipeline flow:
  Query -> Embed -> Qdrant Search (top 20)
       -> BM25 Search (top 20)
       -> Merge + Deduplicate
       -> Metadata Filter
       -> Rerank (top 10 -> top 5)
       -> Hallucination Check
       -> Confidence Calculation
       -> Return Verified Context

This replaces both faiss_retriever.py and retrieval_engine.py with a single
production-grade module.
"""

import re
import os
import json
import glob
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# BM25 imports (graceful fallback)
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not installed — keyword search disabled")


class HybridRetriever:
    """
    Production-grade hybrid retrieval engine.
    """

    _instance: Optional["HybridRetriever"] = None
    _bm25_index = None
    _bm25_corpus: List[Dict[str, Any]] = []
    _bm25_tokenized: List[List[str]] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ------------------------------------------------------------------
    # BM25 Index Management
    # ------------------------------------------------------------------

    @classmethod
    def build_bm25_index(cls, documents: List[Dict[str, Any]]):
        """Build BM25 index from knowledge base documents."""
        if not BM25_AVAILABLE:
            logger.warning("BM25 unavailable — semantic-only mode")
            return

        corpus = []
        for doc in documents:
            content = doc.get("content", "")
            if not content.strip():
                continue
            tokens = re.findall(r'\w+', content.lower())
            corpus.append((tokens, doc))

        if not corpus:
            return

        tokenized = [c[0] for c in corpus]
        cls._bm25_index = BM25Okapi(tokenized)
        cls._bm25_corpus = [c[1] for c in corpus]
        cls._bm25_tokenized = tokenized
        logger.info(f"BM25 index built: {len(corpus)} documents")

    @classmethod
    def bm25_search(cls, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """Keyword search using BM25 scoring."""
        if cls._bm25_index is None:
            # Auto-build index from Qdrant if available (or KB files)
            try:
                from app.rag.qdrant_store import QdrantVectorStore
                store = QdrantVectorStore()
                docs = store.get_all_documents(limit=5000)
                if docs:
                    cls.build_bm25_index(docs)
            except Exception:
                try:
                    from app.rag.kb import collect_knowledge_documents
                    docs = collect_knowledge_documents()
                    if docs:
                        cls.build_bm25_index(docs)
                except Exception:
                    logger.warning("Could not auto-build BM25 index")
                    return []

        if cls._bm25_index is None:
            return []

        query_tokens = re.findall(r'\w+', query.lower())
        scores = cls._bm25_index.get_scores(query_tokens)

        scored_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )

        results = []
        for idx in scored_indices[:top_k]:
            if scores[idx] > 0:
                doc = cls._bm25_corpus[idx].copy()
                doc["bm25_score"] = float(scores[idx])
                doc["bm25_rank"] = len(results) + 1
                results.append(doc)

        return results

    # ------------------------------------------------------------------
    # Qdrant Search
    # ------------------------------------------------------------------

    @classmethod
    def qdrant_search(
        cls,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic search via Qdrant."""
        from app.rag.qdrant_store import QdrantVectorStore
        store = QdrantVectorStore()
        return store.hybrid_search(query, top_k=top_k, filters=filters)

    # ------------------------------------------------------------------
    # BM25 Keyword Search (legacy fallback via retrieval_engine)
    # ------------------------------------------------------------------

    @classmethod
    def statutory_search(
        cls,
        query: str,
        jurisdiction: Optional[str] = None,
        top_k: int = 6,
        min_score: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """Search statutory passages via the existing retrieval engine."""
        from app.services.retrieval_engine import HybridRetrievalEngine
        citations = HybridRetrievalEngine.search_passages(
            query, jurisdiction=jurisdiction, top_k=top_k, min_score=min_score
        )
        results = []
        for cit in citations:
            results.append({
                "content": cit.exact_passage[:1200],
                "source": cit.source_url or cit.act_title,
                "category": "statutory",
                "act_title": cit.act_title,
                "section_heading": cit.section_reference,
                "authority": cit.authority,
                "source_url": cit.source_url or "",
                "effective_date": cit.effective_date,
                "authority_level": cit.authority_rank,
                "title": cit.act_title,
            })
        return results

    # ------------------------------------------------------------------
    # Merge + Deduplicate
    # ------------------------------------------------------------------

    @classmethod
    def _merge_results(
        cls,
        semantic_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        statutory_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Merge results from all sources, deduplicate, and normalize scores."""
        seen = set()
        merged = []

        # Semantic results (highest priority)
        for i, doc in enumerate(semantic_results):
            key = (doc.get("doc_id", ""), doc.get("source", ""), doc.get("content", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            doc["retrieval_method"] = "semantic"
            doc["semantic_rank"] = i + 1
            doc["semantic_score"] = doc.get("score", 0)
            merged.append(doc)

        # BM25 results (complementary)
        for i, doc in enumerate(bm25_results):
            key = (doc.get("doc_id", ""), doc.get("source", ""), doc.get("content", "")[:80])
            if key in seen:
                # Boost existing entry
                for m in merged:
                    if (m.get("doc_id", "") == doc.get("doc_id", "") and
                            m.get("source", "") == doc.get("source", "")):
                        m["bm25_score"] = doc.get("bm25_score", 0)
                        m["bm25_rank"] = i + 1
                        m["retrieval_method"] = "hybrid"
                        break
                continue
            seen.add(key)
            doc["retrieval_method"] = "keyword"
            doc["bm25_rank"] = i + 1
            merged.append(doc)

        # Statutory results (authoritative override)
        for i, doc in enumerate(statutory_results):
            key = (doc.get("act_title", ""), doc.get("source", ""), doc.get("content", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            doc["retrieval_method"] = "statutory"
            doc["statutory_rank"] = i + 1
            merged.append(doc)

        # Compute combined score
        for doc in merged:
            semantic_s = doc.get("semantic_score", 0)
            bm25_s = doc.get("bm25_score", 0)
            authority = 1.0 / max(1, int(doc.get("authority_level", 3)))
            is_statutory = 1.5 if doc.get("retrieval_method") == "statutory" else 1.0

            doc["combined_score"] = (
                semantic_s * 0.45 +
                min(bm25_s / 10.0, 1.0) * 0.25 +
                authority * 0.20 +
                is_statutory * 0.10
            )

        merged.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        return merged

    # ------------------------------------------------------------------
    # Metadata Filtering
    # ------------------------------------------------------------------

    @classmethod
    def _apply_metadata_filters(
        cls,
        documents: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Filter documents by metadata fields."""
        if not filters:
            return documents

        filtered = []
        for doc in documents:
            match = True
            for key, value in filters.items():
                doc_val = doc.get(key, "")
                if isinstance(value, str) and value.lower() not in str(doc_val).lower():
                    match = False
                    break
                elif isinstance(value, (int, float)):
                    if int(doc_val) != value:
                        match = False
                        break
                elif isinstance(value, list):
                    if str(doc_val) not in value:
                        match = False
                        break
            if match:
                filtered.append(doc)

        return filtered

    # ------------------------------------------------------------------
    # Reranking
    # ------------------------------------------------------------------

    @classmethod
    def _rerank(
        cls,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Rerank documents using cross-encoder."""
        from app.rag.reranker import Reranker
        if not Reranker.is_available():
            # Passthrough: keep current ordering, attach a rank score.
            return [
                {**d, "rerank_score": d.get("score", 1.0 / (i + 1)), "original_rank": i}
                for i, d in enumerate(documents[:top_k])
            ]
        reranker = Reranker()
        return reranker.rerank(query, documents, top_k=top_k)

    # ------------------------------------------------------------------
    # Confidence Calculation
    # ------------------------------------------------------------------

    @classmethod
    def _compute_confidence(
        cls,
        query: str,
        sources: List[Dict[str, Any]],
        grounding: Dict[str, Any],
    ) -> float:
        """Compute confidence score based on retrieval quality signals."""
        if not sources:
            return 0.05

        coverage = grounding.get("coverage_ratio", 0)
        num_sources = len(sources)

        # Source authority signal
        authority_scores = []
        for s in sources:
            level = int(s.get("authority_level", 3))
            authority_scores.append(1.0 / max(1, level))
        avg_authority = sum(authority_scores) / len(authority_scores) if authority_scores else 0.25

        # Source diversity signal
        categories = set(s.get("category", "") for s in sources)
        diversity = min(1.0, len(categories) / 4.0)

        # Retrieval method signal
        has_statutory = any(s.get("retrieval_method") == "statutory" for s in sources)
        has_hybrid = any(s.get("retrieval_method") == "hybrid" for s in sources)

        # Reranker score signal
        rerank_scores = [s.get("rerank_score", 0.5) for s in sources]
        avg_rerank = sum(rerank_scores) / len(rerank_scores) if rerank_scores else 0.5

        # Composite confidence
        conf = (
            0.10 +                          # base
            coverage * 0.25 +               # grounding
            avg_authority * 0.20 +          # source quality
            diversity * 0.10 +              # source diversity
            min(1.0, num_sources / 5) * 0.10 +  # quantity
            avg_rerank * 0.10 +             # reranker agreement
            (0.05 if has_statutory else 0) +  # statutory bonus
            (0.05 if has_hybrid else 0)       # hybrid bonus
        )

        return round(max(0.05, min(0.97, conf)), 2)

    # ------------------------------------------------------------------
    # Main Retrieve Method
    # ------------------------------------------------------------------

    @classmethod
    def retrieve(
        cls,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        jurisdiction: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full hybrid retrieval pipeline.

        Returns:
            {
                "sources": [...],           # Final reranked sources
                "confidence": float,        # Confidence score
                "grounding": {...},         # Grounding check details
                "all_candidates": [...],    # Pre-rerank merged results
                "retrieval_stats": {...},   # Timing and count stats
            }
        """
        import time
        start = time.time()

        # Build metadata filters
        effective_filters = filters or {}
        if category:
            effective_filters["category"] = category
        if jurisdiction:
            effective_filters["jurisdiction"] = jurisdiction

        # Step 1: Qdrant semantic search
        semantic_results = cls.qdrant_search(query, top_k=20, filters=effective_filters)
        semantic_time = time.time() - start

        # Step 2: BM25 keyword search
        bm25_start = time.time()
        bm25_results = cls.bm25_search(query, top_k=20)
        bm25_time = time.time() - bm25_start

        # Step 3: Statutory search
        stat_start = time.time()
        statutory_results = cls.statutory_search(query, jurisdiction=jurisdiction, top_k=6)
        stat_time = time.time() - stat_start

        # Step 4: Merge + deduplicate
        merged = cls._merge_results(semantic_results, bm25_results, statutory_results)

        # Step 5: Apply metadata filters (for non-Qdrant results)
        if effective_filters:
            merged = cls._apply_metadata_filters(merged, effective_filters)

        # Step 6: Rerank
        # Cap the cross-encoder input to the top candidates by combined score.
        # The merged list can hold 40+ passages; feeding them all to the
        # CPU-bound BGE reranker adds tens of seconds for marginal gains.
        rerank_start = time.time()
        rerank_candidates = merged[:6]
        reranked = cls._rerank(query, rerank_candidates, top_k=top_k)
        rerank_time = time.time() - rerank_start

        # Step 7: Grounding check
        from app.rag.hallucination_guard import build_grounding_check
        grounding = build_grounding_check(query, reranked)

        # Step 8: Confidence
        confidence = cls._compute_confidence(query, reranked, grounding)

        # Step 9: Hallucination validation
        from app.rag.hallucination_guard import validate_answer, should_refuse_answer
        should_refuse, refusal_reason = should_refuse_answer(
            coverage=grounding["coverage_ratio"],
            confidence=confidence,
            num_sources=len(reranked),
        )

        total_time = time.time() - start

        return {
            "sources": reranked,
            "confidence": confidence,
            "grounding": grounding,
            "should_refuse": should_refuse,
            "refusal_reason": refusal_reason,
            "all_candidates": merged[:20],
            "retrieval_stats": {
                "semantic_results": len(semantic_results),
                "bm25_results": len(bm25_results),
                "statutory_results": len(statutory_results),
                "merged_count": len(merged),
                "final_count": len(reranked),
                "semantic_time_ms": round(semantic_time * 1000, 1),
                "bm25_time_ms": round(bm25_time * 1000, 1),
                "statutory_time_ms": round(stat_time * 1000, 1),
                "rerank_time_ms": round(rerank_time * 1000, 1),
                "total_time_ms": round(total_time * 1000, 1),
                "embedding_provider": _get_embedding_provider(),
                "reranker_available": _is_reranker_available(),
                "qdrant_available": _is_qdrant_available(),
            },
        }

    # ------------------------------------------------------------------
    # Index Management
    # ------------------------------------------------------------------

    @classmethod
    def reindex_all(cls) -> Dict[str, Any]:
        """Full reindex: load KB -> embed -> upsert to Qdrant."""
        import time
        start = time.time()

        from app.rag.kb import collect_knowledge_documents
        from app.rag.qdrant_store import QdrantVectorStore

        # Load all documents
        documents = collect_knowledge_documents()
        logger.info(f"Loaded {len(documents)} documents from knowledge base")

        # Build BM25 index
        cls.build_bm25_index(documents)

        # Upsert to Qdrant
        store = QdrantVectorStore()
        upserted = store.upsert_documents(documents)

        elapsed = time.time() - start
        stats = {
            "total_documents": len(documents),
            "upserted_to_qdrant": upserted,
            "bm25_index_size": len(cls._bm25_corpus),
            "elapsed_seconds": round(elapsed, 2),
        }
        logger.info(f"Reindex complete: {stats}")
        return stats

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Return current pipeline status."""
        from app.rag.qdrant_store import QdrantVectorStore
        qdrant_stats = QdrantVectorStore().get_collection_stats()

        bm25_size = len(cls._bm25_corpus) if cls._bm25_corpus else 0
        if bm25_size == 0 and qdrant_stats.get("total_points", 0) > 0:
            try:
                store = QdrantVectorStore()
                docs = store.get_all_documents(limit=5000)
                if docs:
                    cls.build_bm25_index(docs)
                    bm25_size = len(cls._bm25_corpus)
            except Exception:
                pass

        return {
            "qdrant": qdrant_stats,
            "bm25": {
                "available": BM25_AVAILABLE,
                "index_size": bm25_size,
            },
            "embedding": {
                "provider": _get_embedding_provider(),
                "dim": _get_embedding_dim(),
            },
            "reranker": {
                "available": _is_reranker_available(),
            },
        }


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _get_embedding_provider() -> str:
    try:
        from app.rag.embeddings import EmbeddingEngine
        return EmbeddingEngine.get_provider()
    except Exception:
        return "unknown"


def _get_embedding_dim() -> int:
    try:
        from app.rag.embeddings import EmbeddingEngine
        return EmbeddingEngine.get_dim()
    except Exception:
        return 0


def _is_reranker_available() -> bool:
    try:
        from app.rag.reranker import Reranker
        return Reranker.is_available()
    except Exception:
        return False


def _is_qdrant_available() -> bool:
    try:
        from app.rag.qdrant_store import QdrantVectorStore
        return QdrantVectorStore.is_available()
    except Exception:
        return False


def _warmup_rag_pipeline() -> None:
    """Preload BGE-M3 embeddings and build the BM25 index so the first
    /rag/* request responds without the model-loading penalty."""
    try:
        from app.rag.embeddings import EmbeddingEngine
        engine = EmbeddingEngine()
        warm_text = "VEDALEX IP-SAKTI knowledge base warm-up query"
        engine.embed([warm_text])
        import logging
        logging.getLogger(__name__).info(
            f"RAG warm-up: embeddings ready ({engine.get_provider()}, dim={engine.get_dim()})"
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"RAG warm-up embeddings failed: {e}")

    try:
        _ = HybridRetriever.get_status()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"RAG warm-up status/index failed: {e}")

    # Pre-touch the reranker so its (possibly failed) load attempt happens
    # in the background thread instead of on the first user request.
    try:
        from app.rag.reranker import Reranker
        Reranker.is_available()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"RAG warm-up reranker failed: {e}")
