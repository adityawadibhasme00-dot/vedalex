
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.sandboxing import DocumentSanitizer
from app.models.passport import ClarificationQuery, InnovationPassport
from app.services.passport_engine import PassportEngine

router = APIRouter(prefix="/passport", tags=["Innovation Passport"])

class IntakeRequest(BaseModel):
    raw_text: str
    user_lang: str = "en"
    case_title: str | None = "Ayurvedic Botanical Formulation"
    product_type: str | None = None
    category: str | None = None
    target_markets: list[str] | None = None
    extraction_method: str | None = None
    solvent: str | None = None
    temperature: str | None = None
    time: str | None = None
    processing_steps: str | None = None
    proposed_claims: list[str] | None = None

class DocumentSanitizeRequest(BaseModel):
    document_text: str
    filename: str | None = "label_or_report.pdf"

@router.post("/create", response_model=InnovationPassport)
def create_passport(req: IntakeRequest):
    sanitized_text, threats = DocumentSanitizer.sanitize(req.raw_text, source_filename="intake_text")
    passport = PassportEngine.create_from_intake(
        raw_text=sanitized_text,
        user_lang=req.user_lang,
        title=req.case_title or "Ayurvedic Botanical Formulation",
        intake={
            "product_type": req.product_type,
            "category": req.category,
            "target_markets": req.target_markets,
            "extraction_method": req.extraction_method,
            "solvent": req.solvent,
            "temperature": req.temperature,
            "time": req.time,
            "processing_steps": req.processing_steps,
            "proposed_claims": req.proposed_claims,
        } if any([
            req.product_type, req.category, req.target_markets, req.extraction_method,
            req.solvent, req.temperature, req.time, req.processing_steps, req.proposed_claims,
        ]) else None,
    )
    return passport

@router.get("/{passport_id}", response_model=InnovationPassport)
def get_passport(passport_id: str):
    passport = PassportEngine.get_passport(passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")
    return passport

@router.put("/{passport_id}/update", response_model=InnovationPassport)
def update_passport(passport_id: str, passport: InnovationPassport):
    existing = PassportEngine.get_passport(passport_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Passport not found")
    updated = PassportEngine.update_passport(passport)
    return updated

@router.get("/{passport_id}/clarifications", response_model=list[ClarificationQuery])
def get_clarifications(passport_id: str):
    passport = PassportEngine.get_passport(passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")
    return PassportEngine.get_clarifications_for_passport(passport)

@router.post("/sanitize-document")
def sanitize_document(req: DocumentSanitizeRequest):
    cleaned, threats = DocumentSanitizer.sanitize(req.document_text, req.filename or "upload.txt")
    return {
        "status": "success",
        "cleaned_text": cleaned,
        "threats_detected_and_neutralized": threats,
        "is_safe_for_reasoning": True
    }
