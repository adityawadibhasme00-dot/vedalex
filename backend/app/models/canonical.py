
from pydantic import BaseModel, Field


class CanonicalIngredient(BaseModel):
    canonical_id: str = Field(description="Unique internal ID e.g. 'ING-ASHWAGANDHA-01'")
    api_monograph_id: str = Field(description="Ayurvedic Pharmacopoeia of India ID e.g. 'API-VOL1-008'")
    accepted_botanical_name: str = Field(description="Binomial e.g. 'Withania somnifera (L.) Dunal'")
    family: str = Field(description="e.g. 'Solanaceae'")
    sanskrit_names: list[str] = Field(default_factory=list)
    hindi_names: list[str] = Field(default_factory=list)
    marathi_names: list[str] = Field(default_factory=list)
    regional_synonyms: dict[str, list[str]] = Field(default_factory=dict, description="Tamil, Telugu, Kannada, Bengali, Gujarati, etc.")
    standard_plant_parts: list[str] = Field(default_factory=list)
    classical_therapeutic_uses: list[str] = Field(default_factory=list)
    fssai_aahara_status: str = Field(default="permitted", description="permitted | restricted | prohibited")
    us_fda_ndi_status: str = Field(default="old_dietary_ingredient", description="old_dietary_ingredient | ndi_notification_required | restricted")
    canada_nhpid_status: str = Field(default="monographed", description="monographed | schedule_1 | prohibited")
    resolution_confidence: float = 1.0

class FormulationFingerprint(BaseModel):
    fingerprint_hash: str
    canonical_ingredient_ids: list[str]
    ratios: dict[str, float]
    process_signature: str  # e.g. "aqueous_decoction_tablet"
