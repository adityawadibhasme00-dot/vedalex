from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.rag.retrieval_pipeline import HybridRetriever
from app.services import copilot_orchestrator as co
from app.services.ai_copilot import NO_EVIDENCE_ANSWER, AICopilot
from app.services.copilot_orchestrator import AICopilotOrchestrator as Orchestrator
from app.services.retrieval_engine import HybridRetrievalEngine

QUESTION = "What are the patent requirements for Ashwagandha formulation in India?"


def _source(content, **kw):
    base = {
        "content": content,
        "source": "India Code",
        "title": "India Code",
        "act_title": "Patents Act, 1970",
        "authority": "Government of India",
        "authority_rank": 1,
        "category": "statutory",
        "retrieval_method": "statutory",
        "jurisdiction": "India",
        "source_url": "https://www.indiacode.nic.in/act",
    }
    base.update(kw)
    return base


def _grounded(question, **kw):
    tokens = " ".join(sorted(co._meaningful_tokens(question)))
    return _source(f"{tokens} section 3(p) of the patents act covers these requirements", **kw)


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
        "missing_evidence": ["stability data", "clinical studies"],
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
    table = SimpleNamespace(
        total_claims=2,
        supported_count=2 if passed else 1,
        contradicted_count=0,
        not_enough_count=0,
        support_ratio=1.0 if passed else 0.4,
        all_supported=passed,
        has_contradictions=False,
        claims=[
            SimpleNamespace(
                claim_text="claim one", claim_type="factual", status="SUPPORTED",
                entailment_score=0.9, best_source="src", citations_found=1,
                explanation="supported by evidence",
            )
        ],
    )
    report = SimpleNamespace(
        total_citations=1, valid_citations=1, invalid_citations=0,
        validity_ratio=1.0, all_valid=True,
        checks=[
            SimpleNamespace(
                citation_text="[1] Patents Act", document_found=True,
                section_found=True, source_matched=True, valid=True, note="ok",
            )
        ],
    )
    evidence = SimpleNamespace(
        overall=0.8, band="HIGH",
        signals=[SimpleNamespace(name="coverage", score=1.0, weight=1, description="d")],
    )
    return SimpleNamespace(
        original_answer="", final_answer=final_answer,
        verification_table=table, citation_report=report,
        evidence_confidence=evidence, passed_gate=passed, gate_reason=gate_reason,
        regenerated=regenerated, regeneration_count=1 if regenerated else 0,
        removed_claims=[], unsupported_claims=[],
    )


def _guard_ok(answer, sources, question, confidence):
    return SimpleNamespace(
        risk_level=SimpleNamespace(value="low"), grounded=True,
        coverage_ratio=0.9, citation_count=1, violations=[], recommendations=[],
    )


def _guard_critical(answer, sources, question, confidence):
    return SimpleNamespace(
        risk_level=SimpleNamespace(value="critical"), grounded=False,
        coverage_ratio=0.0, citation_count=0,
        violations=["unsupported claim"], recommendations=["add sources"],
    )


def _draft_off(*args, **kwargs):
    return {"generated": False, "text": None, "provider": "off", "model": None,
            "reason": "disabled in tests"}


def _guard_pass_then_critical():
    calls = {"n": 0}

    def _guard(answer, sources, question, confidence):
        calls["n"] += 1
        if calls["n"] == 1:
            return _guard_ok(answer, sources, question, confidence)
        return _guard_critical(answer, sources, question, confidence)

    return _guard


def _draft_on(text="A grounded draft answer built only from retrieved passages "
                   "and citing every claim it makes in the answer text."):
    def _inner(*args, **kwargs):
        return {"generated": True, "text": text, "provider": "unit", "model": "m",
                "reason": ""}
    return _inner


def _draft_boom(*args, **kwargs):
    raise RuntimeError("llm unavailable")


@pytest.fixture(autouse=True)
def _pipeline_defaults(monkeypatch):
    monkeypatch.delenv("IPSAKTI_ENABLE_LIVE_WEB", raising=False)
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft", _draft_off)
    monkeypatch.setattr("app.rag.hallucination_guard.validate_answer", _guard_ok)
    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification",
                        lambda *a, **k: _verification())
    yield


def _run(question, sources=None, **kw):
    if sources is None:
        return Orchestrator.run(question, **kw)
    return Orchestrator.run(question, retrieved_sources=list(sources), **kw)


# ---------------------------------------------------------------------------
# intent / jurisdiction / token helpers
# ---------------------------------------------------------------------------

INTENT_CASES = [
    ("where are white space opportunities in this market", "white_space"),
    ("ashwagandha sourcing origin geography in india", "botanical_origin"),
    ("is this label claim safe for marketing", "marketing_claim"),
    ("can i patent this formulation", "patentability"),
    ("prior art search for tulsi extract", "prior_art"),
    ("roadmap for my regulatory journey", "regulatory_roadmap"),
    ("fssai compliance requirements", "compliance"),
    ("what scientific evidence supports this", "evidence_strength"),
    ("tell me about ashwagandha", "general"),
]


@pytest.mark.parametrize("question,expected", INTENT_CASES)
def test_characterization_classify_intent_routes_to_surface_intent(question, expected):
    assert co.classify_intent(question)["id"] == expected


def test_meaningful_tokens_drop_framing_and_hinglish_words():
    tokens = co._meaningful_tokens("kya mujhe kar sakti hoon patent filing")
    assert "patent" in tokens
    assert "filing" in tokens
    assert "kya" not in tokens
    assert "mujhe" not in tokens
    assert "the" not in tokens


def test_detect_jurisdiction_prefers_explicit_toggle():
    info = co.detect_jurisdiction("patent rules", {"jurisdiction": "canada"})
    assert info["detected"] == "Canada"
    assert info["cue"] == "explicit jurisdiction toggle"
    assert info["retrieval_jurisdiction"] == "Canada"


def test_detect_jurisdiction_reads_keyword_cues():
    assert co.detect_jurisdiction("fda dshea dietary supplement rules")["detected"] == "United States"
    assert co.detect_jurisdiction("health canada nhp licence")["detected"] == "Canada"
    assert co.detect_jurisdiction("wipo pct international filing")["detected"] == "International"
    assert co.detect_jurisdiction("ayurveda aahara rules")["detected"] == "India"


def test_detect_jurisdiction_defaults_to_india():
    info = co.detect_jurisdiction("tell me about product quality checks")
    assert info["detected"] == "India"
    assert info["cue"] == "default (India)"
    assert info["applied_filters"] == ["jurisdiction"]


def test_detect_jurisdiction_international_has_no_retrieval_filter():
    info = co.detect_jurisdiction("wipo madrid protocol")
    assert info["retrieval_jurisdiction"] is None
    assert info["applied_filters"] == []


def test_reorder_for_jurisdiction_prefers_matching_sources():
    sources = [
        _source("us text", jurisdiction="United States"),
        _source("in text", jurisdiction="India"),
        _source("intl text", jurisdiction="International"),
    ]
    ordered = co._reorder_for_jurisdiction(sources, "India")
    assert [s["jurisdiction"] for s in ordered] == ["India", "International", "United States"]
    assert co._reorder_for_jurisdiction([], "India") == []


def test_reorder_for_jurisdiction_international_mode():
    sources = [
        _source("in text", jurisdiction="India"),
        _source("ca text", jurisdiction="Canada"),
    ]
    ordered = co._reorder_for_jurisdiction(sources, "International")
    assert ordered[0]["jurisdiction"] == "Canada"


@pytest.mark.parametrize("raw,expected", [("2", 2), (1, 1), (None, 3), ("abc", 3), ("", 3)])
def test_authority_level_parsing(raw, expected):
    assert co._authority_level({"authority_rank": raw}) == expected


def test_authority_level_falls_back_to_authority_level_key():
    assert co._authority_level({"authority_level": "1"}) == 1


def test_rank_by_authority_orders_by_jurisdiction_statute_rank_score():
    sources = [
        _source("secondary", jurisdiction="United States", category="blog",
                authority_rank=3, score=0.9),
        _source("guidance", jurisdiction="India", category="guidance",
                authority_rank=3, score=0.5),
        _source("act", jurisdiction="India", category="statutory",
                authority_rank=1, score=0.2),
        _source("unranked", jurisdiction="", score="not-a-number"),
    ]
    ranked = co._rank_by_authority(sources, "India")
    assert ranked[0]["category"] == "statutory"
    assert ranked[1]["content"] == "guidance"
    assert ranked[2]["content"] == "unranked"
    assert ranked[3]["jurisdiction"] == "United States"
    assert co._rank_by_authority([], "India") == []


def test_rank_by_authority_international_prefers_intl_bucket():
    sources = [
        _source("in", jurisdiction="India", category="statutory", authority_rank=1),
        _source("wipo", jurisdiction="International", category="official", authority_rank=3),
    ]
    ranked = co._rank_by_authority(sources, "International")
    assert ranked[0]["jurisdiction"] == "International"


@pytest.mark.parametrize("kw,expected", [
    ({"source": "Charaka Samhita"}, "Classical Text"),
    ({"source": "WIPO PATENTSCOPE"}, "Patent / TKDL"),
    ({"source": "PubMed journal study"}, "Scientific"),
    ({"source": "Ministry of AYUSH gazette"}, "Government"),
    ({"source": "misc registry"}, "Official"),
])
def test_source_kind_classification(kw, expected):
    payload = {"act_title": "", "authority": ""}
    payload.update(kw)
    assert co._source_kind(_source("", **payload)) == expected


def test_source_display_name_precedence():
    assert co._source_display_name({"act_title": "Act", "source": "S", "title": "T"}) == "Act"
    assert co._source_display_name({"source": "S", "title": "T"}) == "S"
    assert co._source_display_name({"title": "T"}) == "T"
    assert co._source_display_name({}) == "Retrieved Source"


def test_top_citation_builds_verified_line():
    src = _source("c", section="3(p)", authority="CGPDTM")
    line = co._top_citation([src])
    assert line.startswith("Verified citation:")
    assert "3(p)" in line
    assert "https://www.indiacode.nic.in/act" in line
    assert co._top_citation([]) == ""


def test_top_citation_hides_default_authority():
    src = _source("c", authority="Official Source", source_url="")
    assert "Official Source" not in co._top_citation([src])


def test_get_passport_handles_missing_and_broken_lookup():
    assert co._get_passport(None, "q") is None
    assert co._get_passport("missing", "q") is None

    def _boom(_pid):
        raise RuntimeError("store down")

    with patch.object(co.PassportEngine, "get_passport", _boom):
        assert co._get_passport("p1", "q") is None

    sentinel = object()
    with patch.object(co.PassportEngine, "get_passport", lambda _pid: sentinel):
        assert co._get_passport("p1", "q") is sentinel


def test_readiness_returns_engine_result():
    with patch.object(co.PatentReadinessEngine, "compute",
                      lambda *_a, **_k: {"overall_readiness": 10}):
        assert co._readiness("passport") == {"overall_readiness": 10}


def test_readiness_swallows_engine_errors():
    def _boom(*_a, **_k):
        raise RuntimeError("engine down")

    with patch.object(co.PatentReadinessEngine, "compute", _boom):
        assert co._readiness("passport") is None


def test_load_knowledge_json_reads_and_misses():
    data = co._load_knowledge_json("india_origin.json")
    assert isinstance(data, list) and data
    assert co._load_knowledge_json("does_not_exist.json") is None


# ---------------------------------------------------------------------------
# chart builders
# ---------------------------------------------------------------------------

def test_radar_chart_percentages():
    chart = co._radar_chart(_readiness_result())
    assert chart["type"] == "radar"
    assert len(chart["labels"]) == 8
    assert len(chart["values"]) == 8
    assert all(0 <= v <= 100 for v in chart["values"])
    assert "Overall" in chart["subtitle"]


def test_similarity_chart_includes_top_family_insight():
    chart = co._similarity_chart(_readiness_result())
    assert chart["type"] == "bar_h"
    assert chart["values"] == [61]
    assert "Family ABC" in chart["insights"][0]


def test_similarity_chart_without_families_reports_no_overlap():
    chart = co._similarity_chart(_readiness_result(similar=False))
    assert chart["insights"][0].startswith("No close prior-art")


def test_evidence_donut_splits_earned_and_gaps():
    chart = co._evidence_donut(_readiness_result())
    assert chart["type"] == "doughnut"
    assert chart["values"][0] == 3
    assert chart["values"][1] == 7
    assert chart["insights"]


def test_compliance_gauge_averages_three_components():
    chart = co._compliance_gauge(_readiness_result())
    assert chart["type"] == "gauge"
    assert chart["values"] == [60]
    assert "Section 3(p) status: Flagged" in chart["description"]


def test_timeline_chart_without_passport_marks_prior_art_done():
    chart = co._timeline_chart(None)
    assert chart["type"] == "timeline"
    assert chart["values"][0] == 2
    assert chart["current"] is None
    assert chart["insights"] == ["All primary gates completed."]


def test_timeline_chart_with_ready_passport():
    r = _readiness_result(patent_ready=True, overall=75.0)
    chart = co._timeline_chart(r)
    assert chart["current"] in ("Evidence", "Patent", "ABS")
    assert chart["insights"]


def test_india_heatmap_counts_verified_origins():
    chart = co._india_heatmap()
    assert chart["type"] == "india_heatmap"
    assert chart["values"][0] + chart["values"][1] == len(chart["states"])
    assert "verified" in chart["insights"][0]


def test_risk_matrix_chart_reflects_red_position():
    chart = co._risk_matrix_chart({"counts": {"red": 2, "yellow": 1, "green": 0}})
    assert chart["current"] == 2
    assert chart["values"] == [0, 1, 2]
    calm = co._risk_matrix_chart({"counts": {"red": 0, "yellow": 0, "green": 3}})
    assert calm["current"] == 0


def test_white_space_chart_reads_dataset():
    chart = co._white_space_chart()
    assert chart is not None
    assert chart["type"] == "opportunity_heatmap"
    assert "herbs" in chart and "cells" in chart


def test_white_space_chart_returns_none_without_dataset():
    with patch.object(co, "_load_knowledge_json", lambda _n: None):
        assert co._white_space_chart() is None


# ---------------------------------------------------------------------------
# claim firewall / answer builders
# ---------------------------------------------------------------------------

def test_claim_firewall_flags_therapeutic_wording():
    out = co._claim_firewall(["Treats diabetes naturally", "Supports immunity"])
    assert out["overall"] == "HIGH_RISK"
    assert out["counts"]["red"] == 1
    assert out["counts"]["green"] == 1
    assert out["results"][0]["risk"] == "HIGH_RISK"
    assert "supports" in out["suggested"][0].lower()


def test_claim_firewall_safe_claims_get_disclaimer_suggestion():
    out = co._claim_firewall(["Supports immune function"])
    assert out["overall"] == "SAFE"
    assert out["counts"]["red"] == 0
    assert "not intended to diagnose" in out["suggested"][0]


def test_general_grounded_summary_without_sources():
    assert co._general_grounded_summary("anything", []) == ""


def test_general_grounded_summary_quotes_overlapping_sources():
    sources = [
        _source("Ashwagandha formulation patent requirements are listed here.", title="Doc"),
        _source("completely unrelated marine biology notes", title="Other"),
    ]
    out = co._general_grounded_summary("ashwagandha patent requirements", sources)
    assert out.startswith("Based on the retrieved official sources:")
    assert "Doc" in out
    assert "Other" not in out


def test_general_grounded_summary_strict_mode_drops_non_overlapping():
    sources = [_source("marine biology notes only", title="Other")]
    assert co._general_grounded_summary("ashwagandha patent", sources) == ""


def test_general_grounded_summary_loose_mode_labels_closest_sources():
    sources = [
        _source("marine biology notes only", title="Other", authority_rank=1),
        _source("another unrelated passage about shipping", title="Shipping", authority_rank=3),
    ]
    out = co._general_grounded_summary("ashwagandha patent", sources, loose=True)
    assert out.startswith("I could not map your exact wording")
    assert "Other" in out
    assert "Shipping" not in out


def test_general_grounded_summary_loose_without_authoritative_pool():
    sources = [_source("unrelated passage", title="Generic", authority_rank=None)]
    out = co._general_grounded_summary("ashwagandha patent", sources, loose=True)
    assert out.startswith("I could not map your exact wording")


def test_general_grounded_summary_appends_detail_suffixes():
    src = _source(
        "ashwagandha patent requirements detail",
        title="Entry",
        uniprot_accession="P12345",
        ncbi_gene_id="666",
        pubchem_cid="999",
        pmid="123456",
        section_heading="Section 3(p)",
    )
    out = co._general_grounded_summary("ashwagandha patent requirements", [src])
    assert "[UniProt P12345, NCBI Gene 666, PubChem CID 999, PMID 123456, Section 3(p)]" in out


def test_general_grounded_summary_notes_overflow_sources():
    sources = [
        _source(f"ashwagandha patent requirement number {i} text", title=f"D{i}")
        for i in range(6)
    ]
    out = co._general_grounded_summary("ashwagandha patent requirements", sources)
    assert "of 6 sources had direct keyword overlap" in out


def test_general_grounded_summary_skips_source_without_matching_content():
    sources = [_source("   ", act_title="", source="",
                       title="ashwagandha patent notes")]
    assert co._general_grounded_summary("ashwagandha patent", sources) == ""


def test_general_grounded_summary_loose_mode_returns_empty_without_quotes():
    sources = [_source("   ", authority_rank=1)]
    assert co._general_grounded_summary("ashwagandha patent", sources, loose=True) == ""


def test_source_bullets_quote_and_reference():
    sources = [
        _source("a" * 400, act_title="", source="", title="Doc",
                section_reference="Section 3(p)"),
        _source("short passage", act_title="", source="", title="Doc2",
                section_heading="Heading"),
        _source("   ", act_title="", source="", title="Blank"),
    ]
    bullets = co._source_bullets(sources, "q")
    assert len(bullets) == 2
    assert bullets[0].startswith("• Doc · Section 3(p):")
    assert bullets[0].endswith("…")
    assert "Heading" in bullets[1]
    assert co._source_bullets([], "q") == []


def test_source_bullets_respects_limit():
    sources = [_source(f"passage {i}", act_title="", source="", title=f"D{i}")
               for i in range(6)]
    assert len(co._source_bullets(sources, "q", limit=2)) == 2


def test_source_citations_dedupe_and_limit():
    sources = [
        _source("one", act_title="", source="", title="Doc", jurisdiction="India",
                authority="CGPDTM"),
        _source("two", act_title="", source="", title="Doc"),
        _source("three", act_title="", source="", title="Other", section_heading="S.1"),
    ] + [_source(f"x{i}", act_title="", source="", title=f"T{i}") for i in range(8)]
    lines = co._source_citations(sources, limit=3)
    assert len(lines) == 3
    assert lines[0].startswith("[1] Doc")
    assert "CGPDTM" in lines[0]
    titles = [ln.split(" — ")[0] for ln in lines]
    assert len(set(titles)) == len(titles)


def test_source_citations_skips_blank_names():
    src = {"content": "c", "act_title": "", "source": "", "title": ""}
    assert co._source_citations([src]) == ["[1] Retrieved Source"]


def test_build_structured_answer_sections():
    out = co.build_structured_answer(
        "Summary text.", "Verified citation: Act", co.DISCLAIMER,
        [_source("quoted passage", title="Doc")], "q", intent_id="patentability",
        r=_readiness_result(),
    )
    assert out.startswith("SUMMARY\n")
    assert "WHAT THE RULES SAY" in out
    assert "NEXT STEPS" in out
    assert "EVIDENCE CITED" in out
    assert co.DISCLAIMER in out


def test_build_structured_answer_refused_summary_omits_disclaimer():
    out = co.build_structured_answer(
        NO_EVIDENCE_ANSWER, "Verified citation: Act", co.DISCLAIMER, [], "q",
    )
    assert NO_EVIDENCE_ANSWER in out
    assert co.DISCLAIMER not in out


def test_build_structured_answer_falls_back_to_plain_citation():
    out = co.build_structured_answer(
        "", "Verified citation: Act", "", [], "q", intent_id="general",
    )
    assert "VERIFIED CITATION" in out
    assert "Verified citation: Act" in out


def test_build_structured_answer_empty_returns_placeholder():
    out = co.build_structured_answer("", "", "", [], "q")
    assert out == "No evidence available."


def test_build_structured_answer_can_skip_bullets():
    out = co.build_structured_answer(
        "Summary text.", "", co.DISCLAIMER,
        [_source("quoted passage", title="Doc")], "q", include_bullets=False,
    )
    assert "WHAT THE RULES SAY" not in out


def test_build_structured_answer_surfaces_top_citation_when_no_structured_evidence():
    out = co.build_structured_answer("Summary only.", "Verified citation: Act", "", [], "q")
    assert "VERIFIED CITATION" in out


def test_executive_summary_without_readiness_for_scored_intents():
    for intent in ("patentability", "prior_art", "compliance", "evidence_strength",
                   "regulatory_roadmap"):
        text = co._executive_summary(intent, None, None, "Verified citation: Act")
        assert "Verified citation: Act" in text
        assert "rule-engine scored assessment" in text


def test_executive_summary_patentability_with_readiness():
    text = co._executive_summary("patentability", _readiness_result(overall=62.0), None, "")
    assert "62/100" in text
    assert "not yet patent-ready" in text
    assert "overlap is 35%" in text
    assert "Run a detailed TKDL search" in text


def test_executive_summary_patentability_ready_flag():
    text = co._executive_summary(
        "patentability", _readiness_result(patent_ready=True, overall=80.0), None, "")
    assert "patent-ready" in text


def test_executive_summary_prior_art_with_and_without_families():
    with_families = co._executive_summary("prior_art", _readiness_result(), None, "")
    assert "overlaps by 61%" in with_families
    empty = co._executive_summary("prior_art", _readiness_result(similar=False), None, "")
    assert "No close botanical prior-art families" in empty


def test_executive_summary_marketing_claim_risk_levels():
    high = co._executive_summary("marketing_claim", None, _claim(), "")
    assert "unapproved drug" in high
    safe = co._executive_summary(
        "marketing_claim", None, _claim(overall="SAFE", counts={"red": 0, "yellow": 0, "green": 1}), "")
    assert "structure/function safe" in safe


def test_executive_summary_dataset_intents():
    origin = co._executive_summary("botanical_origin", None, None, "")
    assert "ingredient origins are verified" in origin
    space = co._executive_summary("white_space", None, None, "")
    assert "white-space grid" in space
    road = co._executive_summary("regulatory_roadmap", _readiness_result(), None, "")
    assert "Six regulatory gates" in road


def test_executive_summary_compliance_and_evidence_intents():
    r = _readiness_result()
    comp = co._executive_summary("compliance", r, None, "")
    assert "60/100" in comp
    assert "Flagged" in comp
    ev = co._executive_summary("evidence_strength", r, None, "")
    assert "3 of its 10 weight points" in ev
    assert "stability data" in ev


def test_executive_summary_falls_back_to_citation():
    assert co._executive_summary("general", None, None, "Verified citation: Act") == \
        "Verified citation: Act"
    assert co._executive_summary("general", None, None, "") == \
        "Grounded in the retrieved official sources."


def test_next_actions_general_and_unknown_intents():
    general = co._next_actions("general", None, None)
    assert len(general) == 3
    assert co._next_actions("brand_new_intent", None, None) == []


@pytest.mark.parametrize("intent", [
    "patentability", "prior_art", "marketing_claim", "botanical_origin",
    "regulatory_roadmap", "compliance", "evidence_strength", "white_space",
])
def test_next_actions_cover_every_mapped_intent(intent):
    actions = co._next_actions(intent, None, None)
    assert 1 <= len(actions) <= 4


def test_next_actions_use_readiness_and_claim_enrichment():
    r = _readiness_result()
    r["next_actions"] = ["Custom action one", "Custom action two"]
    actions = co._next_actions("patentability", r, None)
    assert actions[0] == "Custom action one"

    claim_actions = co._next_actions("marketing_claim", None, _claim())
    assert claim_actions[0] == "Suggested compliant wording:"
    assert "Supports healthy function" in claim_actions


def test_compute_confidence_edges():
    assert co._compute_confidence(set(), [], 0.0, "general") == 0.08
    assert co._compute_confidence({"a"}, [], 0.0, "general") == 0.08

    general = co._compute_confidence({"a", "b"}, [_source("x")], 1.0, "general")
    patent = co._compute_confidence({"a", "b"}, [_source("x")], 1.0, "patentability")
    other = co._compute_confidence({"a", "b"}, [_source("x")], 1.0, "compliance")
    assert general > patent > other
    assert 0.06 <= general <= 0.97


def test_compute_confidence_tolerates_broken_authority_rank():
    conf = co._compute_confidence({"a"}, [_source("x", authority_rank="zzz")], 0.5, "general")
    assert 0.06 <= conf <= 0.97


def test_compute_confidence_scales_with_coverage_and_agreement():
    sparse = co._compute_confidence({"a", "b"}, [_source("x")], 0.0, "general")
    dense = co._compute_confidence({"a", "b"}, [_source("x") for _ in range(5)], 1.0, "general")
    assert dense > sparse


# ---------------------------------------------------------------------------
# class-level helpers
# ---------------------------------------------------------------------------

def test_dedupe_drops_repeated_citation_identity():
    sources = [
        _source("x" * 100 + " tail a"),
        _source("x" * 100 + " tail b"),
        _source("different", source="Other"),
    ]
    deduped = Orchestrator._dedupe(sources)
    assert len(deduped) == 2


def test_dedupe_respects_limit():
    sources = [_source(f"content {i}", source=f"S{i}") for i in range(20)]
    assert len(Orchestrator._dedupe(sources, limit=4)) == 4


def test_get_fallback_sources_merges_index_and_statutory(monkeypatch):
    index = SimpleNamespace(search=lambda q, top_k=8: [
        {"content": "index passage about ashwagandha", "source": "kb", "doc_id": "d1"}
    ])
    monkeypatch.setattr(AICopilot, "_faiss_index", index)
    monkeypatch.setattr(HybridRetrievalEngine, "search_passages", lambda *a, **k: [
        SimpleNamespace(
            exact_passage="statutory passage text", source_url="https://example.gov/1",
            act_title="Act", section_reference="S.1", authority="Gov",
            effective_date="2020-01-01", authority_rank=1,
        )
    ])
    sources = Orchestrator._get_fallback_sources("ashwagandha")
    assert any(s.get("category") == "knowledge" for s in sources)
    assert any(s.get("category") == "statutory" for s in sources)


def test_get_fallback_sources_swallows_backend_errors(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("index down")

    monkeypatch.setattr(AICopilot, "_faiss_index", None)
    monkeypatch.setattr(AICopilot, "get_index", _boom)
    monkeypatch.setattr(HybridRetrievalEngine, "search_passages", _boom)
    assert Orchestrator._get_fallback_sources("ashwagandha") == []


# ---------------------------------------------------------------------------
# run() — grounding, refusal, routing
# ---------------------------------------------------------------------------

def test_run_with_pre_retrieved_sources_is_grounded():
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert result["confidence"] > 0.3
    assert result["answer"]
    assert NO_EVIDENCE_ANSWER not in result["answer"]
    assert len(result["sources"]) == 1
    assert result["analysis_card"]["verification_badge"] != "Insufficient Evidence"
    assert result["response_sections"]["direct_answer"] == result["answer"]


def test_run_refuses_when_no_evidence_anywhere(monkeypatch):
    monkeypatch.setattr(HybridRetriever, "retrieve", lambda *a, **k: {})
    monkeypatch.setattr(Orchestrator, "_get_fallback_sources",
                        classmethod(lambda cls, q: []))
    result = Orchestrator.run("tell me about obscure marine lichens")
    assert NO_EVIDENCE_ANSWER in result["answer"]
    assert result["confidence"] <= 0.1
    assert result["sources"] == []
    assert result["analysis_card"]["verification_badge"] == "Insufficient Evidence"
    assert len(result["next_actions"]) == 3
    assert not result["verification"]


def test_run_uses_hybrid_retriever_when_no_pre_retrieved_sources(monkeypatch):
    captured = {}

    def _retrieve(query, **kw):
        captured["query"] = query
        captured["kw"] = kw
        return {
            "sources": [_grounded(QUESTION)],
            "confidence": 0.72,
            "should_refuse": False,
            "refusal_reason": "",
            "retrieval_stats": {"semantic_results": 4, "final_count": 1},
            "grounding": {"coverage_ratio": 0.9},
        }

    monkeypatch.setattr(HybridRetriever, "retrieve", _retrieve)
    result = Orchestrator.run(QUESTION)
    assert captured["kw"]["top_k"] == 10
    assert captured["kw"]["jurisdiction"] == "India"
    assert captured["kw"]["domains"] == ["patents", "traditional_knowledge"]
    assert result["confidence"] == 0.72
    assert result["analysis_card"]["retrieval_stats"]["semantic_results"] == 4


def test_run_falls_back_to_legacy_sources_when_retriever_breaks(monkeypatch):
    monkeypatch.setattr(HybridRetriever, "retrieve",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(Orchestrator, "_get_fallback_sources",
                        classmethod(lambda cls, q: [_grounded(QUESTION)]))
    result = Orchestrator.run(QUESTION)
    assert result["confidence"] > 0.3
    assert NO_EVIDENCE_ANSWER not in result["answer"]


def test_run_honours_retriever_refusal_only_without_grounding(monkeypatch):
    def _refusing(*a, **k):
        return {
            "sources": [_source("unrelated marine biology notes", category="blog",
                                retrieval_method="semantic", authority_rank=3)],
            "confidence": 0.0,
            "should_refuse": True,
            "refusal_reason": "below confidence bar",
            "retrieval_stats": {},
            "grounding": {},
        }

    monkeypatch.setattr(HybridRetriever, "retrieve", _refusing)
    monkeypatch.setattr(Orchestrator, "_get_fallback_sources",
                        classmethod(lambda cls, q: []))
    result = Orchestrator.run("ashwagandha patent requirements")
    assert NO_EVIDENCE_ANSWER in result["answer"]
    assert result["confidence"] <= 0.1


def test_run_retriever_refusal_does_not_override_real_grounding(monkeypatch):
    def _refusing(*a, **k):
        return {
            "sources": [_grounded(QUESTION)],
            "confidence": 0.0,
            "should_refuse": True,
            "refusal_reason": "stale provider signal",
            "retrieval_stats": {},
            "grounding": {},
        }

    monkeypatch.setattr(HybridRetriever, "retrieve", _refusing)
    result = Orchestrator.run(QUESTION)
    assert NO_EVIDENCE_ANSWER not in result["answer"]
    assert result["confidence"] > 0.3


def test_run_loose_rescue_when_coverage_is_weak(monkeypatch):
    sources = [_source("unrelated marine biology notes about coral", title="Marine")]
    result = _run("what is the meaning of life", sources)
    assert result["confidence"] > 0.1
    assert NO_EVIDENCE_ANSWER not in result["answer"]
    assert "closest official sources" in result["analysis_card"]["executive_summary"]


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


def test_run_jurisdiction_toggle_flows_into_trace():
    result = _run("ashwagandha patent rules", [_grounded("ashwagandha patent rules")],
                  context={"jurisdiction": "international"})
    assert result["jurisdiction"]["detected"] == "International"
    assert result["jurisdiction"]["applied_filters"] == []
    trace = result["decision_trace"]["jurisdiction"]
    assert trace["detected"] == "International"


def test_run_detects_hinglish_query_label():
    question = "kya mujhe kaise kar sakti hoon aur ye dawa bhi"
    result = _run(question, [_source(
        "kya mujhe kaise kar sakti hoon aur ye dawa bhi ki jankari hai")])
    assert result["decision_trace"]["language"]["label"] == "Hinglish (Romanised)"
    assert result["detected_language"] == "en"


def test_run_detects_indic_language():
    question = "भारत में पेटेंट कैसे करें"
    result = _run(question, [_source("भारत में पेटेंट कैसे करें इसकी जानकारी")])
    assert result["detected_language"] == "hi"
    assert result["decision_trace"]["language"]["label"] == "Hindi"


def test_run_bhashini_translates_query_and_answer(monkeypatch):
    from app.services.bhashini_client import BhashiniClient

    calls = {"query": 0, "answer": 0}

    monkeypatch.setattr(BhashiniClient, "is_enabled", staticmethod(lambda: True))

    def _to_english(text, lang):
        calls["query"] += 1
        return "translated english patent query"

    def _to_lang(text, lang):
        calls["answer"] += 1
        return "हिंदी उत्तर"

    monkeypatch.setattr(BhashiniClient, "translate_query_to_english", staticmethod(_to_english))
    monkeypatch.setattr(BhashiniClient, "translate_answer_to_lang", staticmethod(_to_lang))

    result = _run("भारत में पेटेंट कैसे करें",
                  [_source("translated english patent query section 3(p) guidance")])
    assert calls["query"] == 1
    assert calls["answer"] >= 1
    assert result["answer"].startswith("हिंदी उत्तर")
    bhashini = result["decision_trace"]["rules_applied"]
    entry = next(r for r in bhashini if r["rule"] == "Bhashini Translation")
    assert entry["status"] == "PASS"


def test_run_live_web_sources_merged_when_enabled(monkeypatch):
    monkeypatch.setenv("IPSAKTI_ENABLE_LIVE_WEB", "1")
    monkeypatch.setattr("app.rag.official_web_retriever.fetch_official_sources",
                        lambda q, top_k=3: [
                            _source("live official passage about patent rules",
                                    source="IP India", retrieval_method="live_web",
                                    category="official")
                        ])
    result = _run("ashwagandha patent rules", [_grounded("ashwagandha patent rules")])
    assert any(s.get("retrieval_method") == "live_web" for s in result["sources"])


def test_run_live_web_errors_are_ignored(monkeypatch):
    monkeypatch.setenv("IPSAKTI_ENABLE_LIVE_WEB", "1")
    monkeypatch.setattr(
        "app.rag.official_web_retriever.fetch_official_sources",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    result = _run("ashwagandha patent rules", [_grounded("ashwagandha patent rules")])
    assert result["sources"]


# ---------------------------------------------------------------------------
# run() — rule engine enrichment per intent
# ---------------------------------------------------------------------------

def test_run_patentability_intent_builds_rule_charts(monkeypatch):
    monkeypatch.setattr(co, "_get_passport", lambda pid, q: object())
    monkeypatch.setattr(co, "_readiness", lambda p: _readiness_result())
    result = _run("Can I patent this ashwagandha formulation?",
                  [_grounded("Can I patent this ashwagandha formulation?")],
                  passport_id="passport-1")
    types = [c["type"] for c in result["charts"]]
    assert "radar" in types
    assert "bar_h" in types
    assert "doughnut" in types
    assert result["analysis_card"]["verification_badge"] == "Verified — Measured by Rule Engines"
    assert result["analysis_card"]["patent_readiness"] == 55
    assert result["analysis_card"]["risk_level"] == "Moderate"
    assert "not yet patent-ready" in result["analysis_card"]["executive_summary"]


def _passport_stub(pid, question):
    return object() if pid else None


def test_run_patentability_without_real_passport_stays_unscored(monkeypatch):
    monkeypatch.setattr(co, "_get_passport", _passport_stub)
    monkeypatch.setattr(co, "_readiness", lambda p: _readiness_result())
    result = _run("Can I patent this ashwagandha formulation?",
                  [_grounded("Can I patent this ashwagandha formulation?")])
    assert result["charts"] == []
    assert result["analysis_card"]["patent_readiness"] is None


def test_run_prior_art_intent_builds_similarity_chart(monkeypatch):
    monkeypatch.setattr(co, "_get_passport", _passport_stub)
    monkeypatch.setattr(co, "_readiness", lambda p: _readiness_result())
    result = _run("prior art search for tulsi extract",
                  [_grounded("prior art search for tulsi extract")],
                  passport_id="passport-1")
    types = [c["type"] for c in result["charts"]]
    assert "bar_h" in types
    assert "doughnut" in types


def test_run_compliance_intent_builds_gauge(monkeypatch):
    monkeypatch.setattr(co, "_get_passport", _passport_stub)
    monkeypatch.setattr(co, "_readiness", lambda p: _readiness_result(overall=80.0))
    question = "fssai compliance requirements for patent documents"
    result = _run(question, [_grounded(question)], passport_id="passport-1")
    types = [c["type"] for c in result["charts"]]
    assert "gauge" in types
    assert "radar" in types
    assert result["analysis_card"]["risk_level"] == "Low"


def test_run_evidence_strength_intent_builds_donut(monkeypatch):
    monkeypatch.setattr(co, "_get_passport", _passport_stub)
    monkeypatch.setattr(co, "_readiness", lambda p: _readiness_result())
    question = "what scientific evidence and stability data are required for patent"
    result = _run(question, [_grounded(question)], passport_id="passport-1")
    assert [c["type"] for c in result["charts"]] == ["doughnut"]
    assert "stability data" in result["analysis_card"]["executive_summary"]


def test_run_regulatory_roadmap_intent_builds_timeline(monkeypatch):
    monkeypatch.setattr(co, "_get_passport", lambda pid, q: None)
    question = "what is the roadmap for my patent filing journey"
    result = _run(question, [_grounded(question)])
    assert [c["type"] for c in result["charts"]] == ["timeline"]


def test_run_marketing_claim_intent_runs_claim_firewall(monkeypatch):
    monkeypatch.setattr(
        co.PassportEngine, "get_passport",
        lambda pid: SimpleNamespace(proposed_claims=["Treats diabetes naturally",
                                                     "Supports immunity"]))
    result = _run("is this label claim safe for marketing",
                  [_grounded("is this label claim safe for marketing")],
                  passport_id="passport-1")
    assert [c["type"] for c in result["charts"]] == ["risk_matrix"]
    assert result["analysis_card"]["risk_level"] == "High"
    assert result["next_actions"][0] == "Suggested compliant wording:"


def test_run_botanical_origin_intent_adds_heatmap(monkeypatch):
    result = _run("ashwagandha sourcing origin geography in india",
                  [_grounded("ashwagandha sourcing origin geography in india")])
    assert [c["type"] for c in result["charts"]] == ["india_heatmap"]
    assert "verified" in result["analysis_card"]["executive_summary"]


def test_run_white_space_intent_adds_opportunity_grid(monkeypatch):
    result = _run("where are white space opportunities in this market",
                  [_grounded("where are white space opportunities in this market")])
    assert [c["type"] for c in result["charts"]] == ["opportunity_heatmap"]


def test_run_answer_has_no_patent_advice_for_regulatory_domain():
    result = _run("fssai compliance requirements for food business operator",
                  [_grounded("fssai compliance requirements for food business operator")])
    joined = " ".join(result["next_actions"])
    assert "Section 3(p)" not in joined
    assert "patent agent" not in joined
    prompt_user = str(result["llm_prompt"].get("user", ""))
    assert "TOPIC RESTRICTION" in prompt_user


# ---------------------------------------------------------------------------
# run() — verification, hallucination guard, LLM draft
# ---------------------------------------------------------------------------

def test_run_verification_gate_failure_blocks_answer(monkeypatch):
    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification",
                        lambda *a, **k: _verification(passed=False))
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert result["verification"]["passed_gate"] is False
    assert result["confidence"] == 0.05
    assert result["analysis_card"]["verification_badge"] == "Insufficient Evidence"
    assert result["decision_trace"]["rules_applied"][-2]["status"] == "BLOCK"


def test_run_verification_regenerated_answer_lowers_confidence(monkeypatch):
    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification",
                        lambda *a, **k: _verification(passed=False, regenerated=True))
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert result["verification"]["regenerated"] is True
    assert result["confidence"] <= 0.85
    assert result["analysis_card"]["verification_badge"] == \
        "Regenerated — Unsupported Claims Removed"


def test_run_verification_keeps_rule_engine_verdict(monkeypatch):
    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification",
                        lambda *a, **k: _verification(passed=False, gate_reason="low support"))
    monkeypatch.setattr(co, "_get_passport", _passport_stub)
    monkeypatch.setattr(co, "_readiness", lambda p: _readiness_result())
    result = _run("Can I patent this ashwagandha formulation?",
                  [_grounded("Can I patent this ashwagandha formulation?")],
                  passport_id="passport-1")
    assert result["verification"]["passed_gate"] is False
    assert "rule-engine verdict retained" in result["verification"]["gate_reason"]
    assert result["confidence"] > 0.05
    assert result["analysis_card"]["verification_badge"] == "Verified — Measured by Rule Engines"


def test_run_verification_exception_keeps_answer_running(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("verification down")

    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification", _boom)
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert result["verification"] is None
    assert result["analysis_card"]["verification_badge"] == \
        "Verified — Government Sources Cited"
    assert NO_EVIDENCE_ANSWER not in result["answer"]


def test_run_verification_gate_pass_reports_band(monkeypatch):
    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification",
                        lambda *a, **k: _verification(passed=True))
    result = _run(QUESTION, [_grounded(QUESTION)])
    badge = result["analysis_card"]["verification_badge"]
    assert badge.startswith("Verified — ")
    assert "Evidence Confidence" in badge
    assert result["analysis_card"]["claim_verification"]["support_ratio"] == 1.0
    assert result["analysis_card"]["citation_validity"]["validity_ratio"] == 1.0


def test_run_grounding_badge_when_evidence_is_non_statutory(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("verification down")

    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification", _boom)
    src = _grounded(QUESTION, category="guidance", retrieval_method="semantic",
                    authority_rank=3, source="Journal of Herbs", act_title="")
    result = _run(QUESTION, [src])
    assert result["analysis_card"]["verification_badge"] == \
        "Grounded — Knowledge Base Cited"


def test_run_critical_hallucination_check_refuses_answer(monkeypatch):
    monkeypatch.setattr("app.rag.hallucination_guard.validate_answer", _guard_critical)
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert NO_EVIDENCE_ANSWER in result["answer"]
    assert result["confidence"] == 0.05
    assert result["analysis_card"]["hallucination_check"]["risk_level"] == "critical"
    assert result["analysis_card"]["verification_badge"] == "Insufficient Evidence"


def test_run_llm_draft_applied_for_general_intent(monkeypatch):
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft",
                        _draft_on("Drafted reply grounded strictly in the retrieved "
                                  "official passages quoted below with citations."))
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert result["analysis_card"]["llm_generation"]["generated"] is True
    assert result["analysis_card"]["llm_generation"]["provider"] == "unit"
    assert result["answer"].startswith("Drafted reply grounded strictly")
    assert result["analysis_card"]["verification_badge"] == \
        "Verified — Source-Grounded Answer"


def test_run_llm_draft_blocked_when_guard_flags_critical(monkeypatch):
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft",
                        _draft_on("Drafted reply grounded strictly in the retrieved "
                                  "official passages quoted below with citations."))
    monkeypatch.setattr("app.rag.hallucination_guard.validate_answer",
                        _guard_pass_then_critical())
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert result["analysis_card"]["llm_generation"]["generated"] is True
    assert not result["answer"].startswith("Drafted reply grounded strictly")
    assert result["answer"] != NO_EVIDENCE_ANSWER


def test_run_llm_draft_skipped_for_rule_scored_intent(monkeypatch):
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft",
                        _draft_on("Drafted reply grounded strictly in the retrieved "
                                  "official passages quoted below with citations."))
    monkeypatch.setattr(co, "_get_passport", _passport_stub)
    monkeypatch.setattr(co, "_readiness", lambda p: _readiness_result())
    result = _run("Can I patent this ashwagandha formulation?",
                  [_grounded("Can I patent this ashwagandha formulation?")],
                  passport_id="passport-1")
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


def test_run_llm_draft_ignored_when_too_short(monkeypatch):
    monkeypatch.setattr("app.rag.llm_adapter.generate_draft",
                        _draft_on("Too short."))
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert not result["answer"].startswith("Too short.")


def test_run_appends_knowledge_base_evidence_block(monkeypatch):
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert "Based on the retrieved official sources:" in result["answer"]


def test_run_hallucination_guard_exception_is_ignored(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("guard down")

    monkeypatch.setattr("app.rag.hallucination_guard.validate_answer", _boom)
    result = _run(QUESTION, [_grounded(QUESTION)])
    assert result["analysis_card"]["hallucination_check"] == {}
    assert NO_EVIDENCE_ANSWER not in result["answer"]


def test_run_engine_grounded_badge_for_dataset_intent(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("verification down")

    monkeypatch.setattr("app.rag.verification_orchestrator.run_verification", _boom)
    src = _source("white space opportunity grid records", category="guidance",
                  retrieval_method="semantic", authority_rank=3, source="KB",
                  act_title="")
    result = _run("where are white space opportunities in this market", [src])
    assert result["analysis_card"]["verification_badge"] == \
        "Verified — Measured by Rule Engines"


# ---------------------------------------------------------------------------
# run() — trace / response contract
# ---------------------------------------------------------------------------

def test_run_decision_trace_lists_every_stage():
    result = _run(QUESTION, [_grounded(QUESTION)])
    rules = [r["rule"] for r in result["decision_trace"]["rules_applied"]]
    for expected in ("Language Detection", "Intent Detection", "Bhashini Translation",
                     "Domain Routing", "Jurisdiction Routing",
                     "Hybrid Retrieval (BM25 + BGE-M3 + Qdrant)", "BGE Reranker",
                     "Rule Engine Scoring", "Grounding Threshold"):
        assert expected in rules
    trace = result["decision_trace"]
    assert trace["intent"]["id"] == "general"
    assert trace["intent"]["domain"] == "patent"
    assert trace["knowledge_base"]["selected_collections"] == ["patents", "traditional_knowledge"]
    assert trace["retrieval"]["candidate_count"] == 1
    assert trace["confidence"] == round(result["confidence"] * 100)


def test_run_response_contract_keys():
    result = _run(QUESTION, [_grounded(QUESTION)])
    for key in ("question", "answer", "sources", "confidence", "images", "intent",
                "detected_language", "response_sections", "analysis_card",
                "evidence_used", "verification", "jurisdiction", "decision_trace",
                "next_actions", "charts", "llm_prompt"):
        assert key in result
    sections = result["response_sections"]
    for key in ("direct_answer", "supporting_evidence", "official_citation",
                "confidence", "next_actions"):
        assert key in sections
    assert sections["confidence"] == round(result["confidence"] * 100)
    assert result["evidence_used"][0]["name"]
    assert result["evidence_used"][0]["type"]


def test_run_evidence_used_dedupes_display_names():
    sources = [
        _grounded(QUESTION, title="Doc"),
        _source("second copy of the same title record", title="Doc"),
    ]
    result = _run(QUESTION, sources)
    names = [e["name"] for e in result["evidence_used"]]
    assert len(names) == len(set(names))


def test_run_blocked_grounding_reports_refusal_actions():
    with patch.object(Orchestrator, "_get_fallback_sources",
                      classmethod(lambda cls, q: [])):
        with patch.object(HybridRetriever, "retrieve", lambda *a, **k: {}):
            result = Orchestrator.run("obscure marine lichen taxonomy")
    assert result["decision_trace"]["rules_applied"][-1]["status"] == "BLOCK"
    assert result["next_actions"][0].startswith("Add the authoritative document")
