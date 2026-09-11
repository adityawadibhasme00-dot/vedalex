from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ─── Claim & Safety Intelligence ───────────────────────────────────────────
class ClaimSafetySignal(BaseModel):
    ingredient: str
    botanical_name: str
    signal: str
    severity: str = Field(description="HIGH | MEDIUM | LOW")
    evidence_source: str
    precaution: str


class MisleadingAdRisk(BaseModel):
    flagged_phrases: List[str] = Field(default_factory=list)
    act_citation: str
    action: str


class ClaimSafetyResult(BaseModel):
    claim_text: str
    claim_category: str = Field(description="curative | structure_function | wellness | traditional_use | cosmetic | safety | other")
    evidence_alignment: str = Field(description="supported | partial | unsupported | not_evaluated")
    risk_level: str = Field(description="HIGH_RISK | WARNING | SAFE")
    risk_color: str = Field(description="red | yellow | green")
    regulation: str
    suggested_alternative: Optional[str] = None
    note: str


class ClaimSafetyAnalysisResponse(BaseModel):
    passport_id: Optional[str] = None
    overall_verdict: str = Field(description="HIGH_RISK | WARNING | SAFE")
    overall_color: str
    claims: List[ClaimSafetyResult]
    safety_signals: List[ClaimSafetySignal] = Field(default_factory=list)
    misleading_ad_risk: MisleadingAdRisk
    regulatory_alerts: List[str] = Field(default_factory=list)
    summary: str
    disclaimer: str


# ─── Evidence & Quality Intelligence ───────────────────────────────────────
class EvidenceLadderCell(BaseModel):
    level: str = Field(description="traditional_use | preclinical | clinical | product_specific | safety")
    level_label: str
    support_status: str = Field(description="documented | partially_documented | insufficient")
    support_pct: int
    sources: List[str] = Field(default_factory=list)
    note: str
    gap_reason: Optional[str] = None


class QualityParameter(BaseModel):
    param_name: str
    spec: str
    test_method: str
    available: bool
    status: str = Field(description="available | missing")


class IngredientIntelligence(BaseModel):
    canonical_id: str
    botanical_name: str
    api_monograph_id: str
    evidence_ladder: List[EvidenceLadderCell] = Field(default_factory=list)
    evidence_support_pct: int
    evidence_gaps: List[str] = Field(default_factory=list)
    quality_parameters: List[QualityParameter] = Field(default_factory=list)
    quality_readiness_pct: int
    quality_gaps: List[str] = Field(default_factory=list)


class EvidenceQualityIntelligenceResponse(BaseModel):
    passport_id: str
    ingredients: List[IngredientIntelligence] = Field(default_factory=list)
    overall_evidence_support_pct: int
    overall_quality_readiness_pct: int
    recommended_actions: List[str] = Field(default_factory=list)
    disclaimer: str


# ─── Bio-Resource Intelligence ──────────────────────────────────────────────
class GeoOrigin(BaseModel):
    state: str
    status: str = Field(description="verified | supplier_confirmed | pending")
    note: str
    source: str


class BioResourcePlant(BaseModel):
    canonical_id: str
    botanical_name: str
    family: str = ""
    api_monograph_id: str = ""
    plant_parts: List[str] = Field(default_factory=list)
    ayurvedic_names: Dict[str, List[str]] = Field(default_factory=dict)
    regional_synonyms: Dict[str, List[str]] = Field(default_factory=dict)
    english_names: List[str] = Field(default_factory=list)
    geography: List[GeoOrigin] = Field(default_factory=list)
    conservation_status: str = ""
    trade_demand_class: str = ""
    price_trend_note: str = ""
    provenance_options: List[str] = Field(default_factory=list)
    abs_considerations: List[str] = Field(default_factory=list)
    tk_considerations: List[str] = Field(default_factory=list)
    ip_considerations: List[str] = Field(default_factory=list)
    evidence_support_pct: int = 0


class BioResourceGraphResponse(BaseModel):
    passport_id: str
    plants: List[BioResourcePlant] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    disclaimer: str


# ─── Ayurveda Aahara / Product Classifier ───────────────────────────────────
class PathwayScore(BaseModel):
    pathway: str
    score: int
    match_reasons: List[str] = Field(default_factory=list)


class ProductClassifierResponse(BaseModel):
    passport_id: Optional[str] = None
    product_form: str = ""
    dosage_form: str = ""
    intended_use: str = ""
    claims: List[str] = Field(default_factory=list)
    ingredients: List[str] = Field(default_factory=list)
    likely_pathway: str
    pathway_category: str = Field(description="ayurvedic_drug | proprietary_ayurveda | ayurveda_aahara | cosmetic | nutraceutical | unresolved")
    pathway_confidence: str = Field(description="HIGH | MEDIUM | LOW")
    reasons: List[str] = Field(default_factory=list)
    alternative_pathways: List[PathwayScore] = Field(default_factory=list)
    applicable_authority: str = ""
    applicable_sources: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    disclaimer: str


# ─── Export / Market Readiness ──────────────────────────────────────────────
class ExportGap(BaseModel):
    area: str
    requirement: str
    status: str = Field(description="satisfied | partial | missing")
    action: str
    source: str


class MarketReadinessItem(BaseModel):
    market: str
    flag: str = ""
    overall_status: str = Field(description="ready | partial | not_ready")
    readiness_pct: int
    prerequisites_satisfied: List[str] = Field(default_factory=list)
    gaps: List[ExportGap] = Field(default_factory=list)


class ExportReadinessResponse(BaseModel):
    passport_id: str
    origin_market: str = "India"
    markets: List[MarketReadinessItem] = Field(default_factory=list)
    recommended_first_market: str = ""
    summary: str = ""
    next_actions: List[str] = Field(default_factory=list)
    disclaimer: str


# ─── Terminology Mapper ─────────────────────────────────────────────────────
class TerminologyMapResponse(BaseModel):
    query: str
    matched: bool
    matched_via: str = Field(description="exact | synonym | fuzzy | none")
    canonical_id: Optional[str] = None
    botanical_name: Optional[str] = None
    api_monograph_id: Optional[str] = None
    family: Optional[str] = None
    classical_uses: List[str] = Field(default_factory=list)
    names: Dict[str, List[str]] = Field(default_factory=dict)
    transliterations: List[str] = Field(default_factory=list)
    nearest_possible: List[str] = Field(default_factory=list)
    rag_hint: str = ""
    source: str = ""