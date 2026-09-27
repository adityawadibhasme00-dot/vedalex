from enum import StrEnum

from pydantic import BaseModel, Field


class EvidenceLifecycle(StrEnum):
    MISSING = "Missing"
    UPLOADED = "Uploaded"
    NEEDS_REVIEW = "Needs review"
    ACCEPTED = "Accepted for this assessment"

class EvidenceItem(BaseModel):
    id: str
    passport_id: str
    requirement_name: str
    why_it_applies: str
    expected_evidence_type: str  # "Lab Certificate", "Classical Text Citation", "GMP Audit", "Stability Data"
    status: EvidenceLifecycle = EvidenceLifecycle.MISSING
    supplied_filename: str | None = None
    prerequisites: list[str] = Field(default_factory=list)
    next_action: str
    jurisdiction: str = "India"

class EvidenceGapSummary(BaseModel):
    passport_id: str
    total_checks: int
    evaluated_checks: int
    blocked_by_missing_sources: int
    coverage_meter_percentage: int  # Describes task completion, NOT approval probability
    items: list[EvidenceItem]
