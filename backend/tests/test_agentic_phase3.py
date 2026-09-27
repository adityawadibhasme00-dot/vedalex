"""Phase 3 (Master Prompt v7.0.0) — classifier, TKDL, ABS, citation, guardrails."""

from __future__ import annotations

import pytest

from app.agents.abs_agent import ABSComplianceAgent
from app.agents.base import AgentContext
from app.agents.citation_checker import CitationChecker
from app.agents.classifier import (
    AYURVEDA_AAHR,
    CLASSICAL_MEDICINE,
    COSMETIC,
    NEW_DRUG,
    PHYTOPHARMACEUTICAL,
    PROPRIETARY_MEDICINE,
    FormulationClassifier,
)
from app.agents.guardrails import REJECT_MESSAGE, GuardrailJudge
from app.agents.tkdl_agent import TKDLPriorArtAgent

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    monkeypatch.setenv("IPSAKTI_LLM_PROVIDER", "off")


# ---------------------------------------------------------------------------
# Component 2 — Formulation Classifier
# ---------------------------------------------------------------------------


def test_classifier_detects_cosmetic():
    out = FormulationClassifier().classify("A cosmetic face cream for external use")
    assert out["category"] == COSMETIC
    assert "Based on your description" in out["basis"]
    assert out["needs_clarification"] is False


def test_classifier_detects_aahar_nutraceutical():
    out = FormulationClassifier().classify(
        "FSSAI dietary supplement health drink under Ayurveda AAHAR"
    )
    assert out["category"] == AYURVEDA_AAHR


def test_classifier_detects_phytopharmaceutical():
    out = FormulationClassifier().classify(
        "Purified extract with defined marker compound"
    )
    assert out["category"] == PHYTOPHARMACEUTICAL


def test_classifier_detects_new_drug():
    out = FormulationClassifier().classify(
        "New indication for a non-classical molecule"
    )
    assert out["category"] == NEW_DRUG


def test_classifier_detects_proprietary_via_modification():
    out = FormulationClassifier().classify(
        "Our own modified composition with a changed ratio"
    )
    assert out["category"] == PROPRIETARY_MEDICINE


def test_classifier_detects_classical_from_text():
    out = FormulationClassifier().classify(
        "Formulation taken verbatim from Charaka Samhita"
    )
    assert out["category"] == CLASSICAL_MEDICINE
    assert "Section 3(p)" in out["ip_posture_summary"]


def test_classifier_asks_up_to_five_questions_when_unknown():
    out = FormulationClassifier().classify("We want to file something for our brand")
    assert out["category"] is None
    assert out["needs_clarification"] is True
    assert 0 < len(out["clarifying_questions"]) <= 5
    assert out["next_question"] == out["clarifying_questions"][0]


def test_classifier_sets_context_product_category():
    ctx = AgentContext()
    out = FormulationClassifier().classify("Cosmetic face cream", context=ctx)
    assert out["category"] == COSMETIC
    assert ctx.product_category == COSMETIC


def test_classifier_ip_and_abs_posture_present_for_every_category():
    clf = FormulationClassifier()
    queries = {
        CLASSICAL_MEDICINE: "verbatim from Charaka Samhita",
        PROPRIETARY_MEDICINE: "our modified composition",
        NEW_DRUG: "new indication claimed",
        PHYTOPHARMACEUTICAL: "purified extract with marker compound",
        AYURVEDA_AAHR: "FSSAI dietary supplement",
        COSMETIC: "cosmetic external use cream",
    }
    for category, q in queries.items():
        out = clf.classify(q)
        assert out["category"] == category, q
        assert out["ip_posture_summary"]
        assert out["abs_posture_summary"]


# ---------------------------------------------------------------------------
# Component 5 — TKDL Prior-Art Agent
# ---------------------------------------------------------------------------


def test_tkdl_documented_classical_ingredients_red():
    out = TKDLPriorArtAgent().assess(
        ingredients=["ashwagandha", "brahmi"],
        description="patent for a classical churna",
    )
    assert out["risk_level"] == "RED"
    assert len(out["ingredient_findings"]) == 2
    assert all(f["documented_in_tk"] for f in out["ingredient_findings"])
    assert out["matched_classical_texts"], "Charaka record should match"
    assert len(out["recommendations"]) >= 3
    assert "preliminary" in out["disclaimer"].lower()


def test_tkdl_novelty_signals_downgrade_to_amber():
    out = TKDLPriorArtAgent().assess(
        ingredients=["ashwagandha"],
        description="novel sustained-release tablet dosage form",
    )
    assert out["risk_level"] == "AMBER"
    assert out["recommendations"]


def test_tkdl_unknown_ingredient_is_green():
    out = TKDLPriorArtAgent().assess(ingredients=["xyzzyherbium"])
    assert out["risk_level"] == "GREEN"
    assert out["ingredient_findings"][0]["documented_in_tk"] is False


def test_tkdl_explicit_classical_reference_is_red():
    out = TKDLPriorArtAgent().assess(
        ingredients=["ashwagandha"],
        classical_text="Charaka Samhita, Chikitsa Sthana",
    )
    assert out["risk_level"] == "RED"


def test_tkdl_contested_case_precedent_for_turmeric():
    out = TKDLPriorArtAgent().assess(ingredients=["turmeric"])
    findings = out["ingredient_findings"][0]
    assert findings["documented_in_tk"] is True
    assert findings["contested_cases"], "US 5,401,504 precedent expected"
    assert out["risk_level"] == "RED"


def test_tkdl_uses_agent_context_ingredients():
    ctx = AgentContext(ingredients=["ashwagandha", "brahmi"])
    out = TKDLPriorArtAgent().assess(context=ctx, description="classical churna")
    assert len(out["ingredient_findings"]) == 2


# ---------------------------------------------------------------------------
# Component 6 — ABS Compliance Agent
# ---------------------------------------------------------------------------


def test_abs_agent_builds_numbered_steps_with_citations():
    out = ABSComplianceAgent().compliance_path(
        ingredients=["ashwagandha"], user_type="company"
    )
    assert out["status"] in ("compliance_required", "info_required", "exempt")
    assert out["steps"], "at least the applicability step is required"
    assert [s["step"] for s in out["steps"]] == list(
        range(1, len(out["steps"]) + 1)
    )
    for step in out["steps"]:
        assert step["title"]
        assert step["authority"]
        assert "citation" in step
        assert "timeline" in step
    assert out["disclaimer"]
    assert "facilitator" in out["escalation"].lower()


def test_abs_agent_exempt_path_has_two_steps():
    out = ABSComplianceAgent().compliance_path(
        ingredients=["ashwagandha"],
        user_type="registered_ayush_practitioner",
    )
    if out["status"] == "exempt":
        assert len(out["steps"]) == 2
        assert out["exemption_reason"]
    else:
        # Engine did not grant the exemption — path still must be complete.
        assert len(out["steps"]) >= 3


def test_abs_agent_uses_agent_context_ingredients():
    ctx = AgentContext(ingredients=["ashwagandha"])
    out = ABSComplianceAgent().compliance_path(context=ctx, user_type="company")
    assert out["steps"]


def test_abs_agent_result_has_benefit_sharing_and_citations_keys():
    out = ABSComplianceAgent().compliance_path(ingredients=["ashwagandha"])
    assert "benefit_sharing" in out
    assert "required_approvals" in out
    assert "citations" in out


# ---------------------------------------------------------------------------
# Component 7 — Citation & Confidence Module
# ---------------------------------------------------------------------------

_GOOD_SOURCES = [
    {
        "title": "The Patents Act 1970",
        "content": (
            "Section 3(p) of the Patents Act 1970 bars claims on properties "
            "or uses of known substances without enhanced efficacy."
        ),
        "jurisdiction": "India",
    }
]


def test_citation_checker_high_confidence_when_all_verified():
    answer = (
        "Evergreening is barred. [Source: Patents Act 1970, Section 3(p)] "
        "Patents Act 1970 Section 3(p) applies."
    )
    out = CitationChecker().verify(answer, _GOOD_SOURCES)
    assert out["total_citations"] >= 1
    assert out["valid_citations"] == out["total_citations"]
    assert out["verified"] is True
    assert out["confidence"] == "HIGH"
    assert out["unverified"] == []


def test_citation_checker_low_confidence_when_nothing_verifies():
    answer = "FSSAI Nutraceutical Rules 2022 govern this claim."
    out = CitationChecker().verify(answer, _GOOD_SOURCES)
    assert out["confidence"] == "LOW"
    assert out["verified"] is False
    assert out["unverified"]


def test_citation_checker_medium_when_answer_has_no_citations():
    out = CitationChecker().verify(
        "General information without any statutory citations.", _GOOD_SOURCES
    )
    assert out["total_citations"] == 0
    assert out["confidence"] == "MEDIUM"
    assert out["verified"] is False


def test_citation_checker_handles_empty_sources():
    out = CitationChecker().verify("Patents Act 1970 Section 3(p)", [])
    assert out["total_citations"] == 0
    assert out["confidence"] == "MEDIUM"


# ---------------------------------------------------------------------------
# Component 8 — Guardrails / Abstention Judge
# ---------------------------------------------------------------------------

_CLEAN_ANSWER = (
    "Direct answer: evergreening of known substances is barred. "
    "Patents Act 1970 Section 3(p) applies. "
    "[Source: Patents Act 1970, Section 3(p)] "
    "\n\nThis is general information, not legal advice."
)


def test_guardrails_approve_well_grounded_answer():
    out = GuardrailJudge().review(
        query="What does Section 3(p) of the Patents Act bar?",
        answer=_CLEAN_ANSWER,
        sources=_GOOD_SOURCES,
        jurisdiction="india",
        confidence="HIGH",
    )
    assert out["verdict"] == "APPROVE"
    assert out["suggested_action"] == "answer"
    assert out["failed_checks"] == []
    assert out["reject_message"] is None


def test_guardrails_reject_ungrounded_citation():
    out = GuardrailJudge().review(
        query="What does the law say?",
        answer="FSSAI Nutraceutical Rules 2022 allow this. [Source: FSSAI Nutraceutical Rules 2022]",
        sources=_GOOD_SOURCES,
        jurisdiction="india",
        confidence="MEDIUM",
    )
    assert out["verdict"] == "REJECT"
    assert out["suggested_action"] == "abstain"
    assert "source_grounded" in out["failed_checks"]
    assert out["reject_message"] == REJECT_MESSAGE


def test_guardrails_reject_personal_legal_advice_scope():
    out = GuardrailJudge().review(
        query="Should I sue them for copying my product?",
        answer="General context only.",
        sources=_GOOD_SOURCES,
        jurisdiction="india",
        confidence="HIGH",
    )
    assert out["verdict"] == "REJECT"
    assert out["suggested_action"] == "escalate"
    assert "scope" in out["failed_checks"]


def test_guardrails_reject_medical_dosage_advice():
    out = GuardrailJudge().review(
        query="How many mg of Ashwagandha should I take?",
        answer="Take 500 mg twice daily with milk.",
        sources=_GOOD_SOURCES,
        jurisdiction="india",
        confidence="HIGH",
    )
    assert out["verdict"] == "REJECT"
    assert "medical" in out["failed_checks"] or "scope" in out["failed_checks"]
    assert out["suggested_action"] in ("escalate", "abstain")


def test_guardrails_reject_when_no_sources_uncertainty():
    out = GuardrailJudge().review(
        query="What is a patent?",
        answer="A patent is a right.",
        sources=[],
        jurisdiction="india",
        confidence="LOW",
    )
    assert out["verdict"] == "REJECT"
    assert "uncertainty" in out["failed_checks"]
    assert out["suggested_action"] == "abstain"


def test_guardrails_reject_low_confidence_even_with_sources():
    out = GuardrailJudge().review(
        query="What does the law say?",
        answer="Some text with no citations.",
        sources=_GOOD_SOURCES,
        jurisdiction="india",
        confidence="LOW",
    )
    assert out["verdict"] == "REJECT"
    assert "uncertainty" in out["failed_checks"]


def test_guardrails_reject_jurisdiction_mixing():
    intl_source = {
        "title": "WIPO PCT Treaty Article 27",
        "content": "PCT Article 27 says national treatment applies.",
        "jurisdiction": "International",
    }
    out = GuardrailJudge().review(
        query="What are the patentability requirements?",
        answer="PCT Treaty Article 27 applies here. WIPO PCT Treaty Article 27.",
        sources=[intl_source],
        jurisdiction="india",
        confidence="HIGH",
    )
    assert out["verdict"] == "REJECT"
    assert "jurisdiction_mixing" in out["failed_checks"]


def test_guardrails_reject_is_sticky_against_llm_approve(monkeypatch):
    judge = GuardrailJudge()
    monkeypatch.setattr(
        judge,
        "llm_json",
        lambda prompt, fallback: {"verdict": "APPROVE", "reason": "fine"},
    )
    out = judge.review(
        query="Should I sue them for copying my product?",
        answer=_CLEAN_ANSWER,
        sources=_GOOD_SOURCES,
        jurisdiction="india",
        confidence="HIGH",
    )
    assert out["verdict"] == "REJECT"  # deterministic scope failure wins


def test_guardrails_llm_can_add_rejection_when_rules_approve(monkeypatch):
    judge = GuardrailJudge()
    monkeypatch.setattr(
        judge,
        "llm_json",
        lambda prompt, fallback: {
            "verdict": "REJECT",
            "reason": "judge says no",
            "suggested_action": "escalate",
        },
    )
    out = judge.review(
        query="What does Section 3(p) of the Patents Act bar?",
        answer=_CLEAN_ANSWER,
        sources=_GOOD_SOURCES,
        jurisdiction="india",
        confidence="HIGH",
    )
    assert out["verdict"] == "REJECT"
    assert out["failed_checks"] == ["llm_judge"]


def test_guardrails_reject_message_matches_master_prompt_template():
    out = GuardrailJudge().review(
        query="Should I sue them?",
        answer="x",
        sources=_GOOD_SOURCES,
        jurisdiction="india",
        confidence="HIGH",
    )
    assert out["reject_message"].startswith(
        "I cannot answer this confidently from authoritative sources."
    )
    assert "human IP facilitator" in out["reject_message"]
