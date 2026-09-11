from app.rag.claim_extractor import extract_claims, ClaimType
from app.rag.claim_verifier import verify_claims
from app.rag.citation_validity_checker import check_citation_validity
from app.rag.evidence_confidence_scorer import compute_evidence_confidence
from app.rag.verification_orchestrator import run_verification

SOURCES = [
    {
        "content": (
            "Section 3(p) of the Patents Act 1970 excludes traditional knowledge "
            "which is already known to the public from patentability. The TKDL "
            "documents traditional knowledge to prevent biopiracy."
        ),
        "act_title": "Patents Act, 1970",
        "section_heading": "Section 3(p)",
        "authority": "Government of India",
        "authority_level": 1,
        "category": "statutory",
        "retrieval_method": "statutory",
    },
    {
        "content": (
            "The TKDL provides a database of traditional knowledge for patent "
            "examiners to prevent wrongful patents on traditional innovations."
        ),
        "act_title": "TKDL",
        "authority": "CSIR",
        "authority_level": 2,
        "category": "tkdl",
        "retrieval_method": "semantic",
    },
]

ANSWER = (
    "Traditional knowledge already known to the public cannot be patented "
    "under Section 3(p) of the Patents Act. The TKDL helps prevent wrongful "
    "patents on traditional knowledge. Patent will definitely be rejected if filed."
)


def test_claim_extraction_breaks_answer_into_claims():
    claims = extract_claims(ANSWER)
    assert len(claims) >= 2, "Answer should decompose into multiple claims"
    types = [c.claim_type for c in claims]
    assert ClaimType.LEGAL in types or ClaimType.FACTUAL in types


def test_claim_verification_supports_grounded_claims():
    table = verify_claims(ANSWER, SOURCES)
    assert table.total_claims > 0
    supported_text = " ".join(
        v.claim_text for v in table.claims if v.status == "SUPPORTED"
    )
    assert "Section 3(p)" in supported_text
    assert "patented" in supported_text


def test_citation_validity_verifies_real_citations():
    report = check_citation_validity(
        "Section 3(p) of the Patents Act prevents patenting TK.", SOURCES
    )
    assert report.total_citations >= 2
    assert report.valid_citations >= 2
    assert report.all_valid
    assert report.validity_ratio == 1.0


def test_citation_validity_flags_fabricated_section():
    report = check_citation_validity(
        "Section 999(x) of the Code of Neverland restricts everything.", SOURCES
    )
    assert report.total_citations >= 1
    assert report.invalid_citations >= 1
    assert not report.all_valid


def test_evidence_confidence_bands():
    ec = compute_evidence_confidence(
        SOURCES,
        grounding={"coverage_ratio": 0.9},
        supported_ratio=1.0,
        citation_validity=1.0,
        rule_engine_pass=True,
    )
    assert ec.overall >= 0.5
    assert ec.band in ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT")
    assert len(ec.signals) == 6


def test_unsupported_claims_removed_from_final_answer():
    vr = run_verification(ANSWER, SOURCES, "Can TK be patented in India?")
    assert vr.final_answer != vr.original_answer
    assert "definitely be rejected" not in vr.final_answer
    assert vr.regenerated or vr.removed_claims


def test_full_refusal_when_nothing_is_supported():
    vr = run_verification(
        "Pink elephants fly over the moon on Tuesdays.",
        SOURCES,
        "Do pink elephants fly?",
    )
    if vr.verification_table.total_claims > 0:
        assert not vr.passed_gate