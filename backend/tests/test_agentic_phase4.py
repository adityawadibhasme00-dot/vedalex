"""Phase 4 (Master Prompt v7.0.0) — multilingual layer, chain linking, endpoint."""

from __future__ import annotations

import pytest

from app.agents.chain import AgenticChain, _lowest_confidence
from app.agents.multilingual import MultilingualLayer
from app.rag import pipeline as pipe_mod

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "off")
    monkeypatch.delenv("IPSAKTI_BHASHINI_API_KEY", raising=False)
    monkeypatch.delenv("IPSAKTI_BHASHINI_USER_ID", raising=False)


class FakeRetriever:
    calls: list[dict] = []
    result: dict = {
        "sources": [
            {
                "title": "The Patents Act 1970",
                "content": (
                    "Section 3(p) of the Patents Act 1970 bars claims on known "
                    "plants and formulations without enhanced efficacy."
                ),
                "jurisdiction": "India",
            },
            {
                "title": "Biological Diversity Act 2002",
                "content": "Prior approval of the NBA is required for commercial use.",
                "jurisdiction": "India",
            },
            {
                "title": "Ayurvedic Formulary of India",
                "content": "Classical formulations listed in the First Schedule.",
                "jurisdiction": "India",
            },
        ],
        "confidence": 0.9,
        "should_refuse": False,
    }

    @classmethod
    def retrieve(cls, query: str, **kwargs):
        cls.calls.append({"query": query, **kwargs})
        return dict(cls.result)


@pytest.fixture
def fake_retriever(monkeypatch):
    FakeRetriever.calls = []
    monkeypatch.setattr(pipe_mod, "HybridRetriever", FakeRetriever)
    return FakeRetriever


# ---------------------------------------------------------------------------
# Component 10 — Multilingual layer
# ---------------------------------------------------------------------------


def test_multilingual_noop_for_english_target():
    out = MultilingualLayer().translate("Some answer.", target_lang="en")
    assert out["translated"] is False
    assert out["text"] == "Some answer."
    assert out["citations_preserved"] is True


def test_multilingual_offline_returns_original_with_note():
    out = MultilingualLayer().translate(
        "Patents Act 1970, Section 3(p) [Source: Patents Act 1970]",
        target_lang="hi",
    )
    assert out["translated"] is False
    assert out["provider"] == "off"
    assert "preserved" in out["note"]
    assert "[Source: Patents Act 1970]" in out["text"]


def test_multilingual_uses_bhashini_when_enabled(monkeypatch):
    from app.agents import multilingual as ml_mod

    monkeypatch.setattr(
        ml_mod.BhashiniClient, "is_enabled", classmethod(lambda cls: True)
    )
    monkeypatch.setattr(
        ml_mod.BhashiniClient,
        "translate_answer_to_lang",
        classmethod(lambda cls, text, lang: f"[translated:{lang}] {text}"),
    )
    out = MultilingualLayer().translate("Answer text", target_lang="hi")
    assert out["translated"] is True
    assert out["provider"] == "bhashini"
    assert out["text"].startswith("[translated:hi]")


# ---------------------------------------------------------------------------
# Architecture linking — AgenticChain
# ---------------------------------------------------------------------------


def test_lowest_confidence_helper():
    assert _lowest_confidence("HIGH", "MEDIUM") == "MEDIUM"
    assert _lowest_confidence("HIGH", "LOW") == "LOW"
    assert _lowest_confidence("HIGH", "weird") == "LOW"


def test_chain_product_query_links_all_components(fake_retriever):
    out = AgenticChain().execute(
        "Can we patent an Ashwagandha churna from Charaka Samhita?"
    )
    assert out["routing"]["query_type"] == "PRODUCT_SPECIFIC"
    assert out["routing"]["needs_classifier"] is True
    assert out["classification"] is not None
    assert out["classification"]["category"]
    assert out["prior_art"] is not None
    assert out["prior_art"]["risk_level"] in ("RED", "AMBER", "GREEN")
    assert out["citations"]["confidence"] in ("HIGH", "MEDIUM", "LOW")
    assert out["guardrails"]["verdict"] in ("APPROVE", "REJECT")
    assert out["status"] in ("answered", "rejected", "abstained")
    assert out["disclaimer"]
    assert "orchestrator" in out["components"]
    # jurisdiction-filtered retrieval was actually invoked
    assert FakeRetriever.calls[0]["jurisdiction"] in (
        "India",
        "International",
    )


def test_chain_abs_query_includes_abs_path(fake_retriever):
    out = AgenticChain().execute(
        "Do we need access and benefit sharing approval from the NBA?"
    )
    assert out["routing"]["query_type"] == "ABS_QUESTION"
    assert out["abs_path"] is not None
    assert out["abs_path"]["steps"]


def test_chain_general_query_skips_classifier_and_abs(fake_retriever):
    out = AgenticChain().execute("What is a patent?")
    assert out["classification"] is None
    assert out["abs_path"] is None
    assert out["routing"]["query_type"] == "GENERAL_LEGAL"


def test_chain_out_of_scope_query_escalates(fake_retriever):
    out = AgenticChain().execute("Should I sue them for copying my product?")
    assert out["guardrails"]["verdict"] == "REJECT"
    assert out["status"] == "rejected"
    assert out["confidence"] == "LOW"
    assert out["escalation_required"] is True
    assert "human IP facilitator" in out["answer"]


def test_chain_abstains_when_no_sources(fake_retriever):
    FakeRetriever.result = {"sources": [], "should_refuse": True}
    out = AgenticChain().execute("What is a patent?")
    assert out["status"] == "abstained"
    assert out["confidence"] == "LOW"
    assert out["escalation_required"] is True


def test_chain_translation_stage_for_hindi_query(fake_retriever):
    out = AgenticChain().execute(
        "Ashwagandha churna ka patent kar sakte hain?"
    )
    assert out["routing"]["language"] == "hi"
    assert out["translation"]["target_lang"] == "hi"
    assert out["translation"]["translated"] is False  # offline bhashini
    assert out["translation"]["provider"] == "off"


def test_chain_jurisdiction_toggle_india_filters_india_corpus(fake_retriever):
    out = AgenticChain().execute(
        "What does Section 3(p) bar?", jurisdiction="india"
    )
    assert out["jurisdiction"] == "india"
    for call in FakeRetriever.calls:
        assert call["jurisdiction"] == "India"


# ---------------------------------------------------------------------------
# Endpoint — POST /api/v1/agents/agentic-chat
# ---------------------------------------------------------------------------


def test_agentic_chat_endpoint_answers(api_client, fake_retriever):
    resp = api_client.post(
        "/api/v1/agents/agentic-chat",
        json={"query": "What does Section 3(p) of the Patents Act bar?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "answer",
        "status",
        "confidence",
        "escalation_required",
        "routing",
        "citations",
        "guardrails",
        "disclaimer",
    ):
        assert key in body, key
    assert body["routing"]["jurisdiction"] in ("india", "international", "both")


def test_agentic_chat_endpoint_validates_query(api_client):
    resp = api_client.post(
        "/api/v1/agents/agentic-chat", json={"query": "ab"}
    )
    assert resp.status_code == 422


def test_agentic_chat_endpoint_validates_jurisdiction(api_client):
    resp = api_client.post(
        "/api/v1/agents/agentic-chat",
        json={"query": "What is a patent?", "jurisdiction": "mars"},
    )
    assert resp.status_code == 422


def test_agentic_components_endpoint(api_client):
    resp = api_client.get("/api/v1/agents/components")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == len(body["components"])
    assert "orchestrator" in body["components"]
    assert "guardrails" in body["components"]
