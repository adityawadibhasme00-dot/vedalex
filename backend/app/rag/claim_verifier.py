"""
Claim-Level Verifier for VEDALEX Verification Layer.

Combines claim extraction + semantic entailment to produce a
claim-level verification table. Each claim in the generated answer
is checked against all retrieved evidence and assigned a status:

  SUPPORTED    — evidence implies or directly states the claim
  CONTRADICTED — evidence conflicts with the claim
  NOT_ENOUGH   — insufficient evidence to confirm or deny

The verification table is the core artifact that judges see:

  Claim                                    Evidence          Status
  ─────────────────────────────────────────────────────────────────
  Section 3(p) is relevant                 Patents Act       ✅ Supported
  TKDL helps prevent wrongful patents      TKDL source       ✅ Supported
  Patent will definitely be rejected       No evidence       ❌ Unsupported
  Application should follow X procedure    Partial evidence  ⚠️ Partial
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from app.rag.claim_extractor import Claim, ClaimType, extract_claims
from app.rag.semantic_entailment import EntailmentVerdict, check_entailments_batch

logger = logging.getLogger(__name__)


@dataclass
class ClaimVerification:
    claim_text: str
    claim_type: str
    status: str  # "SUPPORTED", "CONTRADICTED", "NOT_ENOUGH"
    entailment_score: float
    best_source: Optional[str] = None
    best_source_idx: int = -1
    citations_found: List[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class VerificationTable:
    claims: List[ClaimVerification]
    supported_count: int = 0
    contradicted_count: int = 0
    not_enough_count: int = 0
    total_claims: int = 0
    support_ratio: float = 0.0
    all_supported: bool = False
    has_contradictions: bool = False
    has_unsupported: bool = False


def _source_label(source: Dict[str, Any]) -> str:
    """Build a short human-readable label for a source."""
    parts = []
    for key in ("act_title", "title", "source"):
        val = source.get(key)
        if val:
            parts.append(str(val))
            break
    if source.get("section_heading"):
        parts.append(str(source["section_heading"]))
    if source.get("authority") and source["authority"] != "Official Source":
        parts.append(str(source["authority"]))
    return " — ".join(parts) if parts else "Retrieved Source"


def verify_claims(
    answer: str,
    sources: List[Dict[str, Any]],
) -> VerificationTable:
    """
    Extract claims from the answer and verify each against retrieved evidence.

    For each claim:
      1. Extract it from the answer text
      2. Run semantic entailment against all source chunks
      3. Record the verdict, score, and best matching source

    Returns a VerificationTable with the full claim-by-claim breakdown.
    """
    claims = extract_claims(answer)

    if not claims:
        return VerificationTable(
            claims=[],
            supported_count=0,
            contradicted_count=0,
            not_enough_count=0,
            total_claims=0,
            support_ratio=0.0,
            all_supported=False,
            has_contradictions=False,
            has_unsupported=False,
        )

    verifications: List[ClaimVerification] = []
    claim_texts = [c.text for c in claims]
    results = check_entailments_batch(claim_texts, sources)

    for claim, result in zip(claims, results):
        best_src_label = None
        best_idx = result.best_source_idx
        if 0 <= best_idx < len(sources):
            best_src_label = _source_label(sources[best_idx])

        verifications.append(ClaimVerification(
            claim_text=claim.text,
            claim_type=claim.claim_type.value,
            status=result.verdict.value,
            entailment_score=result.score,
            best_source=best_src_label,
            best_source_idx=best_idx,
            citations_found=claim.citations,
            explanation=result.explanation,
        ))

    supported = sum(1 for v in verifications if v.status == "SUPPORTED")
    contradicted = sum(1 for v in verifications if v.status == "CONTRADICTED")
    not_enough = sum(1 for v in verifications if v.status == "NOT_ENOUGH")
    total = len(verifications)

    table = VerificationTable(
        claims=verifications,
        supported_count=supported,
        contradicted_count=contradicted,
        not_enough_count=not_enough,
        total_claims=total,
        support_ratio=round(supported / max(1, total), 3),
        all_supported=supported == total and total > 0,
        has_contradictions=contradicted > 0,
        has_unsupported=not_enough > 0,
    )

    logger.info(
        f"Claim verification: {supported}/{total} supported, "
        f"{contradicted} contradicted, {not_enough} not enough evidence"
    )
    return table
