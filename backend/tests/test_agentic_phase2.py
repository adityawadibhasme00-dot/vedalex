"""Phase 2 (Master Prompt v7.0.0) — prompts, agent base, orchestrator, RAG pipeline."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.base import (
    PROMPTS_DIR,
    AgentBase,
    AgentContext,
    extract_json,
    load_prompt,
)
from app.agents.orchestrator import Orchestrator
from app.rag import pipeline as pipe_mod
from app.rag.pipeline import (
    ABSTAIN_MESSAGE,
    DISCLAIMER,
    RagPipeline,
    canonical_jurisdiction,
)

pytestmark = pytest.mark.unit

PROMPT_FILES = (
    "orchestrator_prompt.txt",
    "classifier_prompt.txt",
    "rag_prompt.txt",
    "tkdl_prompt.txt",
    "abs_prompt.txt",
    "guardrails_prompt.txt",
    "multilingual_prompt.txt",
)


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    """Keep every test deterministic: provider off unless a test overrides."""
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "off")


# ---------------------------------------------------------------------------
# Prompt files
# ---------------------------------------------------------------------------


def test_all_seven_prompt_files_exist_and_are_non_empty():
    for name in PROMPT_FILES:
        path = PROMPTS_DIR / name
        assert path.is_file(), f"missing prompt file: {name}"
        assert path.read_text(encoding="utf-8").strip(), f"empty prompt: {name}"


def test_load_prompt_returns_text_and_caches():
    first = load_prompt("orchestrator_prompt.txt")
    second = load_prompt("orchestrator_prompt.txt")
    assert first is second  # lru_cache hit
    assert "Orchestrator" in first
    assert "JSON routing decision" in first


def test_load_prompt_missing_file_raises(tmp_path, monkeypatch):
    from app.agents import base as base_mod

    monkeypatch.setattr(base_mod, "PROMPTS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        base_mod.load_prompt("does_not_exist.txt")


def test_load_prompt_empty_file_raises(tmp_path, monkeypatch):
    from app.agents import base as base_mod

    (tmp_path / "empty_prompt.txt").write_text("   \n", encoding="utf-8")
    monkeypatch.setattr(base_mod, "PROMPTS_DIR", tmp_path)
    with pytest.raises(ValueError):
        base_mod.load_prompt("empty_prompt.txt")


# ---------------------------------------------------------------------------
# extract_json
# ---------------------------------------------------------------------------


def test_extract_json_fenced_block():
    raw = 'Sure! Here you go:\n```json\n{"risk_level": "RED"}\n```\nDone.'
    assert extract_json(raw) == {"risk_level": "RED"}


def test_extract_json_bare_object_with_prose():
    raw = 'Decision: {"verdict": "APPROVE", "reason": "grounded"}. Thanks'
    assert extract_json(raw) == {"verdict": "APPROVE", "reason": "grounded"}


def test_extract_json_returns_none_for_garbage():
    assert extract_json("no json here") is None
    assert extract_json("") is None
    assert extract_json("   ") is None


def test_extract_json_returns_none_for_non_object_json():
    assert extract_json('["a", "b"]') is None
    assert extract_json('"just a string"') is None


def test_extract_json_invalid_json_object_returns_none():
    assert extract_json('{"broken": ') is None


# ---------------------------------------------------------------------------
# AgentContext
# ---------------------------------------------------------------------------


def test_agent_context_defaults_and_roundtrip():
    ctx = AgentContext()
    assert ctx.language == "en"
    assert ctx.jurisdiction == "india"
    assert ctx.query_type == "GENERAL_LEGAL"
    assert ctx.ingredients == []

    ctx.ingredients = ["ashwagandha"]
    ctx.query_type = "PRODUCT_SPECIFIC"
    data = ctx.to_dict()
    assert data["ingredients"] == ["ashwagandha"]
    restored = AgentContext.from_dict({**data, "unknown_key": 42})
    assert restored.query_type == "PRODUCT_SPECIFIC"
    assert restored.ingredients == ["ashwagandha"]
    assert not hasattr(restored, "unknown_key")


# ---------------------------------------------------------------------------
# llm_json fallback behaviour
# ---------------------------------------------------------------------------


def test_llm_json_returns_fallback_when_provider_off():
    agent = AgentBase()
    agent.name = "test_agent"
    out = agent.llm_json("anything", {"k": "v"})
    assert out == {"k": "v"}
    assert out is not None


def test_llm_json_returns_fallback_copy_not_same_object():
    agent = AgentBase()
    fallback = {"k": ["v"]}
    out = agent.llm_json("x", fallback)
    assert out == fallback
    out["k"].append("extra")
    assert fallback["k"] == ["v"]


def test_llm_json_provider_without_api_key_uses_fallback(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = AgentBase()
    assert agent.llm_json("x", {"fallback": True}) == {"fallback": True}


def test_agent_base_system_prompt_loads_from_prompt_file():
    agent = Orchestrator()
    assert agent.prompt_file == "orchestrator_prompt.txt"
    assert "route it" in agent.system_prompt


# ---------------------------------------------------------------------------
# Component 1 — Orchestrator routing rules
# ---------------------------------------------------------------------------


def test_workflow_example_routes_product_specific_hindi():
    """Master-prompt workflow example: Ashwagandha churna patent question."""
    decision = Orchestrator().route(
        "Ashwagandha churna ka patent kar sakte hain?"
    )
    assert decision["language"] == "hi"
    assert decision["jurisdiction"] == "india"
    assert decision["query_type"] == "PRODUCT_SPECIFIC"
    assert decision["needs_classifier"] is True
    ctx = decision["context"]
    assert "ashwagandha" in ctx["ingredients"]
    assert "churna" in (ctx["product_name"] or "").lower()


def test_devanagari_query_detected_as_hindi():
    decision = Orchestrator().route("आयुर्वेदिक दवा का पेटेंट कैसे करें?")
    assert decision["language"] == "hi"


def test_english_query_defaults_to_english():
    decision = Orchestrator().route("What are the patent filing requirements?")
    assert decision["language"] == "en"


def test_abs_question_routing():
    decision = Orchestrator().route(
        "Do we need NBA approval for access and benefit sharing?"
    )
    assert decision["query_type"] == "ABS_QUESTION"
    assert decision["needs_classifier"] is False


def test_out_of_scope_dosage_advice_routes_to_abstention():
    decision = Orchestrator().route("What dosage of Ashwagandha should I take daily?")
    assert decision["query_type"] == "OUT_OF_SCOPE"


def test_out_of_scope_is_sticky_against_llm_refinement():
    orch = Orchestrator()
    monkey_decide = {
        "language": "en",
        "jurisdiction": "india",
        "query_type": "GENERAL_LEGAL",
        "needs_classifier": False,
        "context": {},
    }

    def fake_llm_json(user_prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
        return monkey_decide

    orch.llm_json = fake_llm_json  # type: ignore[method-assign]
    decision = orch.route("Should I sue them for copying my product?")
    assert decision["query_type"] == "OUT_OF_SCOPE"


def test_foreign_query_routes_international():
    decision = Orchestrator().route(
        "How does TRIPS affect my Ayurveda formulation abroad?"
    )
    assert decision["jurisdiction"] == "international"


def test_india_plus_foreign_query_routes_both():
    decision = Orchestrator().route(
        "Can I file a PCT application and also an Indian patent?"
    )
    assert decision["jurisdiction"] == "both"


def test_toggle_india_plus_export_routes_both():
    decision = Orchestrator().route(
        "Can we export this to the USA?", jurisdiction="india"
    )
    assert decision["jurisdiction"] == "both"


def test_prior_art_question_routing():
    decision = Orchestrator().route("Is turmeric patentable for wound healing?")
    assert decision["query_type"] == "PRIOR_ART_QUESTION"
    assert decision["needs_classifier"] is False


def test_generic_patent_question_is_general_legal():
    decision = Orchestrator().route("What is a patent?")
    assert decision["query_type"] == "GENERAL_LEGAL"


def test_classical_text_reference_forces_product_specific():
    decision = Orchestrator().route(
        "Is a formulation from Charaka Samhita patentable?"
    )
    assert decision["query_type"] == "PRODUCT_SPECIFIC"
    assert decision["needs_classifier"] is True


def test_route_populates_caller_supplied_context_object():
    ctx = AgentContext(jurisdiction="international")
    Orchestrator().route("What is a patent?", context=ctx)
    assert ctx.query_type == "GENERAL_LEGAL"
    assert ctx.jurisdiction == "india"  # reset from explicit detection


def test_rule_decision_used_verbatim_when_provider_off():
    decision = Orchestrator().route("Do we need NBA approval for biological resources?")
    # provider off → llm_json returns the fallback (the rule decision) unchanged
    assert decision["query_type"] == "ABS_QUESTION"


# ---------------------------------------------------------------------------
# Component 4 — RAG pipeline
# ---------------------------------------------------------------------------


def _sources(n: int = 3) -> list[dict[str, Any]]:
    return [
        {
            "title": f"Source {i}: Patents Act 1970",
            "content": (
                f"Section 3(p) bars evergreening of known plants and "
                f"formulations. Chunk {i} of the Act text."
            ),
            "jurisdiction": "India",
        }
        for i in range(1, n + 1)
    ]


class FakeRetriever:
    calls: list[dict[str, Any]] = []
    result: dict[str, Any] = {"sources": _sources(), "confidence": 0.9}
    error: Exception | None = None

    @classmethod
    def retrieve(cls, query: str, **kwargs: Any) -> dict[str, Any]:
        cls.calls.append({"query": query, **kwargs})
        if cls.error is not None:
            raise cls.error
        return dict(cls.result)


@pytest.fixture
def fake_retriever(monkeypatch):
    FakeRetriever.calls = []
    FakeRetriever.result = {"sources": _sources(), "confidence": 0.9}
    FakeRetriever.error = None
    monkeypatch.setattr(pipe_mod, "HybridRetriever", FakeRetriever)
    return FakeRetriever


def test_canonical_jurisdiction_values():
    assert canonical_jurisdiction(None) == "India"
    assert canonical_jurisdiction("india") == "India"
    assert canonical_jurisdiction("International") == "International"
    assert canonical_jurisdiction("global") == "International"
    assert canonical_jurisdiction("both") == "both"
    assert canonical_jurisdiction("anything-else") == "India"


def test_retrieve_passes_jurisdiction_filter_to_hybrid_retriever(fake_retriever):
    RagPipeline().retrieve("Ashwagandha patent", jurisdiction="india", top_k=3)
    assert len(fake_retriever.calls) == 1
    call = fake_retriever.calls[0]
    assert call["jurisdiction"] == "India"
    assert call["top_k"] == 3


def test_retrieve_both_keeps_sides_separate(fake_retriever):
    out = RagPipeline().retrieve("Ashwagandha patent", jurisdiction="both")
    jurisdictions = [c["jurisdiction"] for c in fake_retriever.calls]
    assert jurisdictions == ["India", "International"]
    assert set(out["sides"]) == {"india", "international"}
    tagged = {s["jurisdiction"] for s in out["sources"]}
    assert tagged == {"India", "International"}


def test_answer_abstains_when_no_sources(fake_retriever):
    FakeRetriever.result = {"sources": [], "should_refuse": True,
                            "refusal_reason": "index empty"}
    out = RagPipeline().answer("Ashwagandha patent")
    assert out["text"] == ABSTAIN_MESSAGE
    assert out["confidence"] == "LOW"
    assert out["refused"] is True
    assert out["citations"] == []


def test_answer_abstains_when_retrieval_raises(fake_retriever):
    FakeRetriever.error = RuntimeError("qdrant down")
    out = RagPipeline().answer("Ashwagandha patent")
    assert out["text"] == ABSTAIN_MESSAGE
    assert out["confidence"] == "LOW"


def test_answer_offline_deterministic_with_verified_citations(fake_retriever):
    out = RagPipeline().answer("What does Section 3(p) say?", jurisdiction="india")
    assert out["generated"] is False
    assert out["provider"] in ("off", "mock")
    assert out["confidence"] == "HIGH"
    assert out["citations"], "deterministic answer must cite sources"
    assert out["verification"]["unverified"] == []
    assert DISCLAIMER in out["text"]
    assert out["disclaimer"] == DISCLAIMER
    assert out["refused"] is False


def test_answer_both_jurisdictions_emits_separate_sections(fake_retriever):
    out = RagPipeline().answer("Compare India and PCT routes", jurisdiction="both")
    assert "### India" in out["text"]
    assert "### International" in out["text"]
    assert len(out["sections"]) == 2


def test_citation_in_sources_accepts_real_and_rejects_fabricated():
    srcs = _sources(1)
    assert RagPipeline._citation_in_sources("Patents Act 1970", srcs) is True
    assert RagPipeline._citation_in_sources("Nonexistent Act 2999", srcs) is False
    assert RagPipeline._citation_in_sources("ab", srcs) is False


def test_confidence_levels_from_citation_verification():
    def section(verified: int, total: int) -> dict[str, Any]:
        return {
            "citations": [f"cite-{i}" for i in range(total)],
            "verified_citations": [f"cite-{i}" for i in range(verified)],
        }

    assert RagPipeline._confidence([section(3, 3)], 3) == "HIGH"
    assert RagPipeline._confidence([section(1, 3)], 3) == "MEDIUM"
    assert RagPipeline._confidence([section(0, 2)], 2) == "LOW"
    # No citations in the answer at all: enough sources → HIGH, thin → MEDIUM
    empty: list[dict[str, Any]] = [
        {"citations": [], "verified_citations": []}
    ]
    assert RagPipeline._confidence(empty, 4) == "HIGH"
    assert RagPipeline._confidence(empty, 1) == "MEDIUM"


def test_retrieve_failure_returns_abstain_not_exception(fake_retriever):
    FakeRetriever.result = {"sources": []}
    out = RagPipeline().answer("anything")
    assert out["refused"] is True
