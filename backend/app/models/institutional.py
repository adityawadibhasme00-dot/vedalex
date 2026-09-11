from pydantic import BaseModel, Field
from typing import List, Dict, Any

class IncubatorCaseSummary(BaseModel):
    case_id: str
    startup_name: str
    product_name: str
    target_markets: List[str]
    current_status: str
    coverage_meter: int
    assigned_reviewer: str
    last_updated: str

class CohortGapMetric(BaseModel):
    gap_title: str
    affected_startups_count: int
    percentage: float
    recommended_workshop_action: str

class InstitutionalDashboardData(BaseModel):
    organization_name: str = "AYUSH National Innovation Incubator"
    total_active_cases: int
    pending_expert_reviews: int
    avg_coverage_meter: int
    cases: List[IncubatorCaseSummary]
    top_cohort_gaps: List[CohortGapMetric]
