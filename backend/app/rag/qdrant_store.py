"""
Qdrant vector store for VEDALEX RAG pipeline.

Replaces FAISS with a production-grade vector database that supports:
  - Persistent storage with automatic indexing
  - Metadata filtering (source, jurisdiction, authority_level, patent_number)
  - Hybrid search (dense vectors + sparse/keyword)
  - Collection management and incremental updates
  - Multi-tenancy via payload filters
  - Six curated domain collections (regulations, patents, biodiversity,
    traditional_knowledge, quality_standards, safety) with automatic
    category-to-collection routing at upsert time and cross-collection
    fan-out at search time.

Collection schema:
  - Vectors: 1024-dim (BGE-M3) dense embeddings
  - Payload: source, category, doc_id, title, authority, jurisdiction,
            authority_level, section_heading, patent_number, publication_year,
            source_url, effective_date, chunk_index, domain
"""

import logging
import os
import uuid
from typing import TYPE_CHECKING, Any, Optional, cast

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

QDRANT_URL_DEFAULT = "http://localhost:6333"
LEGACY_COLLECTION = "ipsakti_knowledge"

# Curated domain collections (IP-SAKTI knowledge domains). Every ingested chunk
# is routed to exactly one of these collections via ``resolve_collection``.
QDRANT_COLLECTIONS: list[str] = [
    "regulations",
    "patents",
    "biodiversity",
    "traditional_knowledge",
    "quality_standards",
    "safety",
]

# Source-id registry overrides win over category heuristics.
SOURCE_DOMAIN_OVERRIDES: list[tuple] = [
    ("tkdl", "traditional_knowledge"),
    ("wipo", "patents"),
    ("fda_us", "safety"),
    ("us_fda", "safety"),
    ("health_canada", "safety"),
    ("nba", "biodiversity"),
    ("pharmacopoeia", "quality_standards"),
    ("api", "quality_standards"),
]

# category / document_type / taxonomy -> collection routing table.
DOMAIN_BY_CATEGORY: dict[str, str] = {
    "regulatory": "regulations",
    "regulations": "regulations",
    "statutory": "regulations",
    "acts_and_gazettes": "regulations",
    "official": "regulations",
    "export_market_requirements": "regulations",
    "claim_alternatives": "regulations",
    "white_space": "regulations",
    "evidence_ladders": "regulations",
    "patent": "patents",
    "patents": "patents",
    "patent_statute": "regulations",
    "tkdl": "traditional_knowledge",
    "traditional_knowledge": "traditional_knowledge",
    "classical": "traditional_knowledge",
    "classical_texts": "traditional_knowledge",
    "ayurveda": "traditional_knowledge",
    "pharmacopoeia": "quality_standards",
    "api_monographs": "quality_standards",
    "api": "quality_standards",
    "biodiversity": "biodiversity",
    "abs": "biodiversity",
    "nba": "biodiversity",
    "safety": "safety",
    "who": "safety",
    "pubmed": "safety",
    "academic_research": "safety",
    "academic": "safety",
    "multiomics": "safety",
    "safety_signals": "safety",
}


def resolve_collection(doc: dict[str, Any]) -> str:
    """Route a document/payload to one of the six curated Qdrant collections."""
    source_id = str(doc.get("source_id") or doc.get("source") or "").lower()
    for token, domain in SOURCE_DOMAIN_OVERRIDES:
        if token in source_id:
            return domain

    fields = ("category", "document_type", "taxonomy")
    values = [str(doc.get(f) or "").lower().strip() for f in fields]
    for value in values:
        if value and value in DOMAIN_BY_CATEGORY:
            return DOMAIN_BY_CATEGORY[value]
    for value in values:
        if not value:
            continue
        for part, domain in DOMAIN_BY_CATEGORY.items():
            if part and part in value:
                return domain
    return "regulations"


def _extract_vector_dim(info) -> int | None:
    """Best-effort vector dimension extraction from a Qdrant collection info."""
    try:
        cfg = getattr(info, "config", None)
        params = getattr(cfg, "params", None)
        vectors = getattr(params, "vectors", None)
        if vectors is not None and hasattr(vectors, "size"):
            return vectors.size
        if isinstance(vectors, dict):
            first_v = next(iter(vectors.values()), None)
            if first_v is not None and hasattr(first_v, "size"):
                return first_v.size
        if params is not None and hasattr(params, "size"):
            return params.size
    except Exception:
        pass
    return None


class QdrantVectorStore:
    """
    Production Qdrant vector store with hybrid search capability.
    """

    _instance: Optional["QdrantVectorStore"] = None
    _client: "QdrantClient | None" = None
    _collection_ready = False
    _dim = 1024

    def _require_client(self) -> "QdrantClient":
        client = self._client
        if client is None:
            raise RuntimeError("Qdrant client is not initialised")
        return client

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
                    try:
                        self._client = QdrantClient(path=fallback_path, timeout=30)
                        logger.info(f"Qdrant remote unavailable — using local storage: {fallback_path}")
                    except Exception as e_local:
                        self._client = QdrantClient(":memory:")
                        logger.warning(f"Local Qdrant locked ({e_local}) — using in-memory mode")


            self._ensure_collections()
            logger.info(f"Qdrant connected: {url} (collections={', '.join(QDRANT_COLLECTIONS)})")

        except Exception as e:
            logger.error(f"Qdrant connection failed: {e}")
            self._client = None

    def _ensure_collections(self):
        """Create each of the six domain collections if it doesn't exist
        (recreating any whose vector dimension mismatches the engine)."""
        from qdrant_client.models import (
            Distance,
            OptimizersConfigDiff,
            PayloadSchemaType,
            VectorParams,
        )

        try:
            client = self._require_client()
            collections = client.get_collections()
            existing = {c.name for c in collections.collections}

            for collection_name in QDRANT_COLLECTIONS:
                needs_recreate = False
                if collection_name in existing:
                    try:
                        info = client.get_collection(collection_name)
                        actual_dim = _extract_vector_dim(info)
                        if actual_dim and actual_dim != self._dim:
                            logger.warning(
                                f"Collection {collection_name} dim {actual_dim} != engine dim {self._dim} — recreating"
                            )
                            needs_recreate = True
                    except Exception as e:
                        logger.warning(f"Could not verify collection dim {collection_name}: {e}")

                if collection_name in existing and needs_recreate:
                    client.delete_collection(collection_name)
                    existing.discard(collection_name)
                    logger.info(f"Deleted stale collection {collection_name} for dim {self._dim}")

                if collection_name not in existing:
                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=self._dim,
                            distance=Distance.COSINE,
                        ),
                        optimizers_config=OptimizersConfigDiff(
                            indexing_threshold=20000,
                        ),
                    )
                    logger.info(f"Created collection: {collection_name} (dim={self._dim})")

                # Index every collection, not just newly created ones. Fields
                # added later (e.g. provision_id for the cross-reference graph)
                # would otherwise never be indexed on a collection that already
                # existed, leaving those filters as full scans indefinitely.
                # create_payload_index is idempotent enough for our purposes:
                # "already exists" is swallowed below like any other error.
                for field, schema_type in [
                    ("category", PayloadSchemaType.KEYWORD),
                    ("domain", PayloadSchemaType.KEYWORD),
                    ("authority", PayloadSchemaType.KEYWORD),
                    ("jurisdiction", PayloadSchemaType.KEYWORD),
                    ("authority_level", PayloadSchemaType.INTEGER),
                    ("patent_number", PayloadSchemaType.KEYWORD),
                    ("publication_year", PayloadSchemaType.INTEGER),
                    ("source", PayloadSchemaType.KEYWORD),
                    ("doc_id", PayloadSchemaType.KEYWORD),
                    # Provision identity, so a retrieved chunk can be joined to
                    # the cross-reference graph in
                    # app/services/provision_graph.py. Absent on chunks indexed
                    # before this field existed; the resolver treats that as
                    # "no cross-references" rather than guessing.
                    ("provision_id", PayloadSchemaType.KEYWORD),
                    ("effective_from", PayloadSchemaType.KEYWORD),
                    ("effective_to", PayloadSchemaType.KEYWORD),
                ]:
                    try:
                        client.create_payload_index(
                            collection_name=collection_name,
                            field_name=field,
                            field_schema=schema_type,
                        )
                    except Exception:
                        pass

            # Preserve read access to a pre-existing single-schema collection
            # so previously indexed data is never silently lost.
            self._collection_ready = True

        except Exception as e:
            logger.error(f"Collection setup failed: {e}")
            self._collection_ready = False

    def _existing_collections(self, domains: list[str] | None = None) -> list[str]:
        """Collections to search/scroll — the six curated domains plus a
        legacy single-schema collection when present.

        When ``domains`` is given only those curated collections are returned.
        If none of the requested domains exist on disk the method falls back to
        every available collection so a warm table is never silently skipped.
        """
        try:
            client = self._require_client()
            collections = client.get_collections()
            existing = {c.name for c in collections.collections}
        except Exception:
            return list(QDRANT_COLLECTIONS)
        names = [c for c in QDRANT_COLLECTIONS if c in existing]
        if LEGACY_COLLECTION in existing and LEGACY_COLLECTION not in names:
            names.append(LEGACY_COLLECTION)
        if domains:
            wanted = [d for d in domains if d in names]
            if wanted:
                return wanted
        return names or list(QDRANT_COLLECTIONS)

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
        documents: list[dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """
        Embed and upsert documents into their domain Qdrant collections.
        Returns number of documents upserted.
        """
        if not self.is_available():
            logger.warning("Qdrant not available — skipping upsert")
            return 0

        from app.rag.embeddings import EmbeddingEngine
        engine = EmbeddingEngine()
        from qdrant_client.models import PointStruct

        total_upserted = 0
        for batch_start in range(0, len(documents), batch_size):
            batch = documents[batch_start:batch_start + batch_size]
            texts = [doc.get("content", "") for doc in batch]

            if not texts:
                continue

            embeddings = engine.embed(texts)

            points = []
            for i, doc in enumerate(batch):
                domain = resolve_collection(doc)
                point_id = str(uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{doc.get('source', '')}:{doc.get('doc_id', '')}:{doc.get('chunk_index', i)}"
                ))
                payload = {
                    "content": doc.get("content", "")[:4000],
                    "source": doc.get("source", ""),
                    "source_id": doc.get("source_id", "ingestion"),
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
                    # Provision cross-reference graph identity. Kept separate
                    # from effective_date because the graph models an
                    # applicability window (effective_from/effective_to) that a
                    # single date cannot express.
                    "provision_id": doc.get("provision_id", ""),
                    "effective_from": doc.get("effective_from", ""),
                    "effective_to": doc.get("effective_to", ""),
                    "citation_locator": doc.get("citation_locator", ""),
                    "verification_status": doc.get("verification_status", ""),
                    "chunk_index": int(doc.get("chunk_index", i)),
                    "content_preview": doc.get("content", "")[:200],
                    "domain": domain,
                    "access_mode": doc.get("access_mode", "public"),
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
                        "collection": domain,
                        "payload": payload,
                    }
                )

            grouped: dict[str, list[dict[str, Any]]] = {}
            for p in points:
                grouped.setdefault(p["collection"], []).append(p)

            for collection_name, group in grouped.items():
                try:
                    client = self._require_client()
                    point_objects = [
                        PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
                        for p in group
                    ]
                    client.upsert(
                        collection_name=collection_name,
                        points=point_objects,
                    )
                    total_upserted += len(point_objects)
                except Exception as e:
                    logger.error(f"Upsert batch to {collection_name} failed: {e}")

        logger.info(f"Upserted {total_upserted} documents to Qdrant domain collections")
        return total_upserted

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.3,
        domains: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search across domain collections with optional metadata filtering.

        Args:
            query: User query string
            top_k: Number of results to return
            filters: Metadata filters, e.g. {"category": "patent", "jurisdiction": "India"}
            score_threshold: Minimum cosine similarity score
            domains: Restrict search to these curated collections (intent-relevant
                collections only). None searches every available collection.

        Returns:
            List of matching documents with scores
        """
        if not self.is_available():
            return []

        from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

        from app.rag.embeddings import EmbeddingEngine

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
                qdrant_filter = Filter(must=cast(Any, conditions))

        try:
            client = self._require_client()
            documents = []
            results: list[Any]
            for collection_name in self._existing_collections(domains):
                # qdrant-client >=1.10 uses query_points; older versions use search
                if hasattr(client, "query_points"):
                    qres = client.query_points(
                        collection_name=collection_name,
                        query=query_embedding[0].tolist(),
                        limit=top_k,
                        query_filter=qdrant_filter,
                        score_threshold=score_threshold,
                    )
                    results = cast(
                        list[Any],
                        qres.points if hasattr(qres, "points") else (qres or []),
                    )
                else:
                    results = cast(Any, client).search(
                        collection_name=collection_name,
                        query_vector=query_embedding[0].tolist(),
                        limit=top_k,
                        query_filter=qdrant_filter,
                        score_threshold=score_threshold,
                    )

                for hit in results:
                    doc = hit.payload.copy()
                    doc["score"] = hit.score
                    doc["point_id"] = str(hit.id)
                    doc["collection"] = collection_name
                    documents.append(doc)

            seen = set()
            deduped = []
            for doc in documents:
                dedup_key = (doc.get("doc_id", ""), doc.get("content", "")[:80])
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                deduped.append(doc)

            deduped.sort(key=lambda x: x.get("score", 0), reverse=True)
            return deduped[:top_k]

        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        domains: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Combined semantic + keyword search.
        Semantic results get score boost from keyword overlap.
        """
        semantic_results = self.search(
            query, top_k=top_k * 2, filters=filters, domains=domains
        )

        query_tokens = set(query.lower().split())
        for doc in semantic_results:
            content_tokens = set(doc.get("content", "").lower().split())
            keyword_overlap = len(query_tokens.intersection(content_tokens))
            doc["keyword_boost"] = keyword_overlap * 0.05
            doc["combined_score"] = doc.get("score", 0) + doc["keyword_boost"]

        semantic_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        return semantic_results[:top_k]

    def delete_by_source(self, source: str) -> int:
        """Delete all documents from a specific source across all collections."""
        if not self.is_available():
            return 0

        from qdrant_client.models import FieldCondition, Filter, MatchValue, PointIdsList

        total_deleted = 0
        for collection_name in self._existing_collections():
            try:
                client = self._require_client()
                results = client.scroll(
                    collection_name=collection_name,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="source", match=MatchValue(value=source))]
                    ),
                    limit=10000,
                )
                points = [p.id for p in results[0]]
                if points:
                    client.delete(
                        collection_name=collection_name,
                        points_selector=PointIdsList(points=points),
                    )
                total_deleted += len(points)
            except Exception as e:
                logger.error(f"Delete failed in {collection_name}: {e}")
        return total_deleted

    def get_collection_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across all domain collections."""
        if not self.is_available():
            return {"status": "unavailable"}

        try:
            client = self._require_client()
            total_points = 0
            status_str = "unknown"
            per_collection = []
            for name in self._existing_collections():
                try:
                    info = client.get_collection(name)
                    points_count = getattr(info, "points_count", 0) or 0
                    total_points += points_count
                    status_str = getattr(info, "status", "unknown")
                    per_collection.append({
                        "collection": name,
                        "total_points": points_count,
                        "status": str(status_str),
                    })
                except Exception as e:
                    per_collection.append({"collection": name, "total_points": 0, "status": "error", "error": str(e)})
            return {
                "status": "available",
                "collection": LEGACY_COLLECTION,
                "collections": per_collection,
                "total_points": total_points,
                "vectors_size": total_points,
                "status_str": str(status_str),
                "optimizer_status": "n/a",
                "config": {
                    "dim": self._dim,
                    "distance": "COSINE",
                    "domains": QDRANT_COLLECTIONS,
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_all_documents(
        self,
        category: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Retrieve documents across all collections, optionally filtered by category."""
        if not self.is_available():
            return []

        from qdrant_client.models import FieldCondition, Filter, MatchValue

        scroll_filter = None
        if category:
            scroll_filter = Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=category))]
            )

        try:
            client = self._require_client()
            all_payloads = []
            for collection_name in self._existing_collections():
                points, _ = client.scroll(
                    collection_name=collection_name,
                    scroll_filter=scroll_filter,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False,
                )
                for p in points:
                    payload = p.payload
                    if payload is None:
                        continue
                    payload["collection"] = collection_name
                    all_payloads.append(payload)

            seen = set()
            deduped = []
            for payload in all_payloads:
                key = payload.get("doc_id", payload.get("id", ""))
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(payload)
            return deduped[:limit]
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return []
