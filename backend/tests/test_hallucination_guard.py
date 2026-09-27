import pytest

from app.rag.hallucination_guard import (
    HallucinationRisk,
    build_grounding_check,
    should_refuse_answer,
    validate_answer,
)

pytestmark = pytest.mark.unit


def _sources(*contents, **extra):
    out = []
    for i, content in enumerate(contents):
        s = {"content": content, "title": f"Source {i}"}
        s.update(extra)
        out.append(s)
    return out


# --------------------------------------------------------------------------
# Citation gate (no answer without citation)
# --------------------------------------------------------------------------

def test_validate_answer_requires_citations_at_high_confidence():
    check = validate_answer(
        answer="Ashwagandha supports sleep.",
        sources=_sources("ashwagandha sleep study evidence"),
        query="ashwagandha sleep",
        confidence=0.9,
    )
    assert "No explicit citations found in answer" in check.violations
    assert check.citation_count == 0


def test_validate_answer_skips_citation_gate_at_low_confidence():
    check = validate_answer(
        answer="Ashwagandha supports sleep.",
        sources=_sources("ashwagandha sleep study evidence"),
        query="ashwagandha sleep",
        confidence=0.2,
    )
    assert "No explicit citations found in answer" not in check.violations


def test_grounded_cited_answer_passes_validation():
    check = validate_answer(
        answer="Ashwagandha supports healthy sleep. The trial evidence supports use in adults. [Source 1]",
        sources=_sources(
            "ashwagandha sleep study shows benefit in adults",
            "independent ashwagandha sleep study confirms effect",
        ),
        query="ashwagandha sleep study",
        confidence=0.95,
    )
    assert check.grounded is True
    assert check.risk_level in (HallucinationRisk.NONE, HallucinationRisk.LOW)
    assert check.violations == []
    assert check.coverage_ratio == 1.0


def test_cited_study_claim_still_flagged_as_unsupported():
    # _detect_unsupported_claims is citation-blind: an inline [Source N] does
    # not exempt a "study shows" sentence.
    check = validate_answer(
        answer="Study shows it works. [Source 1]",
        sources=_sources("ashwagandha sleep study shows benefit in adults"),
        query="ashwagandha sleep study",
        confidence=0.9,
    )
    assert any("Study claim without specific citation" in v for v in check.violations)


# --------------------------------------------------------------------------
# Fabrication detection
# --------------------------------------------------------------------------

def test_validate_answer_flags_fabricated_patent_number():
    check = validate_answer(
        answer="See IN-999999 for the formulation details. [Source 1]",
        sources=_sources("ashwagandha formulation patent landscape"),
        query="ashwagandha formulation patent",
        confidence=0.9,
    )
    assert any("Fabricated patent number" in v for v in check.violations)
    assert check.grounded is False
    assert check.risk_level in (HallucinationRisk.HIGH, HallucinationRisk.CRITICAL)


def test_validate_answer_accepts_patent_number_from_sources():
    check = validate_answer(
        answer="Patent IN-123456 covers the extract. [Source 1]",
        sources=_sources("patent IN-123456 describes extraction", patent_number="IN-123456"),
        query="patent extraction",
        confidence=0.9,
    )
    assert not any("Fabricated patent number" in v for v in check.violations)


def test_validate_answer_flags_fabricated_date():
    check = validate_answer(
        answer="Filed on January 5, 2099. [Source 1]",
        sources=_sources("ashwagandha patent filing process"),
        query="patent filing",
        confidence=0.9,
    )
    assert any("fabricated date" in v for v in check.violations)


def test_validate_answer_accepts_date_present_in_sources():
    check = validate_answer(
        answer="The amendment was dated March 3, 2024. [Source 1]",
        sources=_sources(
            "amendment rules March 3, 2024 update",
            effective_date="March 3, 2024",
        ),
        query="amendment rules",
        confidence=0.9,
    )
    assert not any("fabricated date" in v for v in check.violations)


def test_validate_answer_flags_absolute_claims():
    check = validate_answer(
        answer="This definitely cures disease. [Source 1]",
        sources=_sources("traditional use evidence for the formulation"),
        query="traditional use evidence",
        confidence=0.9,
    )
    assert any("Absolute claim" in v for v in check.violations)


def test_validate_answer_flags_missing_sources():
    check = validate_answer(
        answer="Answer from nothing.",
        sources=[],
        query="ashwagandha",
        confidence=0.5,
    )
    assert "No sources provided for answer generation" in check.violations
    assert check.grounded is False


def test_validate_answer_flags_fabricated_pmid():
    check = validate_answer(
        answer="As shown by PMID: 12345678. [Source 1]",
        sources=_sources("ashwagandha sleep study evidence"),
        query="ashwagandha study",
        confidence=0.9,
    )
    assert any("Fabricated PMID" in v for v in check.violations)


def test_validate_answer_accepts_pmid_present_in_sources():
    check = validate_answer(
        answer="See PMID: 12345678. [Source 1]",
        sources=_sources("study summary PMID: 12345678 confirms effect"),
        query="study summary",
        confidence=0.9,
    )
    assert not any("Fabricated PMID" in v for v in check.violations)


def test_validate_answer_flags_fabricated_pubchem_cid():
    check = validate_answer(
        answer="Compound PubChem CID 999999 is relevant. [Source 1]",
        sources=_sources("ashwagandha withanolide evidence"),
        query="withanolide compound",
        confidence=0.9,
    )
    assert any("PubChem CID" in v for v in check.violations)


def test_validate_answer_flags_fabricated_uniprot_accession():
    check = validate_answer(
        answer="Protein P99999 mediates the effect. [Source 1]",
        sources=_sources("ashwagandha molecular pathway evidence"),
        query="molecular pathway",
        confidence=0.9,
    )
    assert any("UniProt" in v for v in check.violations)


# --------------------------------------------------------------------------
# Refusal gate
# --------------------------------------------------------------------------

def test_should_refuse_without_sources():
    refuse, reason = should_refuse_answer(coverage=1.0, confidence=1.0, num_sources=0)
    assert refuse is True
    assert reason.startswith("NO_SOURCES")


def test_should_refuse_low_coverage():
    refuse, reason = should_refuse_answer(coverage=0.1, confidence=0.9, num_sources=3)
    assert refuse is True
    assert reason.startswith("INSUFFICIENT_COVERAGE")


def test_should_refuse_low_confidence():
    refuse, reason = should_refuse_answer(coverage=0.9, confidence=0.05, num_sources=3)
    assert refuse is True
    assert reason.startswith("LOW_CONFIDENCE")


def test_should_not_refuse_when_healthy():
    refuse, reason = should_refuse_answer(coverage=0.9, confidence=0.9, num_sources=3)
    assert refuse is False
    assert reason == ""


def test_should_refuse_boundary_is_inclusive():
    # exactly at both thresholds is healthy (only strictly below refuses)
    refuse, _ = should_refuse_answer(
        coverage=0.4, confidence=0.2, num_sources=2,
        min_coverage=0.4, min_confidence=0.2, min_sources=2,
    )
    assert refuse is False


# --------------------------------------------------------------------------
# Pre-generation grounding check
# --------------------------------------------------------------------------

def test_grounding_check_grounded_above_threshold():
    result = build_grounding_check(
        query="ashwagandha sleep study evidence",
        sources=_sources("ashwagandha sleep study evidence supports use"),
    )
    assert result["grounded"] is True
    assert result["coverage_ratio"] >= 0.4
    assert result["recommendation"] == "Proceed with answer generation"
    assert result["source_count"] == 1


def test_grounding_check_not_grounded_below_threshold():
    result = build_grounding_check(
        query="ashwagandha sleep study evidence",
        sources=_sources("completely unrelated quantum computing topic"),
    )
    assert result["grounded"] is False
    assert result["coverage_ratio"] < 0.4
    assert "Retrieve additional documents" in result["recommendation"]


def test_grounding_check_reports_uncovered_tokens():
    result = build_grounding_check(
        query="ashwagandha sleep study evidence",
        sources=_sources("ashwagandha"),
    )
    assert result["uncovered_tokens"]
    assert result["covered_tokens"] < result["meaningful_tokens"]
