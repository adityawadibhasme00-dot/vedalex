from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid

class FactOrigin(str, Enum):
    USER_CONFIRMED = "user_confirmed"
    DOCUMENT_EXTRACTED = "document_extracted"
    INFERRED = "inferred"
    UNKNOWN = "unknown"

class FactItem(BaseModel):
    value: Any
    origin: FactOrigin = FactOrigin.USER_CONFIRMED
    source_evidence_id: Optional[str] = None
    confidence: float = 1.0

class IngredientEntry(BaseModel):
    raw_name: str
    canonical_id: Optional[str] = None
    botanical_name: Optional[str] = None
    api_monograph_id: Optional[str] = None
    plant_part: str = "Root"
    preparation_method: str = "Aqueous Extract"
    quantity_percentage: float = 50.0
    source_country: str = "India"
    origin_status: FactOrigin = FactOrigin.USER_CONFIRMED

class InnovationPassport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_title: str = "Ayurveda Sleep Formulation"
    product_form: str = "Tablet"  # Tablet, Vati, Kwatha, Taila, Capsule, Powder, Syrup
    dosage_form: str = "500mg Twice Daily"
    intended_use: str = "Supports restful sleep, stress reduction and mental calm"
    proposed_claims: List[str] = ["Supports healthy sleep", "Promotes natural relaxation"]
    claimed_innovation: str = "Synergistic botanical ratio enhancing adaptogenic calming response"
    process_description: str = "Standardized aqueous decoction (Kwatha) followed by spray drying into tablet form"
    ingredients: List[IngredientEntry] = Field(default_factory=list)
    manufacturing_location: str = "India"
    target_markets: List[str] = ["India", "United States", "Canada"]
    business_role: str = "Ayurveda MSME Manufacturer"
    biological_resource_origin: str = "Domestic Cultivated (India)"
    existing_ip_status: str = "None (Pre-filing)"
    version: int = 1
    unresolved_clarifications: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: "2026-09-06T19:00:00Z")
    updated_at: str = Field(default_factory=lambda: "2026-09-06T19:00:00Z")
    is_offline_draft: bool = False

class ClarificationQuery(BaseModel):
    id: str
    field_key: str
    question_text: Dict[str, str]  # Multilingual: en, hi, mr, ta, etc.
    options: List[str]
    severity: str = "DECISION_CRITICAL"  # DECISION_CRITICAL | ADVISORY
