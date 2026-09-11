import uuid
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.models.regulatory import AssessmentResponse, RegulatoryFinding
from app.services.passport_engine import PassportEngine
from app.services.rule_engine import DeterministicRuleEngine
from app.services.citation_validator import CitationValidator
from app.services.provenance_engine import ProvenanceEngine

router = APIRouter(prefix="/assessment", tags=["Regulatory & IP Assessment"])

class AssessmentRequest(BaseModel):
    passport_id: str
    target_markets: Optional[List[str]] = ["India", "United States", "Canada"]
    language: Optional[str] = "en"

@router.post("/evaluate", response_model=AssessmentResponse)
async def evaluate_assessment(req: AssessmentRequest):
    passport = PassportEngine.get_passport(req.passport_id)
    if not passport:
        # Create on the fly if not yet persisted
        passport = PassportEngine.create_from_intake(
            raw_text="Ashwagandha + Brahmi formulation, claim: supports healthy sleep",
            user_lang=req.language or "en"
        )

    raw_findings = DeterministicRuleEngine.evaluate_passport(
        passport,
        target_markets=req.target_markets or ["India", "United States", "Canada"]
    )
    
    audited_findings, ucr = CitationValidator.audit_findings(raw_findings)

    return AssessmentResponse(
        assessment_id=str(uuid.uuid4()),
        passport_id=passport.id,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        language=req.language or "en",
        findings=audited_findings,
        coverage_meter_score=82,
        unsupported_claim_rate=ucr
    )

@router.get("/{passport_id}/provenance")
async def get_provenance(passport_id: str, jurisdiction: str = "India"):
    passport = PassportEngine.get_passport(passport_id)
    if not passport:
        passport = PassportEngine.create_from_intake("Ashwagandha + Brahmi")

    findings = DeterministicRuleEngine.evaluate_passport(passport, [jurisdiction])
    target_finding = next((f for f in findings if f.jurisdiction.lower() == jurisdiction.lower()), None)
    if not target_finding:
        target_finding = findings[0] if findings else None

    if not target_finding:
        raise HTTPException(status_code=404, detail="Finding not found for jurisdiction")

    return ProvenanceEngine.generate_provenance_graph(passport, target_finding)
