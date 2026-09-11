from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.models.regulatory import StatutoryCitation

class WhatIfDiffItem(BaseModel):
    jurisdiction: str
    prior_classification: str
    new_classification: str
    impact_severity: str  # "LOW", "MODERATE_BURDEN_INCREASE", "CRITICAL_BURDEN_INCREASE"
    risk_alert: str
    removed_requirements: List[str] = Field(default_factory=list)
    new_requirements: List[str] = Field(default_factory=list)
    new_citations: List[StatutoryCitation] = Field(default_factory=list)

class WhatIfSimulationResponse(BaseModel):
    original_claims: List[str]
    mutated_claims: List[str]
    affected_nodes_count: int
    diffs: List[WhatIfDiffItem]

class RegulatoryDiffRecord(BaseModel):
    id: str
    source_authority: str
    act_title: str
    prior_version_date: str
    new_version_date: str
    summary_of_change: str
    affected_provisions: List[str]
    affected_case_ids: List[str]
    severity: str = "HIGH"
