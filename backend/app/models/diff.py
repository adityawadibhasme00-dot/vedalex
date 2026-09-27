
from pydantic import BaseModel, Field

from app.models.regulatory import StatutoryCitation


class WhatIfDiffItem(BaseModel):
    jurisdiction: str
    prior_classification: str
    new_classification: str
    impact_severity: str  # "LOW", "MODERATE_BURDEN_INCREASE", "CRITICAL_BURDEN_INCREASE"
    risk_alert: str
    removed_requirements: list[str] = Field(default_factory=list)
    new_requirements: list[str] = Field(default_factory=list)
    new_citations: list[StatutoryCitation] = Field(default_factory=list)

class WhatIfSimulationResponse(BaseModel):
    original_claims: list[str]
    mutated_claims: list[str]
    affected_nodes_count: int
    diffs: list[WhatIfDiffItem]

class RegulatoryDiffRecord(BaseModel):
    id: str
    source_authority: str
    act_title: str
    prior_version_date: str
    new_version_date: str
    summary_of_change: str
    affected_provisions: list[str]
    affected_case_ids: list[str]
    severity: str = "HIGH"
