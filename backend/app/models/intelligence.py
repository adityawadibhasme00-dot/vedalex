from typing import Optional

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
    flagged_phrases: list[str] = Field(default_factory=list)
    act_citation: str
    action: str


class ClaimSafetyResult(BaseModel):
    claim_text: str
    claim_category: str = Field(description="curative | structure_function | wellness | traditional_use | cosmetic | safety | other")
    evidence_alignment: str = Field(description="supported | partial | unsupported | not_evaluated")
    risk_level: str = Field(description="HIGH_RISK | WARNING | SAFE")
    risk_color: str = Field(description="red | yellow | green")
    regulation: str
    suggested_alternative: str | None = None
    note: str


class ClaimSafetyAnalysisResponse(BaseModel):
    passport_id: str | None = None
    overall_verdict: str = Field(description="HIGH_RISK | WARNING | SAFE")
    overall_color: str
    claims: list[ClaimSafetyResult]
    safety_signals: list[ClaimSafetySignal] = Field(default_factory=list)
    misleading_ad_risk: MisleadingAdRisk
    regulatory_alerts: list[str] = Field(default_factory=list)
    summary: str
    disclaimer: str


# ─── Evidence & Quality Intelligence ───────────────────────────────────────
class EvidenceLadderCell(BaseModel):
    level: str = Field(description="traditional_use | preclinical | clinical | product_specific | safety")
    level_label: str
    support_status: str = Field(description="documented | partially_documented | insufficient")
    support_pct: int
    sources: list[str] = Field(default_factory=list)
    note: str
    gap_reason: str | None = None


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
    evidence_ladder: list[EvidenceLadderCell] = Field(default_factory=list)
    evidence_support_pct: int
    evidence_gaps: list[str] = Field(default_factory=list)
    quality_parameters: list[QualityParameter] = Field(default_factory=list)
    quality_readiness_pct: int
    quality_gaps: list[str] = Field(default_factory=list)


class EvidenceQualityIntelligenceResponse(BaseModel):
    passport_id: str
    ingredients: list[IngredientIntelligence] = Field(default_factory=list)
    overall_evidence_support_pct: int
    overall_quality_readiness_pct: int
    recommended_actions: list[str] = Field(default_factory=list)
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
    plant_parts: list[str] = Field(default_factory=list)
    ayurvedic_names: dict[str, list[str]] = Field(default_factory=dict)
    regional_synonyms: dict[str, list[str]] = Field(default_factory=dict)
    english_names: list[str] = Field(default_factory=list)
    geography: list[GeoOrigin] = Field(default_factory=list)
    conservation_status: str = ""
    trade_demand_class: str = ""
    price_trend_note: str = ""
    provenance_options: list[str] = Field(default_factory=list)
    abs_considerations: list[str] = Field(default_factory=list)
    tk_considerations: list[str] = Field(default_factory=list)
    ip_considerations: list[str] = Field(default_factory=list)
    evidence_support_pct: int = 0
    cites: Optional["CITESSchedule"] = None


class CITESSchedule(BaseModel):
    latin_name: str
    synonyms: list[str] = Field(default_factory=list)
    ayurvedic_names: list[str] = Field(default_factory=list)
    appendix: str = ""
    annotation: str | None = None
    plant_parts: list[str] = Field(default_factory=list)
    impact: str = ""
    permit_requirement: str = ""
    india_controls: str = ""
    cultivation_note: str = ""


class BioResourceGraphResponse(BaseModel):
    passport_id: str
    plants: list[BioResourcePlant] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    disclaimer: str


# ─── Ayurveda Aahara / Product Classifier ───────────────────────────────────
class PathwayScore(BaseModel):
    pathway: str
    score: int
    match_reasons: list[str] = Field(default_factory=list)


class ClassifierEvidence(BaseModel):
    collection: str = Field(description="RAG domain collection the passage came from (regulations, patents, biodiversity, ...)")
    title: str = ""
    passage: str = ""
    source: str = Field(description="Official document / act title")
    authority: str = ""
    source_url: str = ""


class RuleValidationCheck(BaseModel):
    rule: str
    status: str = Field(description="SATISFIED | NOT_SATISFIED | INSUFFICIENT")
    verdict: str = Field(description="Compliant | Attention needed | Information required")
    reason: str
    source: str


class ProductClassifierResponse(BaseModel):
    passport_id: str | None = None
    product_name: str = ""
    product_form: str = ""
    dosage_form: str = ""
    intended_use: str = ""
    claims: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    intent_detected: str = Field(default="", description="Step 3 — detected product family (Classical / Patent & Proprietary / New Drug / Ayurveda Aahara / Cosmetic / Nutraceutical)")
    likely_pathway: str
    pathway_category: str = Field(description="classical_medicine | proprietary_ayurveda | new_drug | phytopharmaceutical | ayurveda_aahara | cosmetic | nutraceutical | unresolved")
    pathway_confidence: str = Field(description="HIGH | MEDIUM | LOW")
    reasons: list[str] = Field(default_factory=list)
    alternative_pathways: list[PathwayScore] = Field(default_factory=list)
    applicable_authority: str = ""
    applicable_sources: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence: list[ClassifierEvidence] = Field(default_factory=list, description="Step 4 — RAG retrieval of official database passages (India Code / AYUSH / IP India / NBA / FSSAI).")
    rule_validation: list[RuleValidationCheck] = Field(default_factory=list, description="Step 5 — deterministic 3-state validation of Section 3(p), ABS/NBA, AYUSH, FSSAI and labelling rules.")
    regulatory_pathway: str = Field(default="", description="Step 7 — concrete registration route for the winning category.")
    ip_readiness: str = Field(default="", description="Step 7 — IP position including Section 3(p) traditional-knowledge scrutiny.")
    abs_status: str = Field(default="", description="Step 7 — Access & Benefit Sharing (NBA) position.")
    risk_level: str = Field(default="MODERATE", description="Step 7 — LOW | MODERATE | HIGH")
    recommended_next_step: str = Field(default="", description="Step 7 — single most important next action.")
    disclaimer: str
    decision_path: list[str] = Field(default_factory=list, description="Human-readable trace of wizard answers fed into the rule engine.")
    classification_mode: str = Field(default="form_based", description="form_based | wizard_based")
    abs_assessment: Optional["ABSComplianceResponse"] = None


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
    prerequisites_satisfied: list[str] = Field(default_factory=list)
    gaps: list[ExportGap] = Field(default_factory=list)


class ExportReadinessResponse(BaseModel):
    passport_id: str
    origin_market: str = "India"
    markets: list[MarketReadinessItem] = Field(default_factory=list)
    recommended_first_market: str = ""
    summary: str = ""
    next_actions: list[str] = Field(default_factory=list)
    disclaimer: str


# ─── Dynamic Bio-Resource Knowledge Graph ───────────────────────────────────
class KnowledgeGraphNode(BaseModel):
    id: str
    label: str
    category: str = Field(description="ingredient | botanical | monograph | regulation | authority | jurisdiction | tkdl | patent | paper | safety | supplier | source")
    x: int = 0
    y: int = 0
    details: str = ""
    sourceAuthority: str = ""
    collection: str = ""
    sourceUrl: str = ""


class KnowledgeGraphEdge(BaseModel):
    model_config = {"populate_by_name": True}

    from_: str = Field(..., alias="from")
    to: str
    label: str
    color: str = "#10b981"


class InnovationGraphIngredient(BaseModel):
    raw_name: str
    canonical_id: str = ""
    botanical_name: str = ""
    api_monograph_id: str = ""
    monographed: bool = False


class SelectedInnovationInfo(BaseModel):
    title: str
    kind: str = Field(description="Single Herb | Polyherbal Formulation")
    ingredients: list[InnovationGraphIngredient] = Field(default_factory=list)


class InnovationKnowledgeGraphResponse(BaseModel):
    selected_innovation: SelectedInnovationInfo
    nodes: list[KnowledgeGraphNode] = Field(default_factory=list)
    edges: list[KnowledgeGraphEdge] = Field(default_factory=list)
    collections_used: list[str] = Field(default_factory=list)
    evidence_found: bool = True
    evidence_note: str = ""
    disclaimer: str = ""


# ─── ABS / NBA Compliance ───────────────────────────────────────────────────
class ABSObligation(BaseModel):
    obligation: str
    status: str = Field(description="required | applicable | exempt | not_applicable | info_required")
    citation: str = ""
    note: str = ""


class ABSBenefitSharing(BaseModel):
    applicable: bool = False
    slab: str = Field(default="", description="Turnover slab the rate applies to, e.g. '<= 5 crore'")
    rate_pct: float = 0.0
    amount_inr: float | None = None
    basis: str = Field(default="", description="Basis of calculation, e.g. '0.2% of total turnover'")
    citation: str = ""


class ABSComplianceResponse(BaseModel):
    status: str = Field(description="exempt | compliance_required | info_required | not_applicable")
    user_type: str = ""
    turnover_inr: float | None = None
    codified_tk: bool | None = None
    wild_collected: bool | None = None
    commercial_use: bool = True
    exemption_reason: str = ""
    benefit_sharing: ABSBenefitSharing
    obligations: list[ABSObligation] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    decision_path: list[str] = Field(default_factory=list)
    disclaimer: str = ""


# ─── Terminology Mapper ─────────────────────────────────────────────────────
class TerminologyMapResponse(BaseModel):
    query: str
    matched: bool
    matched_via: str = Field(description="exact | synonym | fuzzy | none")
    canonical_id: str | None = None
    botanical_name: str | None = None
    api_monograph_id: str | None = None
    family: str | None = None
    classical_uses: list[str] = Field(default_factory=list)
    names: dict[str, list[str]] = Field(default_factory=dict)
    transliterations: list[str] = Field(default_factory=list)
    nearest_possible: list[str] = Field(default_factory=list)
    rag_hint: str = ""
    source: str = ""