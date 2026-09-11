from fastapi import APIRouter
from app.models.institutional import InstitutionalDashboardData
from app.services.institutional_service import InstitutionalService

router = APIRouter(prefix="/institutional", tags=["Institutional Mode"])

@router.get("/cohort-analytics", response_model=InstitutionalDashboardData)
async def get_cohort_analytics():
    return InstitutionalService.get_dashboard_data()
