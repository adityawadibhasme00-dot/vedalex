"""Jurisdiction toggle must reach the answer-generation layer.

The copilot toggle (🇮🇳 India / 🌍 International) is sent as ``jurisdiction`` on
the RAG request. It must be forwarded to the orchestrator as
``context.jurisdiction`` so the legal framework is decided BEFORE generation —
otherwise the router finds no signal and answers with a clarification instead
of the answer the user asked for.
"""

import asyncio

from app.api.v1 import rag_router
from app.services.jurisdiction_router import framework_mode_for, retrieval_filter_for
from app.services.rag import base_rag


def _run_route(monkeypatch, jurisdiction):
    """Call /rag/search with a stubbed RAG + orchestrator; return both captures."""
    captured: dict = {}

    class _FakeRag:
        rag_type = "hybrid"

        def search(self, query, filters=None, jurisdiction=None, category=None,
                   top_k=10, user_key="anonymous", domains=None):
            captured["retrieval_jurisdiction"] = jurisdiction
            return base_rag.RagResult(
                sources=[{"source": "India Code", "jurisdiction": "India",
                          "content": "Section 3(p) ..."}],
                confidence=0.6,
                rag_type="hybrid",
            )

    monkeypatch.setattr("app.services.rag.get_rag", lambda _t: _FakeRag())

    from app.services.multi_layer_orchestrator import MultiLayerOrchestrator

    def _fake_run(question, passport_id=None, context=None, retrieved_sources=None):
        captured["context"] = context
        return {"answer": "Answer under the selected framework."}

    monkeypatch.setattr(MultiLayerOrchestrator, "run", _fake_run)

    req = rag_router.UnifiedSearchRequest(
        query="Can I patent this Ayurvedic formulation?",
        jurisdiction=jurisdiction,
        rag_type="hybrid",
        answer=True,
    )
    resp = asyncio.run(rag_router.unified_rag_search(req, current_user=None))
    return resp, captured


def test_india_toggle_is_forwarded_as_framework_context(monkeypatch):
    resp, captured = _run_route(monkeypatch, "India")
    assert captured["context"] == {"jurisdiction": "India"}
    assert captured["retrieval_jurisdiction"] == "India"
    assert resp.answer == "Answer under the selected framework."


def test_international_toggle_is_forwarded_and_not_hard_filtered(monkeypatch):
    resp, captured = _run_route(monkeypatch, "International")
    assert captured["context"] == {"jurisdiction": "International"}
    # Whole-scope values retrieve unfiltered — the no-mixing gate drops the
    # other regime later, so DSHEA / NHPR evidence stays reachable.
    assert captured["retrieval_jurisdiction"] is None
    assert resp.answer == "Answer under the selected framework."


def test_no_jurisdiction_sends_no_context(monkeypatch):
    _, captured = _run_route(monkeypatch, None)
    assert captured["context"] is None
    assert captured["retrieval_jurisdiction"] is None


def test_framework_mode_maps_country_scopes_to_international():
    assert framework_mode_for("International") == "International"
    assert framework_mode_for("india") == "India"
    assert framework_mode_for("United States") == "International"
    assert framework_mode_for("Canada") == "International"
    assert framework_mode_for("Atlantis") is None
    assert framework_mode_for(None) is None


def test_retrieval_filter_only_drops_whole_scope_values():
    assert retrieval_filter_for("India") == "India"
    assert retrieval_filter_for("United States") == "United States"
    assert retrieval_filter_for("International") is None
    assert retrieval_filter_for("global") is None
    assert retrieval_filter_for("  ") is None
