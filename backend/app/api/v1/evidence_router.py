from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.models.evidence import EvidenceItem, EvidenceGapSummary, EvidenceLifecycle

router = APIRouter(prefix="/evidence", tags=["Evidence & Action Engine"])

class EvidenceStatusUpdateRequest(BaseModel):
    status: EvidenceLifecycle
    supplied_filename: Optional[str] = None

# In-memory store for demonstration
_evidence_store: dict = {}

@router.get("/{passport_id}", response_model=EvidenceGapSummary)
async def get_evidence_gaps(passport_id: str):
    if passport_id not in _evidence_store:
        items = [
            EvidenceItem(
                id="EV-01",
                passport_id=passport_id,
                requirement_name="Heavy Metals & Microbiological Safety Certificate",
                why_it_applies="FSSAI Ayurveda Aahara Reg 4(1) and AYUSH Gazette requirement for lead, cadmium, arsenic, and mercury limits.",
                expected_evidence_type="NABL-Accredited Lab Test Certificate",
                status=EvidenceLifecycle.MISSING,
                next_action="Commission heavy metals and microbial limit testing at an approved NABL facility.",
                jurisdiction="India"
            ),
            EvidenceItem(
                id="EV-02",
                passport_id=passport_id,
                requirement_name="Section 3(p) Synergy Combination-Index Data",
                why_it_applies="Indian Patents Act Section 3(p) bar on traditional knowledge aggregation without proven synergistic efficacy.",
                expected_evidence_type="In-Vitro / In-Vivo Synergy Assay Report",
                status=EvidenceLifecycle.NEEDS_REVIEW,
                supplied_filename="synergy_assay_draft.pdf",
                next_action="Calculate combination index (CI < 0.8) to establish true pharmacological synergism.",
                jurisdiction="India"
            ),
            EvidenceItem(
                id="EV-03",
                passport_id=passport_id,
                requirement_name="US FDA 30-Day Structure/Function Notification Draft",
                why_it_applies="Mandatory 21 CFR 101.93 submission within 30 days of first marketing dietary supplement in interstate commerce.",
                expected_evidence_type="FDA Form Letter / Cover Letter",
                status=EvidenceLifecycle.UPLOADED,
                supplied_filename="fda_dshea_30day_notice.docx",
                next_action="Finalize exact label structure/function text before dispatching letter to FDA CDER.",
                jurisdiction="United States"
            ),
            EvidenceItem(
                id="EV-04",
                passport_id=passport_id,
                requirement_name="Health Canada Foreign Site Annex GMP Audit",
                why_it_applies="NHPR SOR/2003-196 Part 3 requires foreign manufacturing facilities to demonstrate GMP equivalence.",
                expected_evidence_type="GMP Equivalence Audit Package",
                status=EvidenceLifecycle.ACCEPTED,
                supplied_filename="who_gmp_certificate_2026.pdf",
                next_action="Ready for ePLA submission.",
                jurisdiction="Canada"
            )
        ]
        _evidence_store[passport_id] = items

    items = _evidence_store[passport_id]
    total = len(items)
    evaluated = sum(1 for i in items if i.status in [EvidenceLifecycle.UPLOADED, EvidenceLifecycle.NEEDS_REVIEW, EvidenceLifecycle.ACCEPTED])
    blocked = total - evaluated
    coverage_pct = int((evaluated / total) * 100) if total > 0 else 0

    return EvidenceGapSummary(
        passport_id=passport_id,
        total_checks=total,
        evaluated_checks=evaluated,
        blocked_by_missing_sources=blocked,
        coverage_meter_percentage=coverage_pct,
        items=items
    )

@router.put("/item/{item_id}/lifecycle", response_model=EvidenceItem)
async def update_lifecycle(item_id: str, req: EvidenceStatusUpdateRequest):
    for passport_id, items in _evidence_store.items():
        for item in items:
            if item.id == item_id:
                item.status = req.status
                if req.supplied_filename:
                    item.supplied_filename = req.supplied_filename
                return item
    raise HTTPException(status_code=404, detail="Evidence item not found")
