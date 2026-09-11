from fastapi import APIRouter
from typing import List, Dict, Any
from app.services.passport_engine import PassportEngine

router = APIRouter(prefix="/roadmap", tags=["Regulatory Roadmap"])

@router.get("/{passport_id}")
async def get_roadmap(passport_id: str):
    passport = PassportEngine.get_passport(passport_id)
    if not passport:
        passport = PassportEngine.create_from_intake("Ashwagandha + Brahmi")

    roadmap_phases = [
        {
            "phase": 1,
            "title": "Prior Art Search",
            "status": "completed",
            "description": "Search existing patents and traditional knowledge databases",
            "duration": "2-4 weeks",
            "requirements": ["Formulation details", "Innovation description"],
        },
        {
            "phase": 2,
            "title": "ABS Clearance (NBA)",
            "status": "pending",
            "description": "Access and Benefit Sharing clearance from National Biodiversity Authority",
            "duration": "4-8 weeks",
            "requirements": ["Biological resource origin details", "Supplier information"],
        },
        {
            "phase": 3,
            "title": "Patent Filing",
            "status": "pending",
            "description": "File patent application with Indian Patent Office / international offices",
            "duration": "12-24 months",
            "requirements": ["Complete specification", "Claims", "Drawings"],
        },
        {
            "phase": 4,
            "title": "Evidence Collection",
            "status": "in_progress",
            "description": "Collect stability, safety, and efficacy evidence",
            "duration": "3-6 months",
            "requirements": ["Stability data", "Safety data", "Clinical evidence"],
        },
        {
            "phase": 5,
            "title": "Compliance Submission",
            "status": "not_started",
            "description": "Submit to CDSCO/FSSAI/FDA for regulatory approval",
            "duration": "6-12 months",
            "requirements": ["Dossier", "GMP certificate", "All evidence"],
        },
        {
            "phase": 6,
            "title": "Market Launch",
            "status": "not_started",
            "description": "Commercial launch with compliant labeling and distribution",
            "duration": "1-3 months",
            "requirements": ["Regulatory approval", "Manufacturing setup", "Distribution channels"],
        },
    ]

    current_phase = 4
    estimated_completion = "2027 Q3"

    return {
        "passport_id": passport_id,
        "phases": roadmap_phases,
        "current_phase": current_phase,
        "total_phases": len(roadmap_phases),
        "estimated_completion": estimated_completion,
        "next_action": "Complete stability studies and safety data collection",
    }
