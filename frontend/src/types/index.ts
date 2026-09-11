export type FactOrigin = 'user_confirmed' | 'document_extracted' | 'inferred' | 'unknown';

export interface IngredientEntry {
  raw_name: string;
  canonical_id?: string;
  botanical_name?: string;
  api_monograph_id?: string;
  plant_part: string;
  preparation_method: string;
  quantity_percentage: number;
  source_country?: string;
  origin_status: FactOrigin;
}

export interface InnovationPassport {
  id: string;
  case_title: string;
  product_form: string;
  dosage_form: string;
  intended_use: string;
  proposed_claims: string[];
  claimed_innovation: string;
  process_description: string;
  ingredients: IngredientEntry[];
  manufacturing_location: string;
  target_markets: string[];
  business_role: string;
  biological_resource_origin: string;
  existing_ip_status: string;
  version: number;
  unresolved_clarifications: string[];
  created_at: string;
  updated_at: string;
  is_offline_draft?: boolean;
}

export interface StatutoryCitation {
  act_title: string;
  section_reference: string;
  authority: string;
  effective_date: string;
  exact_passage: string;
  source_url?: string;
  authority_rank: number;
}

export interface RegulatoryFinding {
  jurisdiction: string;
  pathway_category: string;
  status: 'condition_satisfied' | 'condition_not_satisfied' | 'insufficient_information';
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_EVIDENCE';
  conditions_evaluated: string[];
  supporting_citations: StatutoryCitation[];
  missing_facts: string[];
  next_action_steps: string[];
  coverage_limitations: string;
  assumptions_made: string[];
  explanation_text?: string;
}

export interface AssessmentResponse {
  assessment_id: string;
  passport_id: string;
  timestamp: string;
  language: string;
  findings: RegulatoryFinding[];
  coverage_meter_score: number;
  unsupported_claim_rate: number;
}

export interface ClarificationQuery {
  id: string;
  field_key: string;
  question_text: Record<string, string>;
  options: string[];
  severity: string;
}

export interface WhatIfDiffItem {
  jurisdiction: string;
  prior_classification: string;
  new_classification: string;
  impact_severity: string;
  risk_alert: string;
  removed_requirements: string[];
  new_requirements: string[];
  new_citations: StatutoryCitation[];
}

export interface WhatIfSimulationResponse {
  original_claims: string[];
  mutated_claims: string[];
  affected_nodes_count: number;
  diffs: WhatIfDiffItem[];
}

export interface EvidenceItem {
  id: string;
  passport_id: string;
  requirement_name: string;
  why_it_applies: string;
  expected_evidence_type: string;
  status: 'Missing' | 'Uploaded' | 'Needs review' | 'Accepted for this assessment';
  supplied_filename?: string;
  prerequisites: string[];
  next_action: string;
  jurisdiction: string;
}

export interface EvidenceGapSummary {
  passport_id: string;
  total_checks: number;
  evaluated_checks: number;
  blocked_by_missing_sources: number;
  coverage_meter_percentage: number;
  items: EvidenceItem[];
}

export interface RegulatoryDiffRecord {
  id: string;
  source_authority: string;
  act_title: string;
  prior_version_date: string;
  new_version_date: string;
  summary_of_change: string;
  affected_provisions: string[];
  affected_case_ids: string[];
  severity: string;
}

export interface RedTeamObjection {
  objection_id: string;
  authority_simulated: string;
  legal_basis: string;
  objection_title: string;
  summary: string;
  investigable_action: string;
}

export interface RedTeamResult {
  passport_id: string;
  disclaimer: string;
  total_objections: number;
  objections: RedTeamObjection[];
}

export interface ProvenanceNode {
  id: string;
  type: string;
  label: string;
  status?: string;
  details?: string;
  jurisdiction?: string;
  condition_state?: string;
  authority?: string;
  effective_date?: string;
  passage_excerpt?: string;
  confidence?: string;
}

export interface ProvenanceEdge {
  source: string;
  target: string;
  relation: string;
}

export interface ProvenanceGraphData {
  passport_id: string;
  jurisdiction: string;
  nodes: ProvenanceNode[];
  edges: ProvenanceEdge[];
  verifiable_paper_trail: boolean;
}

// ─── AI Copilot ─────────────────────────────────────────────────────────────────
export interface CopilotSource {
  content: string;
  source: string;
  category: string;
}

export interface CopilotChartPhase {
  label: string;
  status: 'completed' | 'current' | 'pending';
  desc: string;
  duration: string;
}

export interface CopilotChartState {
  code: string;
  state: string;
  ingredient: string;
  status: string;
  x_norm: number;
  y_norm: number;
  note: string;
}

export interface CopilotChartCell {
  herb: string;
  form: string;
  value: string;
  color: string;
  rationale: string;
}

export interface CopilotChart {
  type: string;
  title: string;
  labels: string[];
  values: number[];
  description?: string;
  insights?: string[];
  subtitle?: string;
  phases?: CopilotChartPhase[];
  current?: string | null;
  current_label?: string;
  states?: CopilotChartState[];
  herbs?: string[];
  forms?: string[];
  cells?: CopilotChartCell[];
  colors?: Record<string, string>;
}

export interface CopilotAnalysisCard {
  confidence_pct: number;
  patent_readiness: number | null;
  risk_level: string;
  verification_badge: string;
  executive_summary: string;
}

export interface CopilotResponse {
  answer: string;
  sources: CopilotSource[];
  confidence: number;
  question: string;
  charts?: CopilotChart[];
  images?: string[];
  intent?: { id: string; label: string };
  analysis_card?: CopilotAnalysisCard;
  evidence_used?: { name: string; type: string }[];
  next_actions?: string[];
}

// ─── Patent Analysis ────────────────────────────────────────────────────────────
export interface SimilarPatent {
  patent_id: string;
  title: string;
  similarity: number;
  jurisdiction: string;
}

export interface ReadinessComponent {
  code: 'novelty' | 'prior_art' | 'section3p' | 'disclosure' | 'evidence' | 'ownership' | 'fto' | 'documentation';
  label: string;
  earned: number;
  max: number;
  pct: number;
  status: 'good' | 'warn' | 'risk';
  overlap_pct?: number;
  risk?: string;
  evidence_count?: number;
  claim_count?: number;
}

export interface PatentReadiness {
  passport_id: string;
  novelty_score: number;
  inventive_step_score: number;
  overall_readiness: number;
  overall_pct: number;
  patent_ready: boolean;
  components: ReadinessComponent[];
  similar_patents: SimilarPatent[];
  prior_art_overlap: number;
  section3p_risk: string;
  disclosure_risk: string;
  fto_overlap: number;
  strengths: string[];
  weaknesses: string[];
  next_actions: string[];
  missing_evidence: string[];
  recommendations: string[];
}

// ─── FTO Check ──────────────────────────────────────────────────────────────────
export interface FTOPatent {
  patent_id: string;
  title: string;
  jurisdiction: string;
  overlap_percentage: number;
  risk_level: string;
  description: string;
}

export interface FTOResult {
  passport_id: string;
  similar_patents: FTOPatent[];
  overall_risk: string;
  recommendation: string;
}

// ─── Claim Firewall / Label Analysis ────────────────────────────────────────────
export interface ClaimResult {
  claim_text: string;
  risk_level: string;
  risk_color: string;
  regulation: string;
  note: string;
}

export interface LabelAnalysisResponse {
  overall_status: string;
  overall_color: string;
  claims: ClaimResult[];
  summary: string;
}

// ─── Claim & Safety Intelligence ─────────────────────────────────────────────
export interface ClaimSafetySignal {
  ingredient: string;
  botanical_name: string;
  signal: string;
  severity: string;
  evidence_source: string;
  precaution: string;
}

export interface MisleadingAdRisk {
  flagged_phrases: string[];
  act_citation: string;
  action: string;
}

export interface ClaimSafetyResultItem {
  claim_text: string;
  claim_category: string;
  evidence_alignment: string;
  risk_level: string;
  risk_color: string;
  regulation: string;
  suggested_alternative?: string;
  note: string;
}

export interface ClaimSafetyAnalysisResponse {
  passport_id?: string;
  overall_verdict: string;
  overall_color: string;
  claims: ClaimSafetyResultItem[];
  safety_signals: ClaimSafetySignal[];
  misleading_ad_risk: MisleadingAdRisk;
  regulatory_alerts: string[];
  summary: string;
  disclaimer: string;
}

// ─── Evidence & Quality Intelligence ─────────────────────────────────────────
export interface EvidenceLadderCell {
  level: string;
  level_label: string;
  support_status: string;
  support_pct: number;
  sources: string[];
  note: string;
  gap_reason?: string;
}

export interface QualityParameter {
  param_name: string;
  spec: string;
  test_method: string;
  available: boolean;
  status: string;
}

export interface IngredientIntelligence {
  canonical_id: string;
  botanical_name: string;
  api_monograph_id: string;
  evidence_ladder: EvidenceLadderCell[];
  evidence_support_pct: number;
  evidence_gaps: string[];
  quality_parameters: QualityParameter[];
  quality_readiness_pct: number;
  quality_gaps: string[];
}

export interface EvidenceQualityIntelligenceResponse {
  passport_id: string;
  ingredients: IngredientIntelligence[];
  overall_evidence_support_pct: number;
  overall_quality_readiness_pct: number;
  recommended_actions: string[];
  disclaimer: string;
}

// ─── Regulatory Roadmap ─────────────────────────────────────────────────────────
export interface RoadmapPhase {
  phase: number;
  title: string;
  status: string;
  description: string;
  duration: string;
  requirements: string[];
}

export interface RoadmapData {
  passport_id: string;
  phases: RoadmapPhase[];
  current_phase: number;
  total_phases: number;
  estimated_completion: string;
  next_action: string;
}

// ─── Formulation Parsing ────────────────────────────────────────────────────────
export interface ParsedIngredient {
  raw_name: string;
  detected_language: string;
  canonical_id?: string;
  botanical_name?: string;
  api_monograph_id?: string;
  family?: string;
  plant_part?: string;
  confidence: number;
}

export interface FormulationParseResponse {
  detected_language: string;
  ingredients: ParsedIngredient[];
  raw_text: string;
}

// ─── RAG Pipeline (Production) ────────────────────────────────────────────────
export interface RAGGrounding {
  grounded: boolean;
  coverage_ratio: number;
  meaningful_tokens: number;
  covered_tokens: number;
  uncovered_tokens: string[];
  source_count: number;
  recommendation: string;
}

export interface RAGHallucinationCheck {
  risk_level: 'none' | 'low' | 'medium' | 'high' | 'critical';
  grounded: boolean;
  coverage_ratio: number;
  citation_count: number;
  violations: string[];
  recommendations: string[];
}

export interface RAGRetrievalStats {
  semantic_results: number;
  bm25_results: number;
  statutory_results: number;
  merged_count: number;
  final_count: number;
  semantic_time_ms: number;
  bm25_time_ms: number;
  statutory_time_ms: number;
  rerank_time_ms: number;
  total_time_ms: number;
  embedding_provider: string;
  reranker_available: boolean;
  qdrant_available: boolean;
}

export interface RAGSource {
  content: string;
  source: string;
  category: string;
  doc_id: string;
  title: string;
  authority: string;
  jurisdiction: string;
  authority_level: number;
  section_heading: string;
  patent_number: string;
  publication_year: number;
  source_url: string;
  effective_date: string;
  score: number;
  combined_score: number;
  rerank_score: number;
  retrieval_method: 'semantic' | 'keyword' | 'statutory' | 'hybrid';
  keyword_boost: number;
}

export interface RAGAskResponse {
  answer: string;
  sources: RAGSource[];
  confidence: number;
  grounding: RAGGrounding;
  hallucination_check: RAGHallucinationCheck;
  retrieval_stats: RAGRetrievalStats;
  intent: { id: string; label: string };
  charts: CopilotChart[];
  llm_prompt: { system: string; user: string } | null;
  verification_badge: string;
  next_actions: string[];
}

export interface RAGPatentSearchResponse {
  results: RAGSource[];
  total_found: number;
  query: string;
  filters_applied: Record<string, any>;
  retrieval_stats: RAGRetrievalStats;
}

export interface RAGInnovationPassportResponse {
  passport_id: string;
  formulation_name: string;
  ingredients: { name: string; botanical: string }[];
  prior_art_analysis: { sources: RAGSource[]; overlap_count: number; confidence: number };
  tkdl_overlap: { sources: RAGSource[]; overlap_found: boolean; confidence: number };
  section_3p_assessment: { risk: string; score: number };
  patent_readiness: PatentReadiness | null;
  regulatory_requirements: { sources: RAGSource[]; confidence: number };
  evidence_gaps: string[];
  confidence: number;
  sources: RAGSource[];
}

export interface RAGPipelineStatus {
  qdrant: {
    status: string;
    collection: string;
    total_points: number;
    vectors_size: number;
    config: { dim: number; distance: string };
  };
  bm25: { available: boolean; index_size: number };
  embedding: { provider: string; dim: number };
  reranker: { available: boolean };
}

// ─── Bio-Resource Intelligence ─────────────────────────────────────────────
export interface GeoOrigin {
  state: string;
  status: 'verified' | 'supplier_confirmed' | 'pending';
  note: string;
  source: string;
}

export interface BioResourcePlant {
  canonical_id: string;
  botanical_name: string;
  family: string;
  api_monograph_id: string;
  plant_parts: string[];
  ayurvedic_names: Record<string, string[]>;
  regional_synonyms: Record<string, string[]>;
  english_names: string[];
  geography: GeoOrigin[];
  conservation_status: string;
  trade_demand_class: string;
  price_trend_note: string;
  provenance_options: string[];
  abs_considerations: string[];
  tk_considerations: string[];
  ip_considerations: string[];
  evidence_support_pct: number;
}

export interface BioResourceGraphResponse {
  passport_id: string;
  plants: BioResourcePlant[];
  recommendations: string[];
  disclaimer: string;
}

// ─── Product Classifier ─────────────────────────────────────────────────────
export interface PathwayScore {
  pathway: string;
  score: number;
  match_reasons: string[];
}

export interface ProductClassifierResponse {
  passport_id?: string;
  product_form: string;
  dosage_form: string;
  intended_use: string;
  claims: string[];
  ingredients: string[];
  likely_pathway: string;
  pathway_category: string;
  pathway_confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  reasons: string[];
  alternative_pathways: PathwayScore[];
  applicable_authority: string;
  applicable_sources: string[];
  next_actions: string[];
  disclaimer: string;
}

// ─── Export / Market Readiness ──────────────────────────────────────────────
export interface ExportGap {
  area: string;
  requirement: string;
  status: 'satisfied' | 'partial' | 'missing';
  action: string;
  source: string;
}

export interface MarketReadinessItem {
  market: string;
  flag: string;
  overall_status: 'ready' | 'partial' | 'not_ready';
  readiness_pct: number;
  prerequisites_satisfied: string[];
  gaps: ExportGap[];
}

export interface ExportReadinessResponse {
  passport_id: string;
  origin_market: string;
  markets: MarketReadinessItem[];
  recommended_first_market: string;
  summary: string;
  next_actions: string[];
  disclaimer: string;
}

// ─── Terminology Mapper ─────────────────────────────────────────────────────
export interface TerminologyMapResponse {
  query: string;
  matched: boolean;
  matched_via: 'exact' | 'synonym' | 'fuzzy' | 'none';
  canonical_id?: string;
  botanical_name?: string;
  api_monograph_id?: string;
  family?: string;
  classical_uses: string[];
  names: Record<string, string[]>;
  transliterations: string[];
  nearest_possible: string[];
  rag_hint: string;
  source: string;
}
