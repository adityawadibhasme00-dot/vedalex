"""
Qdrant vector store for VEDALEX RAG pipeline.

Replaces FAISS with a production-grade vector database that supports:
  - Persistent storage with automatic indexing
  - Metadata filtering (source, jurisdiction, authority_level, patent_number)
  - Hybrid search (dense vectors + sparse/keyword)
  - Collection management and incremental updates
  - Multi-tenancy via payload filters

Collection schema:
  - Vectors: 1024-dim (BGE-M3) dense embeddings
  - Payload: source, category, doc_id, title, authority, jurisdiction,
            authority_level, section_heading, patent_number, publication_year,
            source_url, effective_date, chunk_index
"""

import os
import uuid
import numpy as np
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

QDRANT_URL_DEFAULT = "http://localhost:6333"
COLLECTION_NAME = "ipsakti_knowledge"


class QdrantVectorStore:
    """
    Production Qdrant vector store with hybrid search capability.
    """

    _instance: Optional["QdrantVectorStore"] = None
    _client = None
    _collection_ready = False
    _dim = 1024

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is not None:
            return
        self._init_client()

    def _init_client(self):
        from app.rag.embeddings import EmbeddingEngine
        self._dim = EmbeddingEngine.get_dim()

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import VectorParams, Distance

            url = os.environ.get("QDRANT_URL", QDRANT_URL_DEFAULT)
            api_key = os.environ.get("QDRANT_API_KEY", "")
            local_path = os.environ.get("QDRANT_LOCAL_PATH", "")

            # Priority: local path > remote URL > in-memory
            if local_path:
                self._client = QdrantClient(path=local_path, timeout=30)
                logger.info(f"Qdrant local mode: {local_path}")
            elif api_key:
                self._client = QdrantClient(url=url, api_key=api_key, timeout=30)
            else:
                # Try remote first, fall back to local storage
                try:
                    self._client = QdrantClient(url=url, timeout=5)
                    self._client.get_collections()  # health check
                except Exception:
                    fallback_path = os.path.join(
                        os.path.dirname(__file__), "qdrant_local_data"
                    )
                    self._client = QdrantClient(path=fallback_path, timeout=30)
                    logger.info(f"Qdrant remote unavailable — using local storage: {fallback_path}")

            self._ensure_collection()
            logger.info(f"Qdrant connected: {url} (collection={COLLECTION_NAME})")

        except Exception as e:
            logger.error(f"Qdrant connection failed: {e}")
            self._client = None

    def _ensure_collection(self):
        """Create collection if it doesn't exist (recreating if dim mismatch)."""
        from qdrant_client.models import VectorParams, Distance, PayloadSchemaType

        try:
            collections = self._client.get_collections()
            existing = {c.name for c in collections.collections}

            needs_recreate = False
            if COLLECTION_NAME in existing:
                # Verify existing collection dim matches engine dim (BGE-M3 <> fallback)
                try:
                    info = self._client.get_collection(COLLECTION_NAME)
                    actual_dim = getattr(info, "vectors_count", None)
                    if actual_dim is None:
                        from qdrant_client.models import VectorParams
                        params = getattr(info, "config", None) or {}
                        vparams = getattr(params, "params", None)
                        actual_dim = getattr(vparams, "size", None) if vparams else None
                    if actual_dim and actual_dim != self._dim:
                        logger.warning(
                            f"Collection dim {actual_dim} != engine dim {self._dim} — recreating"
                        )
                        needs_recreate = True
                except Exception as e:
                    logger.warning(f"Could not verify collection dim: {e}")

            if COLLECTION_NAME in existing and needs_recreate:
                self._client.delete_collection(COLLECTION_NAME)
                existing.discard(COLLECTION_NAME)
                logger.info(f"Deleted stale collection {COLLECTION_NAME} for dim {self._dim}")

            if COLLECTION_NAME not in existing:
                self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self._dim,
                        distance=Distance.COSINE,
                    ),
                    optimizers_config={
                        "indexing_threshold": 20000,
                    },
                )
                # Create payload indexes for metadata filtering
                for field, schema_type in [
                    ("category", PayloadSchemaType.KEYWORD),
                    ("authority", PayloadSchemaType.KEYWORD),
                    ("jurisdiction", PayloadSchemaType.KEYWORD),
                    ("authority_level", PayloadSchemaType.INTEGER),
                    ("patent_number", PayloadSchemaType.KEYWORD),
                    ("publication_year", PayloadSchemaType.INTEGER),
                    ("source", PayloadSchemaType.KEYWORD),
                    ("doc_id", PayloadSchemaType.KEYWORD),
                ]:
                    try:
                        self._client.create_payload_index(
                            collection_name=COLLECTION_NAME,
                            field_name=field,
                            field_schema=schema_type,
                        )
                    except Exception:
                        pass

                logger.info(f"Created collection: {COLLECTION_NAME} (dim={self._dim})")
            else:
                logger.info(f"Collection exists: {COLLECTION_NAME}")

            self._collection_ready = True

        except Exception as e:
            logger.error(f"Collection setup failed: {e}")
            self._collection_ready = False

    @classmethod
    def is_available(cls) -> bool:
        if cls._instance is None:
            cls()
        return (
            cls._instance is not None
            and cls._instance._client is not None
            and cls._instance._collection_ready
        )

    def upsert_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """
        Embed and upsert documents into Qdrant.
        Returns number of documents upserted.
        """
        if not self.is_available():
            logger.warning("Qdrant not available — skipping upsert")
            return 0

        from app.rag.embeddings import EmbeddingEngine
        engine = EmbeddingEngine()

        total_upserted = 0
        for batch_start in range(0, len(documents), batch_size):
            batch = documents[batch_start:batch_start + batch_size]
            texts = [doc.get("content", "") for doc in batch]

            if not texts:
                continue

            embeddings = engine.embed(texts)

            points = []
            for i, doc in enumerate(batch):
                point_id = str(uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{doc.get('source', '')}:{doc.get('doc_id', '')}:{doc.get('chunk_index', i)}"
                ))
                payload = {
                    "content": doc.get("content", "")[:4000],
                    "source": doc.get("source", ""),
                    "category": doc.get("category", ""),
                    "doc_id": doc.get("doc_id", ""),
                    "title": doc.get("title", ""),
                    "authority": doc.get("authority", ""),
                    "jurisdiction": doc.get("jurisdiction", ""),
                    "authority_level": int(doc.get("authority_level", 3)),
                    "section_heading": doc.get("section_heading", ""),
                    "patent_number": doc.get("patent_number", ""),
                    "publication_year": int(doc.get("publication_year", 0)) if doc.get("publication_year") else 0,
                    "source_url": doc.get("source_url", ""),
                    "effective_date": doc.get("effective_date", ""),
                    "chunk_index": int(doc.get("chunk_index", i)),
                    "content_preview": doc.get("content", "")[:200],
                    "omics_type": doc.get("omics_type", ""),
                    "organism": doc.get("organism", ""),
                    "compound": doc.get("compound", ""),
                    "gene": doc.get("gene", ""),
                    "protein": doc.get("protein", ""),
                    "uniprot_accession": doc.get("uniprot_accession", ""),
                    "ncbi_gene_id": doc.get("ncbi_gene_id", ""),
                    "pubchem_cid": doc.get("pubchem_cid", ""),
                    "pathway": doc.get("pathway", ""),
                    "pmid": doc.get("pmid", ""),
                }
                points.append(
                    {
                        "id": point_id,
                        "vector": embeddings[i].tolist(),
                        "payload": payload,
                    }
                )

            try:
                import qdrant_client
                from qdrant_client.models import PointStruct

                point_objects = []
                for p in points:
                    ps = PointStruct(
                        id=p["id"],
                        vector=p["vector"],
                        payload=p["payload"],
                    )
                    point_objects.append(ps)

                self._client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=point_objects,
                )
                total_upserted += len(points)
            except Exception as e:
                logger.error(f"Upsert batch failed: {e}")

        logger.info(f"Upserted {total_upserted} documents to Qdrant")
        return total_upserted

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search with optional metadata filtering.

        Args:
            query: User query string
            top_k: Number of results to return
            filters: Metadata filters, e.g. {"category": "patent", "jurisdiction": "India"}
            score_threshold: Minimum cosine similarity score

        Returns:
            List of matching documents with scores
        """
        if not self.is_available():
            return []

        from app.rag.embeddings import EmbeddingEngine
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

        engine = EmbeddingEngine()
        query_embedding = engine.embed_query(query)

        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if key == "authority_level" and isinstance(value, (int, float)):
                    conditions.append(
                        FieldCondition(key=key, range=Range(gte=value, lte=10))
                    )
                elif key == "publication_year" and isinstance(value, dict):
                    conditions.append(
                        FieldCondition(
                            key=key,
                            range=Range(
                                gte=value.get("gte", 0),
                                lte=value.get("lte", 9999),
                            ),
                        )
                    )
                else:
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
            if conditions:
                qdrant_filter = Filter(must=conditions)

        try:
            # qdrant-client >=1.10 uses query_points; older versions use search
            if hasattr(self._client, "query_points"):
                qres = self._client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=query_embedding[0].tolist(),
                    limit=top_k,
                    query_filter=qdrant_filter,
                    score_threshold=score_threshold,
                )
                results = qres.points if hasattr(qres, "points") else (qres or [])
            else:
                results = self._client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=query_embedding[0].tolist(),
                    limit=top_k,
                    query_filter=qdrant_filter,
                    score_threshold=score_threshold,
                )

            documents = []
            for hit in results:
                doc = hit.payload.copy()
                doc["score"] = hit.score
                doc["point_id"] = str(hit.id)
                documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Combined semantic + keyword search.
        Semantic results get score boost from keyword overlap.
        """
        semantic_results = self.search(query, top_k=top_k * 2, filters=filters)

        query_tokens = set(query.lower().split())
        for doc in semantic_results:
            content_tokens = set(doc.get("content", "").lower().split())
            keyword_overlap = len(query_tokens.intersection(content_tokens))
            doc["keyword_boost"] = keyword_overlap * 0.05
            doc["combined_score"] = doc.get("score", 0) + doc["keyword_boost"]

        semantic_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        return semantic_results[:top_k]

    def delete_by_source(self, source: str) -> int:
        """Delete all documents from a specific source."""
        if not self.is_available():
            return 0

        from qdrant_client.models import Filter, FieldCondition, MatchValue, PointIdsList

        try:
            results = self._client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[FieldCondition(key="source", match=MatchValue(value=source))]
                ),
                limit=10000,
            )
            points = [p.id for p in results[0]]
            if points:
                self._client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=PointIdsList(points=points),
                )
            return len(points)
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return 0

    def get_collection_stats(self) -> Dict[str, Any]:
        """Return collection statistics."""
        if not self.is_available():
            return {"status": "unavailable"}

        try:
            info = self._client.get_collection(COLLECTION_NAME)
            points_count = getattr(info, "points_count", 0)
            vectors_count = getattr(info, "vectors_count", points_count)
            status_str = getattr(info, "status", "unknown")
            optimizer = getattr(info, "optimizer_status", "unknown")
            actual_dim = self._dim
            try:
                cfg = getattr(info, "config", None) or {}
                params = getattr(cfg, "params", None)
                if params is not None:
                    d = getattr(params, "size", None)
                    if d:
                        actual_dim = d
            except Exception:
                pass
            return {
                "status": "available",
                "collection": COLLECTION_NAME,
                "total_points": points_count,
                "vectors_size": vectors_count,
                "status_str": str(status_str),
                "optimizer_status": str(optimizer),
                "config": {
                    "dim": actual_dim,
                    "distance": getattr(
                        getattr(getattr(info, "config", None) or {}, "params", None),
                        "distance",
                        "COSINE",
                    ),
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_all_documents(
        self,
        category: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Retrieve documents, optionally filtered by category."""
        if not self.is_available():
            return []

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        scroll_filter = None
        if category:
            scroll_filter = Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=category))]
            )

        try:
            points, _ = self._client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=scroll_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            return [p.payload for p in points]
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return []
