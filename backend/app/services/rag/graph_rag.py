"""Graph RAG — Hybrid RAG + knowledge-graph traversal.

Uses the built-in local knowledge graph (``app.rag.knowledge_graph``) which
links ingredients/botanicals/monographs/regulations/authorities. The pipeline:

  1. Extract entities named in the query (lexicon + corpus mentions)
  2. Traverse the graph for related entities/regulations
  3. Run the standard hybrid retrieval
  4. Fuse graph hits with hybrid hits (graph matches get a relevance boost)

Optionally, when ``NEO4J_URI`` is configured, an external Neo4j graph is ALSO
queried via Cypher and merged. Neo4j absence is never fatal — the local graph
fallback silently covers it.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.services.rag.base_rag import RagResult, _elapsed_ns, register
from app.services.rag.config import get as cfg_get
from app.services.rag.hybrid_rag import HybridRAG

logger = logging.getLogger(__name__)


@register
class GraphRAG(HybridRAG):
    rag_type = "graph"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._neo4j_driver: Any = None

    # ------------------------------------------------------------------
    # Entity extraction + local graph traversal
    # ------------------------------------------------------------------

    def _extract_entities(self, query: str) -> list[dict[str, Any]]:
        """Find knowledge-graph nodes whose name/alias appears in the query."""
        try:
            from app.rag.knowledge_graph import search_entities

            return search_entities(query, limit=8).get("matches", [])
        except Exception as exc:
            logger.debug("Entity extraction failed: %s", exc)
            return []

    def _local_graph_matches(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for ent in entities:
            node_type = ent.get("type", "entity")
            name = ent.get("name", "")
            if not name:
                continue
            matches.append({
                "document_id": f"graph:{node_type}:{name}",
                "title": name,
                "content": f"{node_type.replace('_', ' ').title()}: {name}",
                "source": "knowledge-graph",
                "source_type": "graph",
                "entity_type": node_type,
                "graph_relations": ent.get("edges", [])[:8],
                "final_score": 1.5,
            })
        return matches

    # ------------------------------------------------------------------
    # Optional Neo4j traversal
    # ------------------------------------------------------------------

    def _neo4j_client(self):
        uri = cfg_get("neo4j_uri") or ""
        if not uri or self._neo4j_driver is not None:
            return self._neo4j_driver
        try:
            from neo4j import GraphDatabase

            self._neo4j_driver = GraphDatabase.driver(
                uri, auth=(cfg_get("neo4j_user", "neo4j"), cfg_get("neo4j_password", ""))
            )
            self._neo4j_driver.verify_connectivity()
        except Exception as exc:
            logger.warning("Neo4j unavailable (%s) — local knowledge graph only", exc)
            self._neo4j_driver = None
        return self._neo4j_driver

    def _neo4j_query(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        driver = self._neo4j_client()
        if driver is None or not entities:
            return []
        names = [e.get("name", "") for e in entities if e.get("name")]
        cypher = (
            "MATCH (e:Entity) WHERE e.name IN $entities "
            "OPTIONAL MATCH (e)-[r]-(related:Entity) "
            "RETURN e.name AS source, type(r) AS relation, related.name AS target LIMIT 40"
        )
        try:
            with driver.session() as session:
                records = session.run(cypher, entities=names)
                rows = [{
                    "document_id": f"neo4j:{record['source']}",
                    "title": record["source"],
                    "content": f"{record['source']} {record['relation']} {record['target']}",
                    "source": "neo4j-graph",
                    "source_type": "graph",
                    "graph_relation": {
                        "from": record["source"],
                        "relation": record["relation"],
                        "to": record["target"],
                    },
                    "final_score": 1.5,
                } for record in records]
                return rows[:20]
        except Exception as exc:
            logger.warning("Neo4j query failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Fusion
    # ------------------------------------------------------------------

    def _combine(self, graph_hits: list[dict[str, Any]], hybrid: RagResult) -> list[dict[str, Any]]:
        seen: set = set()
        combined: list[dict[str, Any]] = []

        def _key(doc: dict[str, Any]) -> str:
            return doc.get("document_id") or doc.get("title", "") or doc.get("source", "")

        for g in graph_hits:
            k = _key(g)
            if k in seen:
                continue
            seen.add(k)
            combined.append(g)

        for h in hybrid.sources:
            k = _key(h)
            if k in seen:
                continue
            seen.add(k)
            combined.append({**h, "source_type": "hybrid"})

        def _sort_score(doc: dict[str, Any]) -> float:
            return float(doc.get("final_score", doc.get("rerank_score", doc.get("score", 0.0))) or 0.0)

        combined.sort(key=_sort_score, reverse=True)
        return combined[:20]

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        jurisdiction: str | None = None,
        category: str | None = None,
        top_k: int = 10,
        user_key: str = "anonymous",
        domains: list[str] | None = None,
    ) -> RagResult:
        start = time.perf_counter_ns()

        entities = self._extract_entities(query)
        graph_hits = self._local_graph_matches(entities)
        graph_hits += self._neo4j_query(entities)

        hybrid = super().search(query, filters, jurisdiction, category, top_k * 2, user_key, domains)
        combined = self._combine(graph_hits, hybrid)

        result = RagResult(
            sources=combined[:top_k],
            confidence=(hybrid.confidence if hybrid.sources else 0.05),
            grounding=hybrid.grounding,
            should_refuse=hybrid.should_refuse,
            refusal_reason=hybrid.refusal_reason,
            retrieval_stats={**hybrid.retrieval_stats, "graph_entities": len(entities), "graph_hits": len(graph_hits)},
            rag_type=self.rag_type,
            latency_ms=_elapsed_ns(start),
            meta={
                "architecture": "Hybrid + Knowledge Graph (local/Neo4j)",
                "entities": [e.get("name") for e in entities],
                "neo4j_used": self._neo4j_driver is not None,
            },
        )
        return result

    def status(self) -> dict[str, Any]:
        base = super().status()
        return {
            **base,
            "local_graph": "available",
            "neo4j": {
                "configured": bool(cfg_get("neo4j_uri")),
                "connected": self._neo4j_driver is not None,
            },
        }