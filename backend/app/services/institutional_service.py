from typing import List, Dict, Any
from app.models.institutional import InstitutionalDashboardData, IncubatorCaseSummary, CohortGapMetric

class InstitutionalService:
    """
    Institutional / Multi-Tenant Service (Section 7.4.1).
    Provides incubator cohort management, reviewer queues, and aggregated non-identifying compliance gap metrics.
    """

    @classmethod
    def get_dashboard_data(cls) -> InstitutionalDashboardData:
        cases = [
            IncubatorCaseSummary(
                case_id="CASE-AYUR-001",
                startup_name="VedaNidra Therapeutics Pvt Ltd",
                product_name="AshwaCalm Sleep Formulation",
                target_markets=["India", "USA", "Canada"],
                current_status="Pre-filing Triage Complete",
                coverage_meter=82,
                assigned_reviewer="Dr. R. Sharma (IP Facilitator)",
                last_updated="2026-09-06"
            ),
            IncubatorCaseSummary(
                case_id="CASE-AYUR-002",
                startup_name="SiddhaBio Innovations",
                product_name="Brahmi NeuroRevive Elixir",
                target_markets=["India", "Canada"],
                current_status="Awaiting Heavy Metal Lab Report",
                coverage_meter=65,
                assigned_reviewer="Adv. P. Deshmukh (Patent Agent)",
                last_updated="2026-09-05"
            ),
            IncubatorCaseSummary(
                case_id="CASE-AYUR-003",
                startup_name="Haridra Curcumin Labs",
                product_name="Nano-Haridra Anti-inflammatory Vati",
                target_markets=["India", "USA"],
                current_status="Section 3(p) Synergy Test in Progress",
                coverage_meter=74,
                assigned_reviewer="Dr. V. Kulkarni (AYUSH Consultant)",
                last_updated="2026-09-04"
            )
        ]

        gaps = [
            CohortGapMetric(
                gap_title="Missing Section 3(p) Synergy Empirical Assay Data",
                affected_startups_count=18,
                percentage=72.0,
                recommended_workshop_action="Organize institutional webinar on Chou-Talalay combination-index testing for patent novelty."
            ),
            CohortGapMetric(
                gap_title="Foreign Site Licence Annex Missing for US/Canada Export",
                affected_startups_count=14,
                percentage=56.0,
                recommended_workshop_action="Facilitate GMP equivalence audit workshops with certified Canadian regulatory partners."
            ),
            CohortGapMetric(
                gap_title="Disease Treatment Claim Wording in FSSAI Food Applications",
                affected_startups_count=11,
                percentage=44.0,
                recommended_workshop_action="Distribute FSSAI 2022 Structure/Function claim template guide."
            )
        ]

        return InstitutionalDashboardData(
            organization_name="National AYUSH Startup Innovation Hub",
            total_active_cases=25,
            pending_expert_reviews=6,
            avg_coverage_meter=74,
            cases=cases,
            top_cohort_gaps=gaps
        )
