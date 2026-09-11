from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.services.copilot_orchestrator import AICopilotOrchestrator
from app.models.db_models import ChatHistory, User
from app.core.database import get_db
from app.auth.jwt_auth import get_current_user, get_optional_user
from sqlalchemy.orm import Session

router = APIRouter(prefix="/chat", tags=["AI Copilot"])

class ChatRequest(BaseModel):
    question: str
    passport_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    question: str
    charts: List[Dict[str, Any]] = []
    images: List[str] = []
    intent: Optional[Dict[str, str]] = None
    analysis_card: Optional[Dict[str, Any]] = None
    evidence_used: Optional[List[Dict[str, str]]] = None
    next_actions: Optional[List[str]] = None

@router.post("/query", response_model=ChatResponse)
async def chat_query(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    result = AICopilotOrchestrator.run(req.question, req.passport_id, req.context)

    if current_user:
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=req.question,
            response=result["answer"],
            sources=result["sources"],
            confidence=result["confidence"]
        )
        db.add(chat_entry)
        db.commit()

    return ChatResponse(**result)

SUGGESTED_QUESTIONS = [
    "Can I patent this Ayurvedic formulation?",
    "Is Neem already patented?",
    "Is my product label compliant?",
    "What evidence is missing for regulatory approval?",
    "What are the requirements for FSSAI Ayurveda Aahara?",
    "How do I comply with DSHEA in the US market?",
    "What is Section 3(p) and how does it affect my patent?",
    "Do I need NBA clearance for my formulation?",
]

@router.get("/suggested-questions")
async def get_suggested_questions():
    return {"questions": SUGGESTED_QUESTIONS}
