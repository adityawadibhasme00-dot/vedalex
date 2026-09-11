from fastapi import APIRouter
from app.api.v1.passport_router import router as passport_router
from app.api.v1.assessment_router import router as assessment_router
from app.api.v1.screening_router import router as screening_router
from app.api.v1.what_if_router import router as what_if_router
from app.api.v1.red_team_router import router as red_team_router
from app.api.v1.evidence_router import router as evidence_router
from app.api.v1.diff_router import router as diff_router
from app.api.v1.handoff_router import router as handoff_router
from app.api.v1.institutional_router import router as institutional_router
from app.api.v1.evals_router import router as evals_router
from app.api.v1.auth_router import router as auth_router
from app.api.v1.chat_router import router as chat_router
from app.api.v1.formulation_router import router as formulation_router
from app.api.v1.botanical_router import router as botanical_router
from app.api.v1.fto_router import router as fto_router
from app.api.v1.label_router import router as label_router
from app.api.v1.patent_router import router as patent_router
from app.api.v1.export_router import router as export_router
from app.api.v1.upload_router import router as upload_router
from app.api.v1.roadmap_router import router as roadmap_router
from app.api.v1.admin_router import router as admin_router
from app.api.v1.media_router import router as media_router
from app.api.v1.whitespace_router import router as whitespace_router
from app.api.v1.rag_router import router as rag_router
from app.api.v1.intelligence_router import router as intelligence_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(passport_router)
api_router.include_router(assessment_router)
api_router.include_router(screening_router)
api_router.include_router(what_if_router)
api_router.include_router(red_team_router)
api_router.include_router(evidence_router)
api_router.include_router(diff_router)
api_router.include_router(handoff_router)
api_router.include_router(institutional_router)
api_router.include_router(evals_router)
api_router.include_router(chat_router)
api_router.include_router(formulation_router)
api_router.include_router(botanical_router)
api_router.include_router(fto_router)
api_router.include_router(label_router)
api_router.include_router(patent_router)
api_router.include_router(export_router)
api_router.include_router(upload_router)
api_router.include_router(roadmap_router)
api_router.include_router(admin_router)
api_router.include_router(media_router)
api_router.include_router(whitespace_router)
api_router.include_router(rag_router)
api_router.include_router(intelligence_router)