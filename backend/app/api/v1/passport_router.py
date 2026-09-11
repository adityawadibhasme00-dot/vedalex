from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.models.passport import InnovationPassport, ClarificationQuery
from app.services.passport_engine import PassportEngine
from app.core.sandboxing import DocumentSanitizer

router = APIRouter(prefix="/passport", tags=["Innovation Passport"])

class IntakeRequest(BaseModel):
    raw_text: str
    user_lang: str = "en"
    case_title: Optional[str] = "Ayurvedic Restful Sleep Formulation"

class DocumentSanitizeRequest(BaseModel):
    document_text: str
    filename: Optional[str] = "label_or_report.pdf"

@router.post("/create", response_model=InnovationPassport)
async def create_passport(req: IntakeRequest):
    sanitized_text, threats = DocumentSanitizer.sanitize(req.raw_text, source_filename="intake_text")
    passport = PassportEngine.create_from_intake(
        raw_text=sanitized_text,
        user_lang=req.user_lang,
        title=req.case_title or "Ayurvedic Restful Sleep Formulation"
    )
    return passport

@router.get("/{passport_id}", response_model=InnovationPassport)
async def get_passport(passport_id: str):
    passport = PassportEngine.get_passport(passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")
    return passport

@router.put("/{passport_id}/update", response_model=InnovationPassport)
async def update_passport(passport_id: str, passport: InnovationPassport):
    existing = PassportEngine.get_passport(passport_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Passport not found")
    updated = PassportEngine.update_passport(passport)
    return updated

@router.get("/{passport_id}/clarifications", response_model=List[ClarificationQuery])
async def get_clarifications(passport_id: str):
    passport = PassportEngine.get_passport(passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")
    return PassportEngine.get_clarifications_for_passport(passport)

@router.post("/sanitize-document")
async def sanitize_document(req: DocumentSanitizeRequest):
    cleaned, threats = DocumentSanitizer.sanitize(req.document_text, req.filename or "upload.txt")
    return {
        "status": "success",
        "cleaned_text": cleaned,
        "threats_detected_and_neutralized": threats,
        "is_safe_for_reasoning": True
    }
