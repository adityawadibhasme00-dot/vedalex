from pydantic import BaseModel, Field
from typing import List, Optional

class ExpertHandoffRequest(BaseModel):
    passport_id: str
    expert_type: str = "Registered Patent Agent"  # "Registered Patent Agent" | "AYUSH Regulatory Consultant"
    user_name: str
    user_email: str
    user_phone: Optional[str] = None
    explicit_dpdp_consent: bool = True
    liability_boundary_acknowledged: bool = True
    notes: Optional[str] = None

class ExpertHandoffResponse(BaseModel):
    ticket_id: str
    passport_id: str
    status: str = "QUEUED_FOR_EXPERT_DISPATCH"
    assigned_facilitation_center: str = "TIFAC / AYUSH IP Cell New Delhi"
    sla_response_hours: int = 48
    dossier_download_url: str
    consent_audit_hash: str
    message: str
