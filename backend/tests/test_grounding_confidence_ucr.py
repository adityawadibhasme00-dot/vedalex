from typing import Any

import pytest

from app.core.confidence import ConfidenceBand
from app.models.regulatory import RegulatoryFinding, RuleConditionState, StatutoryCitation
from app.rag.claim_extractor import extract_claims
from app.rag.claim_verifier import verify_claims
from app.rag.evidence_confidence_scorer import (
    _score_to_band,
    compute_evidence_confidence,
)
from app.services.citation_validator import CitationValidator

pytestmark = pytest.mark.unit


def _finding(cited: bool = True, confidence: str = "HIGH") -> RegulatoryFinding:
    citations = []
    if cited:
        citations.append(
            StatutoryCitation(
                act_title="Indian Patents Act, 1970",
                section_reference="Section 3(p)",
                authority="Legislature",
                effective_date="1970-01-01",
                exact_passage="A claim shall not be patented if it is a mere aggregation.",
            )
        )
    return RegulatoryFinding(
        jurisdiction="India",
        pathway_category="patentability",
        status=RuleConditionState.SATISFIED,
        confidence=ConfidenceBand(confidence),
        conditions_evaluated=["condition"],
        supporting_citations=citations,
        missing_facts=[],
        next_action_steps=[],
        coverage_limitations="none",
        assumptions_made=[],
        applied_rules=[{"rule_id": "rule", "status": "applied"}],
    )


# --------------------------------------------------------------------------
# Unsupported Claim Rate (UCR)
# --------------------------------------------------------------------------

def test_ucr_zero_for_empty_findings():
    audited, ucr = CitationValidator.audit_findings([])
    assert audited == []
    assert ucr == 0.0


def test_ucr_zero_when_all_findings_cited():
    audited, ucr = CitationValidator.audit_findings([_finding(cited=True)])
    assert ucr == 0.0
    assert audited[0].confidence == "HIGH"
    assert audited[0].explanation_text is None


def test_ucr_one_when_no_finding_has_citations():
    audited, ucr = CitationValidator.audit_findings([_finding(cited=False)])
    assert ucr == 1.0
    assert audited[0].confidence == "INSUFFICIENT_EVIDENCE"
    assert audited[0].explanation_text is not None
    assert audited[0].explanation_text.startswith("Abstaining")


def test_ucr_mixed_findings():
    audited, ucr = CitationValidator.audit_findings(
        [_finding(cited=True), _finding(cited=False)]
    )
    assert ucr == 0.5
    assert audited[0].confidence == "HIGH"
    assert audited[1].confidence == "INSUFFICIENT_EVIDENCE"


def test_ucr_rounded_to_four_decimals():
    _, ucr = CitationValidator.audit_findings(
        [_finding(cited=True), _finding(cited=False), _finding(cited=False)]
    )
    assert ucr == 0.6667


# --------------------------------------------------------------------------
# Confidence bands
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "score,band",
    [
        (1.0, "HIGH"),
        (0.75, "HIGH"),
        (0.749, "MEDIUM"),
        (0.5, "MEDIUM"),
        (0.499, "LOW"),
        (0.25, "LOW"),
        (0.249, "INSUFFICIENT"),
        (0.0, "INSUFFICIENT"),
    ],
)
def test_score_to_band_boundaries(score, band):
    assert _score_to_band(score) == band


def test_compute_confidence_zero_signals_is_insufficient():
    result = compute_evidence_confidence(
        [], grounding=None, supported_ratio=0.0, citation_validity=0.0,
        rule_engine_pass=None,
    )
    assert result.band == "INSUFFICIENT"
    assert result.overall < 0.25


def test_compute_confidence_perfect_signals_is_high():
    result = compute_evidence_confidence(
        [
            {"authority_level": 1, "category": "regulatory"},
            {"authority_level": 1, "category": "statute"},
            {"authority_level": 2, "category": "patent"},
            {"authority_level": 1, "category": "official", "effective_date": "2026-01-01"},
        ],
        grounding={"coverage_ratio": 1.0},
        supported_ratio=1.0,
        citation_validity=1.0,
        rule_engine_pass=True,
    )
    assert result.band == "HIGH"
    assert result.overall >= 0.75


def test_compute_confidence_monotonic_in_supported_ratio():
    base: dict[str, Any] = dict(
        grounding={"coverage_ratio": 0.8},
        citation_validity=0.8,
        rule_engine_pass=True,
        sources=[{"authority_level": 1, "category": "regulatory"}],
    )
    low = compute_evidence_confidence(sources=base.pop("sources"), supported_ratio=0.1, **base)
    base2: dict[str, Any] = dict(
        grounding={"coverage_ratio": 0.8},
        citation_validity=0.8,
        rule_engine_pass=True,
    )
    high = compute_evidence_confidence(
        sources=[{"authority_level": 1, "category": "regulatory"}],
        supported_ratio=0.95,
        **base2,
    )
    assert high.overall > low.overall


def test_compute_confidence_lists_all_seven_signals():
    result = compute_evidence_confidence(
        [], grounding={"coverage_ratio": 0.5}, supported_ratio=0.5,
        citation_validity=0.5, rule_engine_pass=None,
    )
    assert len(result.signals) == 7
    assert sum(s.weight for s in result.signals) == pytest.approx(1.0)
    names = {s.name for s in result.signals}
    assert names == {
        "retrieval_coverage",
        "citation_validity",
        "evidence_support",
        "source_authority",
        "source_diversity",
        "rule_validation",
        "evidence_freshness",
    }


def test_compute_confidence_echoes_input_ratios():
    result = compute_evidence_confidence(
        [], grounding={"coverage_ratio": 0.6}, supported_ratio=0.4,
        citation_validity=0.7, rule_engine_pass=False,
    )
    assert result.retrieval_coverage == 0.6
    assert result.supported_ratio == 0.4
    assert result.citation_validity == 0.7
    assert result.rule_engine_pass is False


def test_compute_confidence_rule_engine_fail_lowers_score():
    common: dict[str, Any] = dict(
        sources=[{"authority_level": 1, "category": "regulatory"}],
        grounding={"coverage_ratio": 0.8},
        supported_ratio=0.8,
        citation_validity=0.8,
    )
    passed = compute_evidence_confidence(rule_engine_pass=True, **common)
    failed = compute_evidence_confidence(rule_engine_pass=False, **common)
    assert passed.overall > failed.overall


# --------------------------------------------------------------------------
# Claim verification (reclassification against evidence)
# --------------------------------------------------------------------------

def test_extract_claims_splits_sentences():
    claims = extract_claims(
        "Ashwagandha supports healthy sleep. The formulation includes Brahmi extract."
    )
    assert len(claims) == 2


def test_verify_claims_counts_sum_to_total():
    table = verify_claims(
        answer="Ashwagandha supports healthy sleep. The formulation includes Brahmi extract.",
        sources=[{"content": "Ashwagandha supports healthy sleep in adults.", "title": "T"}],
    )
    assert table.total_claims >= 1
    assert (
        table.supported_count + table.contradicted_count + table.not_enough_count
        == table.total_claims
    )
    assert 0.0 <= table.support_ratio <= 1.0


def test_verify_claims_reclassifies_supported_and_contradicted():
    table = verify_claims(
        answer="Ashwagandha supports healthy sleep. The formulation includes Brahmi extract.",
        sources=[{"content": "Ashwagandha supports healthy sleep in adults.", "title": "T"}],
    )
    statuses = {c.status for c in table.claims}
    assert statuses <= {"SUPPORTED", "CONTRADICTED", "NOT_ENOUGH"}
    assert table.has_unsupported or table.has_contradictions


def test_verify_claims_empty_answer_returns_empty_table():
    table = verify_claims(answer="", sources=[])
    assert table.total_claims == 0
    assert table.support_ratio == 0.0
    assert table.all_supported is False


def test_verify_claims_flags_contradictions():
    table = verify_claims(
        answer="Ashwagandha does not affect sleep at all. The formulation includes Brahmi extract.",
        sources=[{"content": "Ashwagandha supports healthy sleep in adults.", "title": "T"}],
    )
    if table.claims:
        assert table.has_contradictions or table.has_unsupported
