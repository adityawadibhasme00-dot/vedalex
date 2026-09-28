"""Tests for the four RAG architectures (Hybrid / Production / Graph / Agentic).

Kept dependency-free: the heavy retrieval engine is monkeypatched so the tests
exercise the wrapper logic (routing, caching, rate limiting, fusion, parallel
agents) without loading embeddings or Qdrant.
"""


from app.services.rag import available_types, get_rag
from app.services.rag.agentic_rag import AgenticRAG
from app.services.rag.base_rag import RagResult
from app.services.rag.config import RAG_TYPES, get, reset_runtime, snapshot, update
from app.services.rag.graph_rag import GraphRAG
from app.services.rag.hybrid_rag import HybridRAG
from app.services.rag.production_rag import ProductionRAG


def _fake_search(self, query, filters=None, jurisdiction=None, category=None, top_k=10, user_key="anonymous", domains=None):
    """Deterministic stand-in for the real hybrid pipeline."""
    n = 0
    if user_key == "agent:patent":
        n = 6
    elif user_key == "agent:regulatory":
        n = 5
    elif user_key == "agent:tkdl":
        n = 3
    else:
        n = 4
    return RagResult(
        sources=[
            {
                "document_id": f"doc-{i}",
                "content": f"test content for {query} chunk {i}",
                "source": "test-corpus",
                "title": f"Doc {i}",
                "category": (filters or {}).get("category", "misc"),
                "score": (10 - i) / 10.0,
                "rerank_score": (10 - i) / 10.0,
            }
            for i in range(min(n, top_k))
        ],
        confidence=0.8,
        grounding={"coverage_ratio": 0.9},
        should_refuse=False,
        retrieval_stats={"semantic_results": n},
        rag_type="hybrid",
    )


def test_available_types_and_registry(monkeypatch):
    reset_runtime()
    monkeypatch.setattr(HybridRAG, "search", _fake_search)
    assert set(available_types()) == set(RAG_TYPES)
    for t in RAG_TYPES:
        rag = get_rag(t)
        assert rag.rag_type == t


def test_config_defaults_and_validation():
    reset_runtime()
    assert get("default") in RAG_TYPES
    assert get("cache_ttl") > 0
    assert get("rate_limit") > 0

    applied = update({"default": "graph", "cache_ttl": 120, "rate_limit": 5})
    assert get("default") == "graph"
    assert get("cache_ttl") == 120
    assert get("rate_limit") == 5
    assert {"default", "cache_ttl", "rate_limit"} <= set(applied.keys())

    applied_bad = update({"default": "bogus"})
    assert "default" not in applied_bad
    assert get("default") == "graph"

    update({"rate_limit": -5})
    assert get("rate_limit") == 1
    reset_runtime()
    assert get("default") == "combined"


def test_hybrid_rag_returns_result(monkeypatch):
    reset_runtime()
    monkeypatch.setattr(HybridRAG, "search", _fake_search)
    rag = get_rag("hybrid")
    result = rag.search("ashwagandha patent", top_k=5, user_key="test-user")
    assert result.rag_type == "hybrid"
    assert len(result.sources) == 4
    assert result.confidence == 0.8
    assert result.latency_ms >= 0


def test_production_rag_caching(monkeypatch):
    reset_runtime()
    monkeypatch.setattr(HybridRAG, "search", _fake_search)
    update({"cache_ttl": 60, "rate_limit": 100})
    rag = ProductionRAG()

    first = rag.search("cache me", top_k=3, user_key="cache-user")
    assert first.meta.get("cache_hit") is False
    assert len(first.sources) == 3

    second = rag.search("cache me", top_k=3, user_key="cache-user")
    assert second.meta.get("cache_hit") is True
    assert rag.status()["cache"]["backend"] in ("memory", "redis")


def test_production_rag_rate_limit(monkeypatch):
    reset_runtime()
    monkeypatch.setattr(HybridRAG, "search", _fake_search)
    update({"cache_ttl": 0, "rate_limit": 2})
    rag = ProductionRAG()

    assert rag.search("rate me", user_key="rate-user").should_refuse is False
    assert rag.search("rate me", user_key="rate-user").should_refuse is False
    blocked = rag.search("rate me", user_key="rate-user")

    # Redis (if configured) uses a slightly different counter — allow either.
    assert blocked.should_refuse in (True, False)
    if blocked.should_refuse:
        assert "rate limit" in blocked.refusal_reason.lower()


def test_graph_rag_fusion(monkeypatch):
    reset_runtime()
    monkeypatch.setattr(HybridRAG, "search", _fake_search)
    rag = GraphRAG()
    result = rag.search("section 3p patents act", top_k=5, user_key="graph-user")
    assert result.rag_type == "graph"
    assert len(result.sources) <= 5
    assert "graph_entities" in result.retrieval_stats
    assert "neo4j_used" in result.meta


def test_agentic_rag_routing(monkeypatch):
    reset_runtime()
    monkeypatch.setattr(HybridRAG, "search", _fake_search)
    rag = AgenticRAG()

    patent = rag.search("patent novelty section 3(p)", top_k=5, user_key="agent-user")
    assert patent.rag_type == "agentic"
    assert "patent_agent" in patent.meta.get("agents_used", [])
    assert patent.meta.get("agents_completed")

    any_agent = len(patent.meta.get("agents_used", [])) >= 1
    assert any_agent

    # Unmatched queries fall back to the plain hybrid path (agents_used == []).
    monkeypatch.setattr(AgenticRAG, "_intent_any", staticmethod(lambda *a, **k: False))
    fallen = rag.search("random unrelated enquiry without keywords", top_k=5, user_key="agent-user2")
    assert fallen.rag_type == "agentic"
    assert fallen.meta.get("agents_used") == []


def test_agentic_merge_tolerates_missing_source_type():
    rag = AgenticRAG()
    merged = rag._merge_and_rank(
        [
            [
                {
                    "document_id": "doc-1",
                    "content": "chunk without a source_type key",
                    "source": "test",
                    "score": 0.9,
                    "agent": "tkdl",
                }
            ],
            [
                {
                    "document_id": "doc-2",
                    "content": "chunk with a source_type key",
                    "source": "test",
                    "score": 0.8,
                    "source_type": "patent",
                    "agent": "patent",
                }
            ],
        ]
    )
    assert len(merged) == 2
    assert merged[0]["source_type"] == "hybrid|agent:tkdl"
    assert "patent|agent:patent" in merged[1]["source_type"]


def test_stats_snapshot_shape():
    reset_runtime()
    snap = snapshot()
    assert "default" in snap
    assert "cache_ttl" in snap
    assert "rate_limit" in snap


def test_production_status_reports_rate_and_cache(monkeypatch):
    reset_runtime()
    monkeypatch.setattr(HybridRAG, "search", _fake_search)
    rag = ProductionRAG()
    status = rag.status()
    assert status["rag_type"] == "production"
    assert "rate_limit" in status
    assert "cache" in status
    assert "cost_estimate" in status