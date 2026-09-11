"""
Evidence Confidence Scorer for VEDALEX Verification Layer.

Computes a composite Evidence Confidence score from multiple independent
signals. This replaces raw "accuracy" claims with a transparent,
multi-dimensional confidence metric.

Signals combined:
  1. Retrieval relevance (how well sources match the query)
  2. Citation validity (are citations backed by sources)
  3. Evidence support (claim-level entailment results)
  4. Rule validation (deterministic rule engine status)
  5. Source authority (government > regulatory > peer-reviewed > secondary)
  6. Source diversity (multiple independent sources corroborate)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceSignal:
    name: str
    score: float
    weight: float
    description: str


@dataclass
class EvidenceConfidence:
    overall: float
    band: str  # "HIGH", "MEDIUM", "LOW", "INSUFFICIENT"
    signals: List[ConfidenceSignal]
    supported_ratio: float
    citation_validity: float
    retrieval_coverage: float
    source_authority: float
    source_diversity: float
    rule_engine_pass: Optional[bool]


# Signal weights (must sum to 1.0)
_WEIGHTS = {
    "retrieval": 0.20,
    "citation": 0.15,
    "entailment": 0.30,
    "authority": 0.15,
    "diversity": 0.10,
    "rule": 0.10,
}

# Authority rank mapping (lower = better)
_AUTHORITY_SCORES = {
    "act": 1.0,
    "gazette": 1.0,
    "government": 0.9,
    "regulatory agency": 0.85,
    "patent office": 0.8,
    "wipo": 0.75,
    "peer-reviewed": 0.7,
    "secondary": 0.4,
    "unknown": 0.3,
}


def _source_authority_score(sources: List[Dict[str, Any]]) -> float:
    """Compute average authority score across sources."""
    if not sources:
        return 0.0
    scores = []
    for s in sources:
        # Try explicit authority_level first
        level = s.get("authority_level") or s.get("authority_rank")
        if level is not None:
            try:
                scores.append(1.0 / max(1, int(level)))
            except (ValueError, TypeError):
                scores.append(0.3)
            continue

        # Fall back to keyword matching
        auth_text = str(s.get("authority", "")).lower()
        cat_text = str(s.get("category", "")).lower()
        combined = f"{auth_text} {cat_text}"

        matched = False
        for key, score in _AUTHORITY_SCORES.items():
            if key in combined:
                scores.append(score)
                matched = True
                break
        if not matched:
            scores.append(0.3)

    return sum(scores) / len(scores) if scores else 0.0


def _source_diversity_score(sources: List[Dict[str, Any]]) -> float:
    """Measure how many distinct source categories are represented."""
    if not sources:
        return 0.0
    categories = set()
    for s in sources:
        cat = s.get("category", "") or s.get("retrieval_method", "") or "unknown"
        categories.add(cat.lower())
    # 4+ distinct categories = full diversity
    return min(1.0, len(categories) / 4.0)


def _compute_overall(
    signals: List[ConfidenceSignal],
) -> float:
    """Weighted average of all signals."""
    total_weight = sum(s.weight for s in signals)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(s.score * s.weight for s in signals)
    return round(min(1.0, max(0.0, weighted_sum / total_weight)), 3)


def _score_to_band(score: float) -> str:
    """Map overall score to a confidence band."""
    if score >= 0.75:
        return "HIGH"
    if score >= 0.50:
        return "MEDIUM"
    if score >= 0.25:
        return "LOW"
    return "INSUFFICIENT"


def compute_evidence_confidence(
    sources: List[Dict[str, Any]],
    grounding: Optional[Dict[str, Any]] = None,
    supported_ratio: float = 0.0,
    citation_validity: float = 0.0,
    rule_engine_pass: Optional[bool] = None,
) -> EvidenceConfidence:
    """
    Compute composite Evidence Confidence from all available signals.

    Parameters:
      sources: Retrieved evidence chunks
      grounding: Grounding check result from hallucination_guard
      supported_ratio: Fraction of claims that are SUPPORTED (0.0-1.0)
      citation_validity: Fraction of citations that are valid (0.0-1.0)
      rule_engine_pass: Rule engine result (True/False/None)

    Returns:
      EvidenceConfidence with overall score, band, and per-signal breakdown.
    """
    signals: List[ConfidenceSignal] = []

    # 1. Retrieval coverage
    retrieval_cov = 0.0
    if grounding:
        retrieval_cov = grounding.get("coverage_ratio", 0.0)
    signals.append(ConfidenceSignal(
        name="retrieval_coverage",
        score=retrieval_cov,
        weight=_WEIGHTS["retrieval"],
        description=f"Query token coverage in sources: {retrieval_cov:.1%}",
    ))

    # 2. Citation validity
    signals.append(ConfidenceSignal(
        name="citation_validity",
        score=citation_validity,
        weight=_WEIGHTS["citation"],
        description=f"Citation validity rate: {citation_validity:.1%}",
    ))

    # 3. Claim-level evidence support (entailment)
    signals.append(ConfidenceSignal(
        name="evidence_support",
        score=supported_ratio,
        weight=_WEIGHTS["entailment"],
        description=f"Claims supported by evidence: {supported_ratio:.1%}",
    ))

    # 4. Source authority
    auth_score = _source_authority_score(sources)
    signals.append(ConfidenceSignal(
        name="source_authority",
        score=auth_score,
        weight=_WEIGHTS["authority"],
        description=f"Average source authority: {auth_score:.2f}",
    ))

    # 5. Source diversity
    div_score = _source_diversity_score(sources)
    signals.append(ConfidenceSignal(
        name="source_diversity",
        score=div_score,
        weight=_WEIGHTS["diversity"],
        description=f"Source category diversity: {div_score:.2f}",
    ))

    # 6. Rule engine validation
    rule_score = 0.5  # Neutral when no rule engine result
    if rule_engine_pass is True:
        rule_score = 1.0
    elif rule_engine_pass is False:
        rule_score = 0.0
    signals.append(ConfidenceSignal(
        name="rule_validation",
        score=rule_score,
        weight=_WEIGHTS["rule"],
        description=f"Rule engine: {'PASS' if rule_engine_pass is True else ('FAIL' if rule_engine_pass is False else 'N/A')}",
    ))

    # Compute overall
    overall = _compute_overall(signals)
    band = _score_to_band(overall)

    return EvidenceConfidence(
        overall=overall,
        band=band,
        signals=signals,
        supported_ratio=supported_ratio,
        citation_validity=citation_validity,
        retrieval_coverage=retrieval_cov,
        source_authority=auth_score,
        source_diversity=div_score,
        rule_engine_pass=rule_engine_pass,
    )
