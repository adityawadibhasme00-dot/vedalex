from enum import Enum
from typing import Dict, Any, List

class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class ConfidenceEvaluator:
    """
    Computes deterministic calibrated confidence bands and abstention triggers (Section 7.1.1).
    Derived from retrieval coverage, rule condition completeness, and citation validator status,
    NOT from raw LLM token probabilities.
    """
    @staticmethod
    def calculate(
        rule_satisfied: bool,
        missing_critical_facts: List[str],
        citation_count: int,
        canonical_resolution_confidence: float,
        has_primary_statute: bool
    ) -> ConfidenceBand:
        if len(missing_critical_facts) > 0 and not rule_satisfied:
            return ConfidenceBand.INSUFFICIENT_EVIDENCE

        if canonical_resolution_confidence < 0.6:
            return ConfidenceBand.INSUFFICIENT_EVIDENCE

        if rule_satisfied and has_primary_statute and citation_count >= 1 and canonical_resolution_confidence >= 0.9:
            return ConfidenceBand.HIGH

        if rule_satisfied and citation_count >= 1 and canonical_resolution_confidence >= 0.7:
            return ConfidenceBand.MEDIUM

        if not rule_satisfied or citation_count == 0:
            return ConfidenceBand.LOW

        return ConfidenceBand.MEDIUM
