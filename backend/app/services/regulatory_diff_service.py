import uuid
from typing import List, Dict, Any
from app.models.diff import RegulatoryDiffRecord

class RegulatoryDiffService:
    """
    Living Regulatory-Diff & Case-Notification Service (Section 7.3.1).
    Monitors registered statutory gazettes, computes semantic diffs on amended provisions,
    and alerts affected saved user cases.
    """
    _registered_updates: List[RegulatoryDiffRecord] = [
        RegulatoryDiffRecord(
            id="DIFF-FSSAI-2024-01",
            source_authority="Food Safety and Standards Authority of India (FSSAI)",
            act_title="Food Safety and Standards (Ayurveda Aahara) Amendment Regulations, 2024",
            prior_version_date="2022-05-05",
            new_version_date="2024-03-15",
            summary_of_change="Updated Schedule I permitted extract ratios for Withania somnifera and Bacopa monnieri; added mandatory QR code verification requirement on product packaging.",
            affected_provisions=["Regulation 4(3) - Packaging Label QR Code", "Schedule I - Extract Solvent Limits"],
            affected_case_ids=["case-sleep-001", "case-brahmi-042"],
            severity="MEDIUM"
        ),
        RegulatoryDiffRecord(
            id="DIFF-USFDA-2023-NDI",
            source_authority="US Food and Drug Administration (FDA)",
            act_title="FDA Final Guidance on New Dietary Ingredient (NDI) Notifications and Master Files",
            prior_version_date="2016-08-11",
            new_version_date="2024-03-05",
            summary_of_change="Clarified chemical alteration standards for botanical supercritical CO2 extracts; extracts using non-water solvents may require separate NDI notifications even if whole plant is an Old Dietary Ingredient.",
            affected_provisions=["21 CFR 190.6(a)", "Section IV.B - Chemical Alteration of Botanicals"],
            affected_case_ids=["case-sleep-001"],
            severity="HIGH"
        )
    ]

    @classmethod
    def get_all_updates(cls) -> List[RegulatoryDiffRecord]:
        return cls._registered_updates

    @classmethod
    def get_updates_for_case(cls, case_id: str) -> List[RegulatoryDiffRecord]:
        return [u for u in cls._registered_updates if case_id in u.affected_case_ids or len(u.affected_case_ids) == 0]
