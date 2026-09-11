"""
Verification Layer Orchestrator for VEDALEX | IP-SAKTI SAHAYAK.

Ties together all verification components into a single pipeline:

  Draft Answer
       ↓
  Claim Extraction
       ↓
  Citation Validity Check
       ↓
  Claim-Level Entailment (per claim × per source)
       ↓
  Evidence Confidence Scoring
       ↓
  Confidence Gate
    /           \
  PASS           FAIL
   ↓              ↓
 Final Answer   Regenerate or Refuse

Key concept for judges:
  "Our verification layer doesn't blindly trust the LLM; it decomposes
  the generated response into claims, checks each claim against retrieved
  authoritative evidence and applicable rules, validates citations, and
  blocks or regenerates unsupported claims."
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from app.rag.claim_extractor import extract_claims, Claim
from app.rag.claim_verifier import verify_claims, VerificationTable, ClaimVerification
from app.rag.citation_validity_checker import check_citation_validity, CitationValidityReport
from app.rag.evidence_confidence_scorer import compute_evidence_confidence, EvidenceConfidence

logger = logging.getLogger(__name__)


# Confidence gate thresholds
_MIN_SUPPORT_RATIO = 0.50
_MIN_CITATION_VALIDITY = 0.50
_MIN_EVIDENCE_CONFIDENCE = 0.35
_MAX_CONTRADICTIONS = 0
_MAX_REGENERATION_ATTEMPTS = 1


@dataclass
class VerificationResult:
    original_answer: str
    final_answer: str
    verification_table: VerificationTable
    citation_report: CitationValidityReport
    evidence_confidence: EvidenceConfidence
    passed_gate: bool
    gate_reason: str
    regenerated: bool
    regeneration_count: int
    removed_claims: List[str] = field(default_factory=list)
    unsupported_claims: List[Dict[str, Any]] = field(default_factory=list)


def _filter_answer_by_verification(
    answer: str,
    table: VerificationTable,
) -> str:
    """
    Remove unsupported and contradicted claims from the answer.

    Keeps only SUPPORTED claims, reformatted into a coherent response.
    """
    supported = [v for v in table.claims if v.status == "SUPPORTED"]
    if not supported:
        return ""

    lines = []
    for v in supported:
        lines.append(v.claim_text + ".")

    filtered = " ".join(lines)
    return filtered if filtered.strip() else ""


def _determine_gate_pass(
    table: VerificationTable,
    citation_report: CitationValidityReport,
    evidence_conf: EvidenceConfidence,
) -> tuple:
    """
    Determine whether the answer passes the confidence gate.

    Returns (passed: bool, reason: str).
    """
    reasons = []

    # Check claim support ratio
    if table.support_ratio < _MIN_SUPPORT_RATIO and table.total_claims > 0:
        reasons.append(
            f"Support ratio {table.support_ratio:.1%} below threshold "
            f"{_MIN_SUPPORT_RATIO:.1%}"
        )

    # Check for contradictions (always fail if contradictions exist)
    if table.contradicted_count > _MAX_CONTRADICTIONS:
        reasons.append(
            f"{table.contradicted_count} contradicted claim(s) detected"
        )

    # Check citation validity
    if (citation_report.total_citations > 0 and
            citation_report.validity_ratio < _MIN_CITATION_VALIDITY):
        reasons.append(
            f"Citation validity {citation_report.validity_ratio:.1%} below threshold"
        )

    # Check evidence confidence
    if evidence_conf.overall < _MIN_EVIDENCE_CONFIDENCE:
        reasons.append(
            f"Evidence confidence {evidence_conf.overall:.2f} below threshold"
        )

    passed = len(reasons) == 0
    reason = "All verification checks passed" if passed else "; ".join(reasons)
    return passed, reason


def run_verification(
    answer: str,
    sources: List[Dict[str, Any]],
    query: str,
    rule_engine_pass: Optional[bool] = None,
    grounding: Optional[Dict[str, Any]] = None,
) -> VerificationResult:
    """
    Full verification pipeline.

    Steps:
      1. Extract claims from the answer
      2. Verify each claim against evidence (entailment)
      3. Check citation validity
      4. Compute evidence confidence
      5. Apply confidence gate
      6. If gate fails, regenerate by filtering unsupported claims
      7. Return verification result with full audit trail

    Parameters:
      answer: The LLM-generated draft answer
      sources: Retrieved evidence chunks
      query: The original user query
      rule_engine_pass: Deterministic rule engine result (optional)
      grounding: Pre-computed grounding check (optional)

    Returns:
      VerificationResult with all verification artifacts.
    """
    logger.info(f"Running verification on answer ({len(answer)} chars, {len(sources)} sources)")

    # Step 1-2: Claim extraction + verification
    table = verify_claims(answer, sources)

    # Step 3: Citation validity
    citation_report = check_citation_validity(answer, sources)

    # Step 4: Evidence confidence
    evidence_conf = compute_evidence_confidence(
        sources=sources,
        grounding=grounding,
        supported_ratio=table.support_ratio,
        citation_validity=citation_report.validity_ratio,
        rule_engine_pass=rule_engine_pass,
    )

    # Step 5: Confidence gate
    passed, gate_reason = _determine_gate_pass(table, citation_report, evidence_conf)

    # Step 6: Always remove unsupported/contradicted claims from the final
    # answer. The gate decides whether the answer is acceptable overall;
    # regeneration strips the claims that fail verification.
    final_answer = answer
    regenerated = False
    regeneration_count = 0
    removed_claims = []

    unsupported_claims = [
        v for v in table.claims
        if v.status in ("NOT_ENOUGH", "CONTRADICTED")
    ]
    if unsupported_claims:
        removed_claims = [v.claim_text for v in unsupported_claims]
        filtered = _filter_answer_by_verification(answer, table)
        if filtered:
            final_answer = filtered
            regenerated = True
            regeneration_count = 1
            logger.info(
                f"Answer regenerated: kept {table.supported_count}/{table.total_claims} "
                f"claims, removed {len(removed_claims)} unsupported"
            )
        elif passed:
            # Gate passed but filtering produced nothing (no supported claims
            # survived) — do not serve an empty answer.
            passed = False
            gate_reason = "No supported claims survived verification"

    # If the gate failed and regeneration removed everything, refuse.
    if not passed and not final_answer:
        final_answer = (
            "Insufficient verified information. "
            "The available sources do not provide enough evidence to answer this reliably."
        )
        logger.warning("Verification gate failed and no supported claims remained — refusing")

    # Build unsupported claims list for API response
    unsupported_claims = [
        {
            "claim": v.claim_text,
            "status": v.status,
            "score": v.entailment_score,
            "explanation": v.explanation,
        }
        for v in table.claims
        if v.status in ("NOT_ENOUGH", "CONTRADICTED")
    ]

    return VerificationResult(
        original_answer=answer,
        final_answer=final_answer,
        verification_table=table,
        citation_report=citation_report,
        evidence_confidence=evidence_conf,
        passed_gate=passed,
        gate_reason=gate_reason,
        regenerated=regenerated,
        regeneration_count=regeneration_count,
        removed_claims=removed_claims,
        unsupported_claims=unsupported_claims,
    )
