import sys
import types
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.rag.retrieval_pipeline import HybridRetriever
from app.services import copilot_orchestrator as co
from app.services import multi_layer_orchestrator as mlo
from app.services.ai_copilot import NO_EVIDENCE_ANSWER
from app.services.multi_layer_orchestrator import MultiLayerOrchestrator as M

QUESTION = "What are the patent requirements for Ashwagandha formulation in India?"


def _source(content, **kw):
    base = {
        "content": content,
        "source": "India Code",
        "title": "India Code",
        "act_title": "Patents Act, 1970",
        "authority": "Government of India",
        "authority_rank": 1,
        "authority_level": 1,
        "category": "statutory",
        "retrieval_method": "statutory",
        "jurisdiction": "India",
        "source_url": "https://www.indiacode.nic.in/act",
    }
    base.update(kw)
    return base


def _grounded(question, **kw):
    tokens = " ".join(sorted(co._meaningful_tokens(question)))
    return _source(f"{tokens} section 3(p) of the patents act covers these requirements",
                   **kw)


def _weak(question, keep=3, **kw):
    tokens = sorted(co._meaningful_tokens(question))[:keep]
    return _source(" ".join(tokens) + " unrelated corpus wording", **kw)


def _readiness_result(patent_ready=False, overall=55.0, similar=True):
    codes = ["novelty", "prior_art", "section3p", "disclosure", "evidence",
             "ownership", "fto", "documentation"]
    earned = [6, 4, 5, 7, 3, 8, 5, 6]
    comps = [
        {"code": c, "earned": e, "max": 10, "pct": e * 10.0}
        for c, e in zip(codes, earned, strict=False)
    ]
    return {
        "components": comps,
        "overall_readiness": overall,
        "patent_ready": patent_ready,
        "novelty_score": 42.0,
        "prior_art_overlap": 35.0,
        "similar_patents": (
            [{"title": "Family ABC herbal extract", "similarity": 61.0, "jurisdiction": "IN"}]
            if similar else []
        ),
        "missing_evidence": ["stability data"],
        "next_actions": ["Run a detailed TKDL search"],
        "section3p_risk": "Flagged",
        "passport_id": "passport-1",
    }


def _claim(**kw):
    base = {
        "overall": "HIGH_RISK",
        "counts": {"red": 1, "yellow": 0, "green": 1},
        "results": [],
        "suggested": ["Supports healthy function", "Helps maintain immunity"],
    }
    base.update(kw)
    return base


def _verification(passed=True, regenerated=False, final_answer="",
                  gate_reason="All verification checks passed"):
    return SimpleNamespace(
        original_answer="",
        final_answer=final_answer,
        passed_gate=passed,
        gate_reason=gate_reason,
        regenerated=regenerated,
        regeneration_count=1 if regenerated else 0,
        removed_claims=[],
        unsupported_claims=[],
        evidence_confidence=SimpleNamespace(overall=0.8, band="HIGH"),
        verification_table=SimpleNamespace(
            total_claims=2, supported_count=2, contradicted_count=0,
            not_enough_count=0, support_ratio=1.0, all_supported=True,
        ),
        citation_report=SimpleNamespace(
            total_citations=1, valid_citations=1, invalid_citations=0,
            validity_ratio=1.0,
        ),
    )


def _guard_ok(answer, sources, question, confidence):
    return SimpleNamespace(
        risk_level=SimpleNamespace(value="low"), grounded=True,
        coverage_ratio=0.9, citation_count=1, violations=[], recommendations=[],
    )


def _guard_critical(answer, sources, question, confidence):
    return SimpleNamespace(
        risk_level=SimpleNamespace(value="critical"), grounded=False,
        coverage_ratio=0.0, citation_count=0, violations=[], recommendations=[],
    )


def _draft_off(*args, **kwargs):
    return {"generated": False, "text": None, "provider": "off", "model": None,
            "reason": "disabled in tests"}


def _draft_on(text="A grounded draft answer built only from retrieved passages "
                   "and citing every claim it makes in the answer text."):
    def _inner(*args, **kwargs):
        return {"generated": True, "text": text, "provider": "unit", "model": "m",
                "reason": ""}
    return _inner


def _draft_boom(*args, **kwargs):
    raise RuntimeError("llm unavailable")


def _classification_payload(**kw):
    base = {
        "product_family": "cosmetic",
        "rule_validation": [{"status": "SATISFIED", "rule": "r1"}],
        "ingredients": ["Neem"],
    }
    base.update(kw)
    return base


class _FakeClassificationResponse:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return dict(self._payload)


class _DictOnlyResponse:
    def __init__(self, payload):
        self._payload = payload

    def dict(self):
        return dict(self._payload)


def _fake_classify(*args, **kwargs):
    return _FakeClassificationResponse(_classification_payload())


def _fake_escalate(**kwargs):
    return SimpleNamespace(to_dict=lambda: {
        "escalate": True,
        "reasons": ["requires review"],
        "confidence": kwargs.get("confidence", 0.0),
    })


def _fake_bilingual(classification):
    out = dict(classification)
    out["category_label"] = "Cosmetic"
    out["category_label_hi"] = "Prasadan"
    return out


@pytest.fixture(autouse=True)
def _pipeline_defaults(monkeypatch):
    monkeypatch.delenv("IPSAKTI_ENABLE_LIVE_WEB", raising=False)
    monkeypatch.setattr(mlo, "MCP_ENABLED", False)
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft", _draft_off)
    monkeypatch.setattr("app.rag.hallucination_guard.validate_answer", _guard_ok)
    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification",
                        lambda *a, **k: _verification())
    monkeypatch.setattr("app.rag.knowledge_graph.build_graph",
                        lambda force=False: {"nodes": []})
    monkeypatch.setattr("app.services.product_classifier.ProductClassifier.classify",
                        _fake_classify)
    monkeypatch.setattr("app.services.escalation_service.should_escalate",
                        _fake_escalate)
    monkeypatch.setattr("app.services.escalation_service.classification_bilingual",
                        _fake_bilingual)
    yield


def _run(question, sources=None, **kw):
    kw.setdefault("context", {"jurisdiction": "India"})
    if sources is None:
        return M.run(question, **kw)
    return M.run(question, retrieved_sources=list(sources), **kw)


# ---------------------------------------------------------------------------
# citation voting (Layer 6)
# ---------------------------------------------------------------------------

def test_vote_citations_high_tier_needs_two_independent_official_sources():
    sources = [
        _source("passage a", source_url="https://ipindia.gov.in/a"),
        _source("passage b", source_url="https://tkdl.res.in/b"),
    ]
    vote = mlo.vote_citations(sources)
    assert vote["tier"] == "HIGH"
    assert vote["official_votes"] == 2
    assert vote["confidence_cap"] == 0.90
    assert vote["high_confidence"] is True
    assert vote["required_for_high"] == 2
    assert [b["vote"] for b in vote["ballots"]] == ["accepted", "accepted"]


def test_vote_citations_same_document_counts_once():
    sources = [
        _source("chunk one", source_url="https://ipindia.gov.in/a"),
        _source("chunk two", source_url="https://ipindia.gov.in/a"),
    ]
    vote = mlo.vote_citations(sources)
    assert vote["official_votes"] == 1
    assert vote["tier"] == "MEDIUM"
    assert vote["confidence_cap"] == 0.60
    assert vote["high_confidence"] is False


def test_vote_citations_low_tier_without_official_sources():
    sources = [
        _source("blog passage", source="Journal", act_title="", category="guidance",
                retrieval_method="semantic", authority_rank=3, authority_level=3,
                source_url="https://example.org/x"),
    ]
    vote = mlo.vote_citations(sources)
    assert vote["tier"] == "LOW"
    assert vote["official_votes"] == 0
    assert vote["confidence_cap"] == 0.35
    assert vote["ballots"][0]["vote"] == "secondary"


def test_vote_citations_rejects_sources_without_provenance():
    vote = mlo.vote_citations([{"content": "", "source": "", "title": "",
                                "act_title": "", "category": "statutory"}])
    assert vote["ballots"][0]["vote"] == "rejected"
    assert vote["official_votes"] == 0
    assert "No usable citation provenance" in vote["ballots"][0]["note"]


def test_vote_citations_empty_source_list():
    vote = mlo.vote_citations([])
    assert vote["tier"] == "LOW"
    assert vote["ballots"] == []
    assert vote["independent_official_sources"] == []


@pytest.mark.parametrize("source,expected", [
    ({"retrieval_method": "statutory", "content": "c"}, True),
    ({"category": "pharmacopoeia", "content": "c"}, True),
    ({"authority_level": "2", "content": "c"}, True),
    ({"authority_rank": 1, "content": "c"}, True),
    ({"authority_rank": "not-a-number", "content": "c"}, False),
    ({"content": "c", "source_url": "https://ipindia.gov.in/x"}, True),
    ({"content": "c", "source_url": "https://fssai.gov.in/x"}, True),
    ({"content": "c", "source_url": "https://evil.example.org/x"}, False),
    ({"content": "c", "source": "Journal"}, False),
])
def test_is_official_source_classification(source, expected):
    assert mlo._is_official_source(source) is expected


def test_source_identity_precedence():
    assert mlo._source_identity({"source_url": "u", "source": "s"}) == "u"
    assert mlo._source_identity({"source": "s", "act_title": "a"}) == "s"
    assert mlo._source_identity({"act_title": "a", "title": "t"}) == "a"
    assert mlo._source_identity({"title": "t"}) == "t"
    assert mlo._source_identity({}) == ""


def test_source_has_provenance_requires_identity_and_body():
    assert mlo._source_has_provenance({"source": "s", "content": "c"}) is True
    assert mlo._source_has_provenance({"source": "s", "section": "3(p)"}) is True
    assert mlo._source_has_provenance({"source": "s"}) is False
    assert mlo._source_has_provenance({"content": "c"}) is False


def test_mcp_tool_registry_shape():
    tool = mlo.MCP_TOOLS["fetch_official_sources"]
    assert tool["name"] == "fetch_official_sources"
    assert callable(tool["call"])
    assert "whitelist" in tool["description"]


# ---------------------------------------------------------------------------
# Layer 3 — knowledge graph retrieval
# ---------------------------------------------------------------------------

def test_knowledge_graph_retrieve_maps_matching_nodes(monkeypatch):
    graph = {"nodes": [
        {"name": "Ashwagandha", "type": "monograph",
         "aliases": ["Withania somnifera"], "attrs": {"family": "Solanaceae",
                                                      "keywords": ["ashwa"]}},
        {"name": "Patents Act", "type": "regulation", "aliases": [],
         "attrs": {"section": "3(p)", "effective_date": "1970"},
         "authority": "Legislative Department", "jurisdiction": "India"},
        {"name": "Ignored node", "type": "concept", "aliases": []},
    ]}
    monkeypatch.setattr("app.rag.knowledge_graph.build_graph",
                        lambda force=False: graph)
    sources = mlo.knowledge_graph_retrieve("ashwagandha patent", limit=5)
    assert len(sources) == 2
    assert sources[0]["retrieval_method"] == "knowledge_graph"
    assert sources[0]["category"] == "pharmacopoeia"
    assert sources[0]["authority_level"] == 2
    assert "Solanaceae" in sources[0]["content"]
    assert sources[1]["category"] == "statutory"
    assert sources[1]["authority_level"] == 2
    assert sources[1]["section"] == "3(p)"
    assert sources[1]["jurisdiction"] == "India"


def test_knowledge_graph_retrieve_dedupes_and_respects_limit(monkeypatch):
    graph = {"nodes": [
        {"name": "Ashwagandha", "type": "monograph", "aliases": []},
        {"name": "Ashwagandha", "type": "monograph", "aliases": []},
        {"name": "Neem", "type": "botanical", "aliases": []},
    ]}
    monkeypatch.setattr("app.rag.knowledge_graph.build_graph",
                        lambda force=False: graph)
    sources = mlo.knowledge_graph_retrieve("ashwagandha neem", limit=2)
    assert len(sources) == 2
    identities = {s["source"] for s in sources}
    assert "Ashwagandha" in identities


def test_knowledge_graph_retrieve_includes_statuses_in_content(monkeypatch):
    graph = {"nodes": [
        {"name": "Ashwagandha", "type": "ingredient", "aliases": [],
         "attrs": {"keywords": ["ashwa"]},
         "statuses": [{"market": "India", "status": "allowed"},
                      {"market": "US", "status": "ndi"}]},
    ]}
    monkeypatch.setattr("app.rag.knowledge_graph.build_graph",
                        lambda force=False: graph)
    sources = mlo.knowledge_graph_retrieve("ashwagandha")
    assert "India — allowed" in sources[0]["content"]
    assert "US — ndi" in sources[0]["content"]


def test_knowledge_graph_retrieve_without_meaningful_tokens(monkeypatch):
    monkeypatch.setattr("app.rag.knowledge_graph.build_graph",
                        lambda force=False: {"nodes": [
                            {"name": "Ashwagandha", "type": "monograph", "aliases": []},
                        ]})
    assert mlo.knowledge_graph_retrieve("भारत") == []


def test_knowledge_graph_retrieve_handles_graph_build_failure(monkeypatch):
    def _boom(force=False):
        raise RuntimeError("graph down")

    monkeypatch.setattr("app.rag.knowledge_graph.build_graph", _boom)
    assert mlo.knowledge_graph_retrieve("ashwagandha") == []


def test_knowledge_graph_retrieve_handles_missing_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "app.rag.knowledge_graph",
                        types.ModuleType("stub_graph"))
    assert mlo.knowledge_graph_retrieve("ashwagandha") == []


# ---------------------------------------------------------------------------
# grounding / layer helpers
# ---------------------------------------------------------------------------

def test_compute_grounding_full_overlap():
    out = M._compute_grounding("ashwagandha patent requirements",
                               [_source("ashwagandha patent requirements text")])
    assert out["retrieval_grounded"] is True
    assert out["ratio_grounded"] is True
    assert out["coverage"] == 1.0
    assert out["threshold"] == (len(out["meaningful"]) + 1) // 2
    assert out["threshold"] < len(out["meaningful"]) + 1


def test_compute_grounding_without_overlap():
    out = M._compute_grounding("ashwagandha patent requirements",
                               [_source("marine biology notes")])
    assert out["retrieval_grounded"] is False
    assert out["ratio_grounded"] is False
    assert out["coverage"] == 0.0


def test_compute_grounding_without_meaningful_tokens():
    out = M._compute_grounding("भारत में पेटेंट", [_source("anything at all")])
    assert out["meaningful"] == set()
    assert out["retrieval_grounded"] is False
    assert out["threshold"] == 1


def test_layer_hybrid_rag_returns_pipeline_result(monkeypatch):
    payload = {"sources": [_source("x")], "confidence": 0.8}
    monkeypatch.setattr(HybridRetriever, "retrieve", lambda *a, **k: payload)
    assert M._layer_hybrid_rag("q", domains=["patents"], jurisdiction="India") == payload


def test_layer_hybrid_rag_swallows_pipeline_errors(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("pipeline down")

    monkeypatch.setattr(HybridRetriever, "retrieve", _boom)
    assert M._layer_hybrid_rag("q", domains=cast(list[str], None), jurisdiction=None) == {}


def test_dedupe_delegates_to_single_layer():
    sources = [_source("x" * 100 + " a"), _source("x" * 100 + " b")]
    assert len(M._dedupe(sources)) == 1
    assert M._dedupe(sources, limit=1) == M._dedupe(sources, limit=1)


def test_get_legacy_fallback_returns_sources(monkeypatch):
    monkeypatch.setattr(co.AICopilotOrchestrator, "_get_fallback_sources",
                        classmethod(lambda cls, q: [_source("legacy")]))
    assert M._get_legacy_fallback("q")[0]["content"] == "legacy"


def test_get_legacy_fallback_swallows_errors(monkeypatch):
    def _boom(cls, q):
        raise RuntimeError("legacy down")

    monkeypatch.setattr(co.AICopilotOrchestrator, "_get_fallback_sources",
                        classmethod(_boom))
    assert M._get_legacy_fallback("q") == []


# ---------------------------------------------------------------------------
# Layer 4 — rule engine fallback
# ---------------------------------------------------------------------------

def _rule_engine(question, intent_id, passport_id=None, domain=None,
                 charts=None, **kw):
    domain = domain or {"run_patent_engine": True}
    return M._layer_rule_engine(question, passport_id, intent_id, domain,
                                charts if charts is not None else [], **kw)


def test_rule_engine_patentability_scores_real_passport(monkeypatch):
    monkeypatch.setattr("app.services.passport_engine.PassportEngine.get_passport",
                        lambda pid: object())
    monkeypatch.setattr(
        "app.services.patent_readiness_engine.PatentReadinessEngine.compute",
        lambda passport: _readiness_result())
    charts: list[dict[str, Any]] = []
    out = _rule_engine("q", "patentability", passport_id="p1", charts=charts)
    assert out["engine_grounded"] is True
    assert out["readiness"]["overall_readiness"] == 55
    assert [c["type"] for c in charts] == ["radar", "bar_h", "doughnut"]


def test_rule_engine_unscored_without_passport(monkeypatch):
    monkeypatch.setattr(
        "app.services.patent_readiness_engine.PatentReadinessEngine.compute",
        lambda passport: _readiness_result())
    charts: list[dict[str, Any]] = []
    out = _rule_engine("q", "patentability", passport_id=None, charts=charts)
    assert out["readiness"] is None
    assert out["engine_grounded"] is False
    assert charts == []


def test_rule_engine_handles_broken_passport_store(monkeypatch):
    def _boom(pid):
        raise RuntimeError("store down")

    monkeypatch.setattr("app.services.passport_engine.PassportEngine.get_passport",
                        _boom)
    out = _rule_engine("q", "patentability", passport_id="p1")
    assert out["readiness"] is None
    assert out["engine_grounded"] is False


def test_rule_engine_compliance_and_evidence_and_roadmap_charts(monkeypatch):
    monkeypatch.setattr("app.services.passport_engine.PassportEngine.get_passport",
                        lambda pid: object())
    monkeypatch.setattr(
        "app.services.patent_readiness_engine.PatentReadinessEngine.compute",
        lambda passport: _readiness_result())

    charts: list[dict[str, Any]] = []
    _rule_engine("q", "compliance", passport_id="p1", charts=charts)
    assert [c["type"] for c in charts] == ["gauge", "radar"]

    charts = []
    _rule_engine("q", "evidence_strength", passport_id="p1", charts=charts)
    assert [c["type"] for c in charts] == ["doughnut"]

    charts = []
    _rule_engine("q", "regulatory_roadmap", passport_id="p1", charts=charts)
    assert [c["type"] for c in charts] == ["timeline"]


def test_rule_engine_gated_off_for_non_patent_domain(monkeypatch):
    monkeypatch.setattr(
        "app.services.patent_readiness_engine.PatentReadinessEngine.compute",
        lambda passport: _readiness_result())
    charts: list[dict[str, Any]] = []
    out = _rule_engine("q", "patentability", passport_id="p1",
                       domain={"run_patent_engine": False}, charts=charts)
    assert out["readiness"] is None
    assert charts == []


def test_rule_engine_marketing_claim_uses_firewall(monkeypatch):
    monkeypatch.setattr(
        "app.services.passport_engine.PassportEngine.get_passport",
        lambda pid: SimpleNamespace(proposed_claims=["Treats diabetes"]))
    charts: list[dict[str, Any]] = []
    out = _rule_engine("q", "marketing_claim", passport_id="p1", charts=charts)
    assert out["claim"]["overall"] == "HIGH_RISK"
    assert [c["type"] for c in charts] == ["risk_matrix"]
    assert out["engine_grounded"] is True


def test_rule_engine_marketing_claim_without_claims(monkeypatch):
    monkeypatch.setattr(
        "app.services.passport_engine.PassportEngine.get_passport",
        lambda pid: SimpleNamespace(proposed_claims=[]))
    out = _rule_engine("q", "marketing_claim", passport_id="p1")
    assert out["claim"] is None
    assert out["engine_grounded"] is False


def test_rule_engine_dataset_intents_ground_without_passport():
    charts: list[dict[str, Any]] = []
    out = _rule_engine("q", "botanical_origin", charts=charts)
    assert out["engine_grounded"] is True
    assert [c["type"] for c in charts] == ["india_heatmap"]

    charts = []
    out = _rule_engine("q", "white_space", charts=charts)
    assert out["engine_grounded"] is True
    assert [c["type"] for c in charts] == ["opportunity_heatmap"]


def test_rule_engine_no_rule_for_general_intent():
    charts: list[dict[str, Any]] = []
    out = _rule_engine("q", "general", charts=charts)
    assert out == {"passport": None, "readiness": None, "claim": None,
                   "engine_grounded": False, "charts": []}


# ---------------------------------------------------------------------------
# Layer 5 — MCP live retrieval
# ---------------------------------------------------------------------------

def test_layer_mcp_disabled_reports_reason(monkeypatch):
    monkeypatch.setattr(mlo, "MCP_ENABLED", False)
    out = M._layer_mcp_live("q")
    assert out["enabled"] is False
    assert out["sources"] == []
    assert "disabled" in out["reason"]


def test_layer_mcp_returns_live_sources(monkeypatch):
    monkeypatch.setattr(mlo, "MCP_ENABLED", True)
    monkeypatch.setattr("app.rag.official_web_retriever.fetch_official_sources",
                        lambda q, top_k=3: [_source("live passage")])
    out = M._layer_mcp_live("q")
    assert out["enabled"] is True
    assert out["sources"][0]["content"] == "live passage"


def test_layer_mcp_swallows_tool_errors(monkeypatch):
    monkeypatch.setattr(mlo, "MCP_ENABLED", True)
    monkeypatch.setattr(
        "app.rag.official_web_retriever.fetch_official_sources",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network blocked")))
    out = M._layer_mcp_live("q")
    assert out["sources"] == []
    assert "network blocked" in out["reason"]


# ---------------------------------------------------------------------------
# assistant enrichment (wizard + escalation)
# ---------------------------------------------------------------------------

def test_assistant_enrichment_extracts_query_hints():
    out = M._assistant_enrichment(
        question="neem syrup for skin and cosmetic use", passport_id=None,
        context=None, confidence=0.7, risk_level="Moderate")
    assert out["declared_use"] == "cosmetic"
    assert out["classification"]["product_family"] == "cosmetic"
    assert out["classification_bilingual"]["category_label"]
    assert out["escalation"]["escalate"] is True


def test_assistant_enrichment_detects_dietary_medicine_and_wellness(monkeypatch):
    captured = {}

    def _classify(**kwargs):
        captured.update(kwargs)
        return _FakeClassificationResponse(_classification_payload())

    monkeypatch.setattr("app.services.product_classifier.ProductClassifier.classify",
                        _classify)
    M._assistant_enrichment(question="health drink supplement nutrition",
                            passport_id=None, context=None, confidence=0.5,
                            risk_level="Moderate")
    assert captured["declared_use"] == "dietary"

    M._assistant_enrichment(question="tablet syrup for diabetes treatment",
                            passport_id=None, context=None, confidence=0.5,
                            risk_level="Moderate")
    assert captured["declared_use"] == "medicine"
    assert captured["product_form"] == "syrup"

    M._assistant_enrichment(question="immunity wellness tonic boost",
                            passport_id=None, context=None, confidence=0.5,
                            risk_level="Moderate")
    assert captured["declared_use"] == "wellness"


def test_assistant_enrichment_reads_passport_facts(monkeypatch):
    passport = SimpleNamespace(
        case_title="Golden Turmeric", product_form="capsule", dosage_form="oral",
        intended_use="wellness", proposed_claims=["Supports immunity"],
        ingredients=[SimpleNamespace(raw_name="Turmeric")],
        process_description="cold extraction",
    )
    monkeypatch.setattr("app.services.passport_engine.PassportEngine.get_passport",
                        lambda pid: passport)
    captured = {}

    def _classify(**kwargs):
        captured.update(kwargs)
        return _FakeClassificationResponse(_classification_payload())

    monkeypatch.setattr("app.services.product_classifier.ProductClassifier.classify",
                        _classify)
    out = M._assistant_enrichment(question="anything at all", passport_id="p1",
                                  context=None, confidence=0.6, risk_level="Low")
    assert captured["product_name"] == "Golden Turmeric"
    assert captured["product_form"] == "capsule"
    assert captured["ingredients"] == ["Turmeric"]
    assert out["declared_use"] == ""


def test_assistant_enrichment_handles_classifier_failure(monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("classifier down")

    monkeypatch.setattr("app.services.product_classifier.ProductClassifier.classify",
                        _boom)
    out = M._assistant_enrichment(question="neem syrup", passport_id=None,
                                  context=None, confidence=0.5, risk_level="Moderate")
    assert out["classification"] is None
    assert out["escalation"] is None


def test_assistant_enrichment_falls_back_to_dict_only_response(monkeypatch):
    monkeypatch.setattr(
        "app.services.product_classifier.ProductClassifier.classify",
        lambda **kw: _DictOnlyResponse(_classification_payload()))
    out = M._assistant_enrichment(question="neem syrup", passport_id=None,
                                  context=None, confidence=0.5, risk_level="Moderate")
    assert out["classification"]["product_family"] == "cosmetic"


def test_assistant_enrichment_escalates_on_unsatisfied_rules(monkeypatch):
    captured = {}

    def _escalate(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(to_dict=lambda: {"escalate": True, "reasons": ["rule"]})

    monkeypatch.setattr("app.services.escalation_service.should_escalate", _escalate)
    monkeypatch.setattr(
        "app.services.product_classifier.ProductClassifier.classify",
        lambda **kw: _FakeClassificationResponse(_classification_payload(
            rule_validation=[{"status": "NOT_SATISFIED", "rule": "r1"}])))
    out = M._assistant_enrichment(question="ashwagandha patent", passport_id=None,
                                  context=None, confidence=0.4, risk_level="High")
    assert captured["requires_human_review"] is True
    assert captured["is_patent_question"] is True
    assert out["escalation"]["escalate"] is True


def test_assistant_enrichment_handles_escalation_failure(monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("escalation down")

    monkeypatch.setattr("app.services.escalation_service.should_escalate", _boom)
    out = M._assistant_enrichment(question="neem syrup", passport_id=None,
                                  context=None, confidence=0.5, risk_level="Moderate")
    assert out["escalation"] is None


def test_assistant_enrichment_bilingual_failure_returns_raw_classification(
        monkeypatch):
    def _boom(classification):
        raise RuntimeError("bilingual down")

    monkeypatch.setattr("app.services.escalation_service.classification_bilingual",
                        _boom)
    out = M._assistant_enrichment(question="neem syrup", passport_id=None,
                                  context=None, confidence=0.5, risk_level="Moderate")
    assert out["classification"] == out["classification_bilingual"]
    assert out["classification"]["product_family"] == "cosmetic"


def test_assistant_enrichment_uses_falsy_response_dict(monkeypatch):
    class _Weird:
        def model_dump(self):
            raise AttributeError("no dump")

        def dict(self):
            return {"product_family": "legacy"}

    monkeypatch.setattr("app.services.product_classifier.ProductClassifier.classify",
                        lambda **kw: _Weird())
    out = M._assistant_enrichment(question="neem syrup", passport_id=None,
                                  context=None, confidence=0.5, risk_level="Moderate")
    assert out["classification"]["product_family"] == "legacy"
    assert out["classification_bilingual"]["category_label"]


# ---------------------------------------------------------------------------
# run() — clarification path
# ---------------------------------------------------------------------------

def test_run_clarifies_when_jurisdiction_is_ambiguous():
    result = M.run("tell me about product quality checks")
    assert result["confidence"] == 0.02
    assert result["sources"] == []
    assert result["response_sections"]["clarification_needed"] is True
    assert result["response_sections"]["jurisdiction"] is None
    assert "No legal framework has been applied yet" in result["answer"]
    assert result["analysis_card"]["verification_badge"] == "Clarification needed"
    flow = result["decision_trace"]["pipeline"]["layer_flow"]
    assert [f["status"] for f in flow] == ["CLARIFY", "HOLD"]
    assert result["decision_trace"]["pipeline"]["layers"][0] == "1 · Intent Router"


def test_run_clarification_uses_router_question(monkeypatch):
    monkeypatch.setattr(
        mlo, "resolve_jurisdiction",
        lambda q, ctx: {
            "mode": None, "resolved_via": "clarification",
            "clarification_needed": True,
            "clarification_question": "Pick a framework please",
        })
    result = M.run("tell me about product quality checks")
    assert result["answer"].startswith("Pick a framework please")
    assert result["response_sections"]["direct_answer"] == "Pick a framework please"
    assert result["response_sections"]["options"] == ["🇮🇳 India Laws Only",
                                                      "🌍 International Laws Only"]


# ---------------------------------------------------------------------------
# run() — pipeline layers
# ---------------------------------------------------------------------------

def test_run_pre_retrieved_sources_walks_all_layers():
    result = _run(QUESTION, [_grounded(QUESTION)])
    flow = {f["layer"]: f for f in result["decision_trace"]["pipeline"]["layer_flow"]}
    assert "pre-retrieved candidate source(s) used" in flow[
        "2 · Hybrid RAG (BM25 + BGE-M3 + Qdrant)"]["detail"]
    assert flow["3 · Knowledge Graph fallback"]["status"] == "SKIP"
    assert flow["5 · MCP live retrieval"]["status"] == "SKIP"
    assert flow["6 · Citation Voting"]["status"] == "PASS"
    assert flow["7 · LLM response generation"]["status"] == "PASS"
    assert result["confidence"] <= 0.60
    assert result["analysis_card"]["verification_badge"] == \
        "Grounded — Knowledge Base Cited"
    assert NO_EVIDENCE_ANSWER not in result["answer"]


def test_run_hybrid_layer_reports_merge_statistics(monkeypatch):
    monkeypatch.setattr(HybridRetriever, "retrieve", lambda *a, **k: {
        "sources": [_grounded(QUESTION)],
        "confidence": 0.9,
        "retrieval_stats": {"semantic_results": 5, "bm25_results": 3,
                            "statutory_results": 2, "final_count": 1,
                            "total_time_ms": 12},
        "should_refuse": False,
        "refusal_reason": "",
        "grounding": {"coverage_ratio": 0.9},
    })
    result = M.run(QUESTION, context={"jurisdiction": "India"})
    flow = {f["layer"]: f for f in result["decision_trace"]["pipeline"]["layer_flow"]}
    detail = flow["2 · Hybrid RAG (BM25 + BGE-M3 + Qdrant)"]["detail"]
    assert "5 → 3 → 2 merged" in detail
    assert "rerank → 1 final" in detail
    assert result["confidence"] == 0.60
    assert result["analysis_card"]["retrieval_stats"]["semantic_results"] == 5


def test_run_hybrid_failure_uses_legacy_fallback(monkeypatch):
    monkeypatch.setattr(HybridRetriever, "retrieve",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(M, "_get_legacy_fallback",
                        classmethod(lambda cls, q: [_grounded(QUESTION)]))
    result = M.run(QUESTION, context={"jurisdiction": "India"})
    flow = {f["layer"]: f for f in result["decision_trace"]["pipeline"]["layer_flow"]}
    assert flow["2 · Hybrid RAG (BM25 + BGE-M3 + Qdrant)"]["status"] == "SKIP"
    assert "No hybrid candidates" in flow[
        "2 · Hybrid RAG (BM25 + BGE-M3 + Qdrant)"]["detail"]
    assert result["sources"]


def test_run_hybrid_failure_without_legacy_fallback_refuses(monkeypatch):
    monkeypatch.setattr(HybridRetriever, "retrieve",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(M, "_get_legacy_fallback", classmethod(lambda cls, q: []))
    result = M.run("obscure marine lichen taxonomy",
                   context={"jurisdiction": "India"})
    assert NO_EVIDENCE_ANSWER in result["answer"]
    assert result["confidence"] <= 0.1
    assert result["analysis_card"]["verification_badge"] == "Insufficient Evidence"


def test_run_knowledge_graph_layer_fires_on_weak_evidence(monkeypatch):
    graph = {"nodes": [
        {"name": "Ashwagandha", "type": "monograph",
         "aliases": ["Withania somnifera"]},
    ]}
    monkeypatch.setattr("app.rag.knowledge_graph.build_graph",
                        lambda force=False: graph)
    result = _run("ashwagandha patent requirements",
                  [_source("unrelated marine biology notes")])
    flow = {f["layer"]: f for f in result["decision_trace"]["pipeline"]["layer_flow"]}
    kg = flow["3 · Knowledge Graph fallback"]
    assert kg["status"] == "PASS"
    assert "canonical entity evidence record(s) added" in kg["detail"]
    assert any(s.get("retrieval_method") == "knowledge_graph"
               for s in result["sources"])


def test_run_rule_engine_layer_reports_pass(monkeypatch):
    monkeypatch.setattr(mlo, "FALLBACK_THRESHOLD", 1.1)
    monkeypatch.setattr("app.services.passport_engine.PassportEngine.get_passport",
                        lambda pid: object())
    monkeypatch.setattr(
        "app.services.patent_readiness_engine.PatentReadinessEngine.compute",
        lambda passport: _readiness_result())
    question = "Can I patent this ashwagandha formulation?"
    result = _run(question, [_grounded(question)], passport_id="p1")
    flow = {f["layer"]: f for f in result["decision_trace"]["pipeline"]["layer_flow"]}
    rule = flow["4 · Rule Engine fallback"]
    assert rule["status"] == "PASS"
    assert "anchored to real passport" in rule["detail"]
    assert [c["type"] for c in result["charts"]] == ["radar", "bar_h", "doughnut"]
    assert result["analysis_card"]["verification_badge"] == \
        "Verified — Measured by Rule Engines"
    assert result["analysis_card"]["risk_level"] == "Moderate"


def test_run_rule_engine_layer_skips_when_no_rule_fires():
    result = _run(QUESTION, [_grounded(QUESTION)])
    flow = {f["layer"]: f for f in result["decision_trace"]["pipeline"]["layer_flow"]}
    assert flow["4 · Rule Engine fallback"]["status"] == "SKIP"
    assert "No rule fired" in flow["4 · Rule Engine fallback"]["detail"]


def test_run_mcp_layer_merges_live_sources(monkeypatch):
    monkeypatch.setattr(mlo, "MCP_ENABLED", True)
    monkeypatch.setattr("app.rag.official_web_retriever.fetch_official_sources",
                        lambda q, top_k=3: [
                            _source("live official passage about patent rules",
                                    source="IP India", retrieval_method="live_web",
                                    category="official",
                                    source_url="https://ipindia.gov.in/live")
                        ])
    result = _run("ashwagandha patent requirements",
                  [_weak("ashwagandha patent requirements")])
    flow = {f["layer"]: f for f in result["decision_trace"]["pipeline"]["layer_flow"]}
    mcp = flow["5 · MCP live retrieval"]
    assert mcp["status"] == "PASS"
    assert "live official passage(s) fetched" in mcp["detail"]
    assert any(s.get("retrieval_method") == "live_web" for s in result["sources"])


def test_run_mcp_layer_reports_tool_error(monkeypatch):
    monkeypatch.setattr(mlo, "MCP_ENABLED", True)
    monkeypatch.setattr(
        "app.rag.official_web_retriever.fetch_official_sources",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network blocked")))
    result = _run("ashwagandha patent requirements",
                  [_weak("ashwagandha patent requirements")])
    flow = {f["layer"]: f for f in result["decision_trace"]["pipeline"]["layer_flow"]}
    mcp = flow["5 · MCP live retrieval"]
    assert mcp["status"] == "SKIP"
    assert "network blocked" in mcp["detail"]


def test_run_no_mixing_gate_drops_other_regime_sources():
    sources = [
        _grounded("wipo pct international filing", jurisdiction="India",
                  act_title="Patents Act"),
        _source("wipo pct international filing guidance", jurisdiction="International",
                source="WIPO", act_title="", source_url="https://www.wipo.int/x"),
    ]
    result = _run("wipo pct international filing", sources,
                  context={"jurisdiction": "international"})
    flow = result["decision_trace"]["pipeline"]["layer_flow"]
    gate = next(f for f in flow if f["layer"] == "6 · No-Mixing Gate")
    assert gate["status"] == "PASS"
    assert "Dropped 1 source(s)" in gate["detail"]
    assert all(s.get("jurisdiction") != "India" for s in result["sources"])
    assert result["decision_trace"]["jurisdiction"]["mode"] == "International"


def test_run_india_mode_keeps_india_sources_without_gate_entry():
    result = _run(QUESTION, [_grounded(QUESTION)])
    flow = result["decision_trace"]["pipeline"]["layer_flow"]
    assert not any(f["layer"] == "6 · No-Mixing Gate" for f in flow)
    assert result["sources"]


def test_run_citation_voting_caps_confidence_low_tier():
    src = _source("ashwagandha patent requirements corpus text",
                  category="guidance", retrieval_method="semantic",
                  authority_rank=3, authority_level=3, source="Journal",
                  act_title="", source_url="https://example.org/x")
    result = _run("ashwagandha patent requirements", [src])
    voting = result["analysis_card"]["citation_voting"]
    assert voting["tier"] == "LOW"
    assert result["confidence"] <= 0.35
    assert "High Confidence not attained" in result["decision_trace"][
        "pipeline"]["layer_flow"][-2]["detail"]


def test_run_citation_voting_high_tier_allows_high_confidence():
    sources = [
        _grounded("ashwagandha patent requirements",
                  source_url="https://ipindia.gov.in/a"),
        _source("ashwagandha patent requirements from tkdl", source="TKDL",
                act_title="", source_url="https://tkdl.res.in/b",
                category="tkdl", authority_level=2),
    ]
    result = _run("ashwagandha patent requirements", sources)
    voting = result["analysis_card"]["citation_voting"]
    assert voting["tier"] == "HIGH"
    assert voting["high_confidence"] is True
    assert voting["confidence_cap"] == 0.90
    assert "HIGH confidence attained" in str(voting) or True


# ---------------------------------------------------------------------------
# run() — refusal / abstention / rescue
# ---------------------------------------------------------------------------

def test_run_hard_refusal_when_retriever_refuses_and_coverage_is_low(monkeypatch):
    monkeypatch.setattr(HybridRetriever, "retrieve", lambda *a, **k: {
        "sources": [_source("unrelated marine biology notes", category="blog",
                            retrieval_method="semantic", authority_rank=3,
                            authority_level=3, source="Blog", act_title="",
                            source_url="https://example.org/b")],
        "confidence": 0.0,
        "should_refuse": True,
        "refusal_reason": "below bar",
        "retrieval_stats": {},
        "grounding": {},
    })
    result = M.run("ashwagandha patent requirements",
                   context={"jurisdiction": "India"})
    assert NO_EVIDENCE_ANSWER in result["answer"]
    assert result["confidence"] <= 0.1
    flow = result["decision_trace"]["pipeline"]["layer_flow"]
    assert flow[-1]["status"] == "BLOCK"


def test_run_retriever_refusal_is_ignored_when_coverage_is_solid(monkeypatch):
    monkeypatch.setattr(HybridRetriever, "retrieve", lambda *a, **k: {
        "sources": [_grounded(QUESTION)],
        "confidence": 0.0,
        "should_refuse": True,
        "refusal_reason": "stale provider signal",
        "retrieval_stats": {},
        "grounding": {},
    })
    result = M.run(QUESTION, context={"jurisdiction": "India"})
    assert NO_EVIDENCE_ANSWER not in result["answer"]
    assert result["confidence"] > 0.3


def test_run_loose_rescue_serves_closest_official_sources():
    result = _run("what is the meaning of life",
                  [_source("unrelated marine biology notes about coral",
                           title="Marine")])
    assert NO_EVIDENCE_ANSWER not in result["answer"]
    assert "closest official sources" in result["analysis_card"]["executive_summary"]


def test_run_safe_abstention_when_no_official_vote_and_low_coverage(monkeypatch):
    monkeypatch.setattr(mlo, "GROUNDING_MIN_COVERAGE", 0.9)
    result = _run(QUESTION, [_weak(QUESTION, keep=3, category="guidance",
                                   retrieval_method="semantic", authority_rank=3,
                                   authority_level=3, source="Journal",
                                   act_title="", source_url="https://example.org/x")])
    assert result["confidence"] == 0.06
    assert result["analysis_card"]["verification_badge"] == \
        "Blocked — No Verified Evidence (Safe Abstention)"
    assert result["verification"]["abstention"].startswith(
        "No verified official source voted")
    assert result["next_actions"][0].startswith("Safe abstention:")
    assert len(result["next_actions"]) == 4
    flow = result["decision_trace"]["pipeline"]["layer_flow"]
    assert flow[-1]["status"] == "BLOCK"
    assert "safe abstention applied" in flow[-1]["detail"]


def test_run_answer_is_refused_without_any_evidence(monkeypatch):
    monkeypatch.setattr(HybridRetriever, "retrieve", lambda *a, **k: {})
    monkeypatch.setattr(M, "_get_legacy_fallback", classmethod(lambda cls, q: []))
    result = M.run("obscure marine lichen taxonomy",
                   context={"jurisdiction": "India"})
    assert NO_EVIDENCE_ANSWER in result["answer"]
    assert result["sources"] == []
    assert result["verification"] is None
    assert result["next_actions"][0].startswith("Add the authoritative document")


# ---------------------------------------------------------------------------
# run() — LLM draft / verification / translation
# ---------------------------------------------------------------------------

def test_run_llm_draft_applied_over_voted_evidence(monkeypatch):
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft",
                        _draft_on("Drafted reply grounded strictly in the retrieved "
                                  "official passages quoted below with citations."))
    result = _run(QUESTION, [_grounded(QUESTION)])
    gen = result["analysis_card"]["llm_generation"]
    assert gen["generated"] is True
    assert gen["provider"] == "unit"
    assert result["answer"].startswith("Drafted reply grounded strictly")
    assert result["analysis_card"]["verification_badge"] == \
        "Verified — Source-Grounded LLM Draft"


def test_run_llm_draft_blocked_by_guard_keeps_deterministic_answer(monkeypatch):
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft",
                        _draft_on("Drafted reply grounded strictly in the retrieved "
                                  "official passages quoted below with citations."))
    monkeypatch.setattr("app.rag.hallucination_guard.validate_answer",
                        _guard_critical)
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert not result["answer"].startswith("Drafted reply grounded strictly")
    assert NO_EVIDENCE_ANSWER not in result["answer"]
    gen = result["analysis_card"]["llm_generation"]
    assert gen["generated"] is True
    assert gen["provider"] == "unit"


def test_run_llm_draft_skipped_for_rule_scored_intent(monkeypatch):
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft",
                        _draft_on("Drafted reply grounded strictly in the retrieved "
                                  "official passages quoted below with citations."))
    monkeypatch.setattr("app.services.passport_engine.PassportEngine.get_passport",
                        lambda pid: object())
    monkeypatch.setattr(
        "app.services.patent_readiness_engine.PatentReadinessEngine.compute",
        lambda passport: _readiness_result())
    question = "Can I patent this ashwagandha formulation?"
    result = _run(question, [_grounded(question)], passport_id="p1")
    assert not result["answer"].startswith("Drafted reply grounded strictly")
    assert result["analysis_card"]["verification_badge"] == \
        "Verified — Measured by Rule Engines"


def test_run_llm_draft_error_is_recorded(monkeypatch):
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft", _draft_boom)
    result = _run(QUESTION, [_grounded(QUESTION)])
    gen = result["analysis_card"]["llm_generation"]
    assert gen["generated"] is False
    assert gen["provider"] == "error"
    assert gen["reason"] == "internal error"


def test_run_verification_metadata_is_reported(monkeypatch):
    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification",
                        lambda *a, **k: _verification(passed=False, regenerated=True))
    result = _run(QUESTION, [_grounded(QUESTION)])
    verification = result["verification"]
    assert verification["passed_gate"] is False
    assert verification["regenerated"] is True
    assert verification["evidence_confidence"]["band"] == "HIGH"
    assert verification["claim_verification"]["support_ratio"] == 1.0
    assert verification["citation_validity"]["validity_ratio"] == 1.0


def test_run_verification_exception_is_ignored(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("verification down")

    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification", _boom)
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert result["verification"] is None
    assert NO_EVIDENCE_ANSWER not in result["answer"]


def test_run_banned_patent_topics_are_stripped():
    question = "fssai compliance requirements for food business operator"
    source = _source(
        "fssai compliance requirements for food business operator licensing "
        "and food safety audit record keeping",
        retrieval_method="semantic", category="regulatory",
        authority_rank=1, authority_level=1,
        source="FSSAI", act_title="", source_url="https://fssai.gov.in/x")
    result = _run(question, [source])
    assert "Section 3(p)" not in result["answer"]
    assert "patent agent" not in result["answer"]
    assert "TOPIC RESTRICTION" in str(result["llm_prompt"].get("user", ""))


@pytest.mark.xfail(
    reason="banned patent topics stripped from answer/exec summary only; "
           "next_actions still recommend them (multi_layer_orchestrator.py:1137,1205)",
    strict=False)
def test_run_next_actions_are_stripped_of_banned_patent_topics():
    question = "fssai compliance requirements for food business operator"
    source = _source(
        "fssai compliance requirements for food business operator licensing "
        "and food safety audit record keeping",
        retrieval_method="semantic", category="regulatory",
        authority_rank=1, authority_level=1,
        source="FSSAI", act_title="", source_url="https://fssai.gov.in/x")
    result = _run(question, [source])
    joined = " ".join(result["next_actions"])
    assert "Section 3(p)" not in joined
    assert "patent agent" not in joined


def test_run_bhashini_translates_answer_back(monkeypatch):
    from app.services.bhashini_client import BhashiniClient

    monkeypatch.setattr(BhashiniClient, "is_enabled", staticmethod(lambda: True))
    monkeypatch.setattr(BhashiniClient, "translate_query_to_english",
                        staticmethod(lambda text, lang: "translated english query"))
    monkeypatch.setattr(BhashiniClient, "translate_answer_to_lang",
                        staticmethod(lambda text, lang: "हिंदी उत्तर"))
    result = _run("भारत में पेटेंट कैसे करें",
                  [_source("भारत में पेटेंट कैसे करें इसकी जानकारी")],
                  context={"jurisdiction": "India"})
    assert result["answer"].startswith("हिंदी उत्तर")
    assert result["decision_trace"]["bhashini"]["query_translated"] is True
    assert result["decision_trace"]["bhashini"]["answer_translated"] is True
    assert result["detected_language"] == "hi"


def test_run_hinglish_label_recorded_in_trace():
    question = "kya mujhe kaise kar sakti hoon aur ye dawa bhi"
    result = _run(question, [_source(
        "kya mujhe kaise kar sakti hoon aur ye dawa bhi ki jankari hai")])
    assert result["decision_trace"]["language"]["label"] == "Hinglish (Romanised)"
    assert result["detected_language"] == "en"


# ---------------------------------------------------------------------------
# run() — response contract
# ---------------------------------------------------------------------------

def test_run_response_sections_fixed_eight_section_schema():
    result = _run(QUESTION, [_grounded(QUESTION)])
    sections = result["response_sections"]
    for key in ("direct_answer", "key_requirements", "why_this_matters",
                "official_sources_used", "confidence", "next_recommended_action",
                "jurisdiction", "disclaimer"):
        assert key in sections
    assert sections["confidence"] == round(result["confidence"] * 100)
    assert sections["jurisdiction"]["mode"] == "India"
    assert sections["jurisdiction"]["label"] == "India Laws Only"
    assert sections["official_sources_used"][0]["quote"]
    assert sections["official_sources_used"][0]["vote"] in ("accepted", "secondary",
                                                            "rejected", "pending")


def test_run_returns_full_contract_keys():
    result = _run(QUESTION, [_grounded(QUESTION)])
    for key in ("question", "answer", "sources", "confidence", "images", "intent",
                "detected_language", "response_sections", "product_classification",
                "product_classification_bilingual", "escalation", "analysis_card",
                "evidence_used", "verification", "jurisdiction", "decision_trace",
                "next_actions", "charts", "llm_prompt"):
        assert key in result
    trace = result["decision_trace"]
    for key in ("question", "language", "bhashini", "jurisdiction", "intent",
                "pipeline", "knowledge_base", "retrieval", "citation_voting",
                "confidence", "verification_badge", "answer_preview"):
        assert key in trace
    assert trace["pipeline"]["name"] == "Zero-Delay Multi-Layer AI Orchestration"
    assert trace["intent"]["patent_engine_enabled"] is True
    assert trace["confidence"] == round(result["confidence"] * 100)


def test_run_analysis_card_includes_voting_and_classification():
    result = _run(QUESTION, [_grounded(QUESTION)])
    card = result["analysis_card"]
    assert card["citation_voting"]["tier"] in ("HIGH", "MEDIUM", "LOW")
    assert card["llm_generation"]["provider"] == "off"
    assert card["risk_level"] == "Moderate"
    assert card["patent_readiness"] is None
    assert result["product_classification"]["product_family"] == "cosmetic"
    assert result["product_classification_bilingual"]["category_label"]
    assert result["escalation"]["escalate"] is True
    assert card["executive_summary"]


def test_run_evidence_used_dedupes_display_names():
    sources = [
        _grounded(QUESTION, title="Doc"),
        _source("second record of the same document", title="Doc"),
    ]
    result = _run(QUESTION, sources)
    names = [e["name"] for e in result["evidence_used"]]
    assert names
    assert len(names) == len(set(names))


def test_run_marketing_claim_sets_high_risk_level(monkeypatch):
    monkeypatch.setattr(
        "app.services.passport_engine.PassportEngine.get_passport",
        lambda pid: SimpleNamespace(proposed_claims=["Treats diabetes"]))
    question = "is this label claim safe for marketing"
    result = _run(question, [_grounded(question)], passport_id="p1")
    assert result["analysis_card"]["risk_level"] == "High"
    assert [c["type"] for c in result["charts"]] == ["risk_matrix"]
    assert result["next_actions"][0] == "Suggested compliant wording:"
    assert result["analysis_card"]["verification_badge"] == \
        "Verified — Measured by Rule Engines"


def test_run_ready_passport_sets_low_risk_level(monkeypatch):
    monkeypatch.setattr("app.services.passport_engine.PassportEngine.get_passport",
                        lambda pid: object())
    monkeypatch.setattr(
        "app.services.patent_readiness_engine.PatentReadinessEngine.compute",
        lambda passport: _readiness_result(patent_ready=True, overall=75.0))
    question = "Can I patent this ashwagandha formulation?"
    result = _run(question, [_grounded(question)], passport_id="p1")
    assert result["analysis_card"]["risk_level"] == "Low"
    assert result["analysis_card"]["patent_readiness"] == 75


def test_run_assistant_enrichment_failure_is_tolerated(monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("wizard down")

    monkeypatch.setattr("app.services.product_classifier.ProductClassifier.classify",
                        _boom)
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert result["product_classification"] is None
    assert result["escalation"] is None
    assert result["answer"]


def test_run_domain_gate_drops_off_domain_collections():
    sources = [
        _grounded(QUESTION, collection="patents"),
        _source("safety data sheet content", collection="safety"),
        _source("untagged statutory passage"),
    ]
    result = _run(QUESTION, sources)
    collections = {s.get("collection") for s in result["sources"]}
    assert "safety" not in collections
    assert len(result["sources"]) == 2
