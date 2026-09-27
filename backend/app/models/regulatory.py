from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.core.confidence import ConfidenceBand


class RuleConditionState(StrEnum):
    SATISFIED = "condition_satisfied"
    NOT_SATISFIED = "condition_not_satisfied"
    INSUFFICIENT_INFO = "insufficient_information"

class StatutoryCitation(BaseModel):
    act_title: str
    section_reference: str
    authority: str
    effective_date: str
    exact_passage: str
    source_url: str | None = None
    authority_rank: int = 1  # 1 = Act/Gazette, 2 = Regulatory Agency, 3 = Guidelines

class RegulatoryFinding(BaseModel):
    jurisdiction: str  # "India", "United States", "Canada"
    pathway_category: str  # e.g. "Ayurveda Aahara (FSSAI 2022)", "ASU Classical", "DSHEA Supplement"
    status: RuleConditionState
    confidence: ConfidenceBand
    conditions_evaluated: list[str]
    supporting_citations: list[StatutoryCitation] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    next_action_steps: list[str] = Field(default_factory=list)
    coverage_limitations: str
    assumptions_made: list[str] = Field(default_factory=list)
    explanation_text: str | None = None
    risk_level: str = "low"  # critical | high | medium | low
    requires_human_review: bool = False
    applied_rules: list[dict[str, Any]] = Field(default_factory=list)

class AssessmentResponse(BaseModel):
    assessment_id: str
    passport_id: str
    timestamp: str
    language: str
    findings: list[RegulatoryFinding]
    coverage_meter_score: int = 80
    unsupported_claim_rate: float = 0.0
