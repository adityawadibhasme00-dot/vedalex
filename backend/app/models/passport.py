import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FactOrigin(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    DOCUMENT_EXTRACTED = "document_extracted"
    INFERRED = "inferred"
    UNKNOWN = "unknown"

class FactItem(BaseModel):
    value: Any
    origin: FactOrigin = FactOrigin.USER_CONFIRMED
    source_evidence_id: str | None = None
    confidence: float = 1.0

class IngredientEntry(BaseModel):
    raw_name: str
    canonical_id: str | None = None
    botanical_name: str | None = None
    api_monograph_id: str | None = None
    plant_part: str = "Root"
    preparation_method: str = "Aqueous Extract"
    quantity_percentage: float = 50.0
    source_country: str = "India"
    origin_status: FactOrigin = FactOrigin.USER_CONFIRMED

class InnovationPassport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_title: str = "Ayurvedic Botanical Formulation"
    product_form: str = "Tablet"  # Tablet, Vati, Kwatha, Taila, Capsule, Powder, Syrup
    dosage_form: str = "500mg Twice Daily"
    intended_use: str = ""
    proposed_claims: list[str] = []
    claimed_innovation: str = ""
    process_description: str = "Standardized aqueous decoction (Kwatha) followed by spray drying into tablet form"
    ingredients: list[IngredientEntry] = Field(default_factory=list)
    manufacturing_location: str = "India"
    target_markets: list[str] = ["India", "United States", "Canada"]
    business_role: str = "Ayurveda MSME Manufacturer"
    biological_resource_origin: str = "Domestic Cultivated (India)"
    existing_ip_status: str = "None (Pre-filing)"
    version: int = 1
    unresolved_clarifications: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: "2026-09-06T19:00:00Z")
    updated_at: str = Field(default_factory=lambda: "2026-09-06T19:00:00Z")
    is_offline_draft: bool = False

class ClarificationQuery(BaseModel):
    id: str
    field_key: str
    question_text: dict[str, str]  # Multilingual: en, hi, mr, ta, etc.
    options: list[str]
    severity: str = "DECISION_CRITICAL"  # DECISION_CRITICAL | ADVISORY
