from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.core.confidence import ConfidenceBand

class RuleConditionState(str, Enum):
    SATISFIED = "condition_satisfied"
    NOT_SATISFIED = "condition_not_satisfied"
    INSUFFICIENT_INFO = "insufficient_information"

class StatutoryCitation(BaseModel):
    act_title: str
    section_reference: str
    authority: str
    effective_date: str
    exact_passage: str
    source_url: Optional[str] = None
    authority_rank: int = 1  # 1 = Act/Gazette, 2 = Regulatory Agency, 3 = Guidelines

class RegulatoryFinding(BaseModel):
    jurisdiction: str  # "India", "United States", "Canada"
    pathway_category: str  # e.g. "Ayurveda Aahara (FSSAI 2022)", "ASU Classical", "DSHEA Supplement"
    status: RuleConditionState
    confidence: ConfidenceBand
    conditions_evaluated: List[str]
    supporting_citations: List[StatutoryCitation] = Field(default_factory=list)
    missing_facts: List[str] = Field(default_factory=list)
    next_action_steps: List[str] = Field(default_factory=list)
    coverage_limitations: str
    assumptions_made: List[str] = Field(default_factory=list)
    explanation_text: Optional[str] = None

class AssessmentResponse(BaseModel):
    assessment_id: str
    passport_id: str
    timestamp: str
    language: str
    findings: List[RegulatoryFinding]
    coverage_meter_score: int = 80
    unsupported_claim_rate: float = 0.0
