import {
  InnovationPassport,
  AssessmentResponse,
  ClarificationQuery,
  WhatIfSimulationResponse,
  RedTeamResult,
  EvidenceGapSummary,
  RegulatoryDiffRecord,
  ProvenanceGraphData,
  EvidenceItem,
  ClaimSafetyAnalysisResponse,
  EvidenceQualityIntelligenceResponse,
  BioResourceGraphResponse,
  InnovationKnowledgeGraphResponse,
  ProductClassifierResponse,
  ExportReadinessResponse,
  TerminologyMapResponse,
  WhiteSpaceMutation,
  WhiteSpaceResponse,
  ABSComplianceResponse,
} from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1';

export interface PassportIntakeExtras {
  product_type?: string;
  category?: string;
  target_markets?: string[];
  extraction_method?: string;
  solvent?: string;
  temperature?: string;
  time?: string;
  processing_steps?: string;
  proposed_claims?: string[];
}

export async function createPassportFromIntake(
  rawText: string,
  userLang: string = 'en',
  title?: string,
  extras?: Partial<PassportIntakeExtras>
): Promise<InnovationPassport> {
  const res = await fetch(`${API_BASE_URL}/passport/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      raw_text: rawText,
      user_lang: userLang,
      case_title: title,
      product_type: extras?.product_type,
      category: extras?.category,
      target_markets: extras?.target_markets,
      extraction_method: extras?.extraction_method,
      solvent: extras?.solvent,
      temperature: extras?.temperature,
      time: extras?.time,
      processing_steps: extras?.processing_steps,
      proposed_claims: extras?.proposed_claims
    })
  });
  if (!res.ok) throw new Error('Failed to create passport');
  return res.json();
}

export async function getPassport(passportId: string): Promise<InnovationPassport> {
  const res = await fetch(`${API_BASE_URL}/passport/${passportId}`);
  if (!res.ok) throw new Error('Failed to fetch passport');
  return res.json();
}

export async function getClarifications(passportId: string): Promise<ClarificationQuery[]> {
  const res = await fetch(`${API_BASE_URL}/passport/${passportId}/clarifications`);
  if (!res.ok) return [];
  return res.json();
}

export async function evaluateAssessment(
  passportId: string,
  targetMarkets: string[] = ['India', 'United States', 'Canada'],
  language: string = 'en'
): Promise<AssessmentResponse> {
  const res = await fetch(`${API_BASE_URL}/assessment/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      passport_id: passportId,
      target_markets: targetMarkets,
      language: language
    })
  });
  if (!res.ok) throw new Error('Failed to evaluate assessment');
  return res.json();
}

export async function getProvenanceGraph(
  passportId: string,
  jurisdiction: string = 'India'
): Promise<ProvenanceGraphData> {
  const res = await fetch(`${API_BASE_URL}/assessment/${passportId}/provenance?jurisdiction=${encodeURIComponent(jurisdiction)}`);
  if (!res.ok) throw new Error('Failed to fetch provenance graph');
  return res.json();
}

export async function simulateWhatIf(
  passportId: string,
  mutatedClaims: string[]
): Promise<WhatIfSimulationResponse> {
  const res = await fetch(`${API_BASE_URL}/what-if/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      passport_id: passportId,
      mutated_claims: mutatedClaims
    })
  });
  if (!res.ok) throw new Error('Failed to run what-if simulation');
  return res.json();
}

export async function challengeInnovation(passportId: string): Promise<RedTeamResult> {
  const res = await fetch(`${API_BASE_URL}/red-team/challenge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ passport_id: passportId })
  });
  if (!res.ok) throw new Error('Failed to challenge innovation');
  return res.json();
}

export async function getEvidenceGaps(passportId: string): Promise<EvidenceGapSummary> {
  const res = await fetch(`${API_BASE_URL}/evidence/${passportId}`);
  if (!res.ok) throw new Error('Failed to fetch evidence gaps');
  return res.json();
}

export async function updateEvidenceLifecycle(
  itemId: string,
  status: string,
  suppliedFilename?: string
): Promise<EvidenceItem> {
  const res = await fetch(`${API_BASE_URL}/evidence/item/${itemId}/lifecycle`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      status: status,
      supplied_filename: suppliedFilename
    })
  });
  if (!res.ok) throw new Error('Failed to update evidence lifecycle');
  return res.json();
}

export async function getRegulatoryDiffs(): Promise<RegulatoryDiffRecord[]> {
  const res = await fetch(`${API_BASE_URL}/regulatory-diff/updates`);
  if (!res.ok) return [];
  return res.json();
}

export async function dispatchExpertHandoff(payload: {
  passport_id: string;
  expert_type: string;
  user_name: string;
  user_email: string;
  user_phone?: string;
  explicit_dpdp_consent: boolean;
  liability_boundary_acknowledged: boolean;
}) {
  const res = await fetch(`${API_BASE_URL}/expert-handoff/dispatch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to dispatch expert handoff');
  return res.json();
}

export async function sanitizeDocument(text: string, filename: string) {
  const res = await fetch(`${API_BASE_URL}/passport/sanitize-document`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_text: text, filename })
  });
  if (!res.ok) throw new Error('Sanitization failed');
  return res.json();
}

export async function getInstitutionalAnalytics() {
  const res = await fetch(`${API_BASE_URL}/institutional/cohort-analytics`);
  if (!res.ok) throw new Error('Failed to fetch institutional data');
  return res.json();
}

export async function runBenchmarkEvals() {
  const res = await fetch(`${API_BASE_URL}/evals/run-benchmark`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run benchmark');
  return res.json();
}

// ─── Authentication ──────────────────────────────────────────────
export async function loginUser(email: string, password: string) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }
  return res.json();
}

export async function signupUser(name: string, email: string, password: string, role?: string, institution?: string) {
  const res = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password, role, institution })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Signup failed');
  }
  return res.json();
}

// ─── AI Copilot ──────────────────────────────────────────────────
export async function askCopilot(question: string, passportId?: string, context?: any) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45000);
  try {
    const res = await fetch(`${API_BASE_URL}/chat/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, passport_id: passportId, context }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error('Failed to query AI Copilot');
    return res.json();
  } finally {
    clearTimeout(timer);
  }
}

export async function getSuggestedQuestions() {
  const res = await fetch(`${API_BASE_URL}/chat/suggested-questions`);
  if (!res.ok) return { questions: [] };
  return res.json();
}

// ─── Formulation Parsing ─────────────────────────────────────────
export async function parseFormulation(text: string, language?: string) {
  const res = await fetch(`${API_BASE_URL}/formulation/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language: language || 'auto' })
  });
  if (!res.ok) throw new Error('Failed to parse formulation');
  return res.json();
}

export async function canonicalizeBotanical(rawName: string) {
  const res = await fetch(`${API_BASE_URL}/botanical/canonicalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_name: rawName, source_language: 'auto' })
  });
  if (!res.ok) throw new Error('Failed to canonicalize');
  return res.json();
}

// ─── Patent Analysis ─────────────────────────────────────────────
export async function getPatentReadiness(passportId: string) {
  const res = await fetch(`${API_BASE_URL}/analysis/readiness/${passportId}`);
  if (!res.ok) throw new Error('Failed to get patent readiness');
  return res.json();
}

// ─── FTO Check ───────────────────────────────────────────────────
export async function checkFTO(passportId: string, targetMarkets?: string[]) {
  const res = await fetch(`${API_BASE_URL}/fto/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ passport_id: passportId, target_markets: targetMarkets || [] })
  });
  if (!res.ok) throw new Error('Failed FTO check');
  return res.json();
}

// ─── Label / Claim Firewall ──────────────────────────────────────
export async function analyzeLabel(labelText: string, productType?: string) {
  const res = await fetch(`${API_BASE_URL}/label/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label_text: labelText, product_type: productType || 'ayurvedic_drug' })
  });
  if (!res.ok) throw new Error('Failed to analyze label');
  return res.json();
}

// ─── Claim & Safety Intelligence ─────────────────────────────────
export async function analyzeClaimSafety(payload: {
  claims?: string[];
  ingredients?: string[];
  product_type?: string;
  target_markets?: string[];
  passport_id?: string;
}): Promise<ClaimSafetyAnalysisResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/claim-safety/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      claims: payload.claims,
      ingredients: payload.ingredients,
      product_type: payload.product_type || 'ayurvedic_drug',
      target_markets: payload.target_markets || ['India', 'United States', 'Canada'],
      passport_id: payload.passport_id
    })
  });
  if (!res.ok) throw new Error('Failed to analyze claim safety');
  return res.json();
}

export async function getEvidenceQualityIntelligence(passportId: string): Promise<EvidenceQualityIntelligenceResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/evidence-quality/${passportId}`);
  if (!res.ok) throw new Error('Failed to fetch evidence & quality intelligence');
  return res.json();
}

export async function getBioResourceIntelligence(passportId: string): Promise<BioResourceGraphResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/bio-resource/${passportId}`);
  if (!res.ok) throw new Error('Failed to fetch bio-resource intelligence');
  return res.json();
}

export async function getInnovationGraph(payload: {
  ingredients: string[];
  innovation_title?: string;
  passport_id?: string;
}): Promise<InnovationKnowledgeGraphResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/knowledge-graph`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to fetch innovation knowledge graph');
  return res.json();
}

export async function getPassportInnovationGraph(passportId: string): Promise<InnovationKnowledgeGraphResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/knowledge-graph/${passportId}`);
  if (!res.ok) throw new Error('Failed to fetch passport knowledge graph');
  return res.json();
}

export async function classifyProduct(payload: {
  passport_id?: string;
  product_name?: string;
  product_form?: string;
  dosage_form?: string;
  intended_use?: string;
  claims?: string[];
  ingredients?: string[];
  process_description?: string;
  label_disclaimer?: string;
  first_schedule?: boolean;
  new_ingredient?: boolean;
  extraction_method?: string;
  novel_process?: boolean;
  declared_use?: string;
  ab_user_type?: string;
  ab_turnover_inr?: number;
  ab_wild_collected?: boolean;
  ab_commercial_use?: boolean;
}): Promise<ProductClassifierResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/product-classify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to classify product');
  return res.json();
}

export async function checkABS(payload: {
  ingredients?: string[];
  passport_id?: string;
  user_type?: string;
  turnover_inr?: number;
  codified_tk?: boolean;
  wild_collected?: boolean;
  commercial_use?: boolean;
}): Promise<ABSComplianceResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/abs/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to check ABS compliance');
  return res.json();
}

export async function getExportReadiness(passportId: string): Promise<ExportReadinessResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/export-readiness/${passportId}`);
  if (!res.ok) throw new Error('Failed to fetch export readiness');
  return res.json();
}

export async function mapTerminology(query: string): Promise<TerminologyMapResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/terminology/map`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  if (!res.ok) throw new Error('Failed to map terminology');
  return res.json();
}

// ─── White Space Navigator ───────────────────────────────────────
export async function getWhiteSpaceAnalysis(passportId: string): Promise<WhiteSpaceResponse> {
  const res = await fetch(`${API_BASE_URL}/whitespace/${encodeURIComponent(passportId)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail || 'Failed to fetch white space analysis');
  }
  return res.json();
}

export async function analyzeWhiteSpace(
  passportId: string,
  mutate?: WhiteSpaceMutation
): Promise<WhiteSpaceResponse | { before: WhiteSpaceResponse; after: WhiteSpaceResponse; mutated: true }> {
  const res = await fetch(`${API_BASE_URL}/whitespace/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ passport_id: passportId, mutate: mutate || null })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail || 'Failed to run white space analysis');
  }
  return res.json();
}

// ─── Regulatory Roadmap ──────────────────────────────────────────
export async function getRoadmap(passportId: string) {
  const res = await fetch(`${API_BASE_URL}/roadmap/${passportId}`);
  if (!res.ok) throw new Error('Failed to get roadmap');
  return res.json();
}

// ─── Dossier Export ──────────────────────────────────────────────
export async function exportDossier(passportId: string, format?: string) {
  const res = await fetch(`${API_BASE_URL}/export/dossier`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ passport_id: passportId, format: format || 'pdf' })
  });
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = body?.detail || body?.message || '';
    } catch { /* ignore */ }
    throw new Error(detail || 'Failed to export dossier');
  }
  return res.json();
}

// ─── File Upload ─────────────────────────────────────────────────
export async function uploadDisclosureCheck(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE_URL}/upload/disclosure-check`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) throw new Error('Upload failed');
  return res.json();
}

// ─── RAG Pipeline (Production) ────────────────────────────────────
export async function ragAsk(
  query: string,
  options?: {
    filters?: Record<string, any>;
    jurisdiction?: string;
    category?: string;
    top_k?: number;
    include_prompt?: boolean;
    passport_id?: string;
  }
) {
  const res = await fetch(`${API_BASE_URL}/rag/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, ...options })
  });
  if (!res.ok) throw new Error('RAG query failed');
  return res.json();
}

export async function searchPatents(
  query: string,
  options?: {
    patent_number?: string;
    jurisdiction?: string;
    publication_year?: number;
    section?: string;
    top_k?: number;
  }
) {
  const res = await fetch(`${API_BASE_URL}/rag/search-patent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, ...options })
  });
  if (!res.ok) throw new Error('Patent search failed');
  return res.json();
}

export async function getRAGInnovationPassport(passportId: string) {
  const res = await fetch(`${API_BASE_URL}/rag/innovation-passport/${passportId}`);
  if (!res.ok) throw new Error('Failed to fetch RAG innovation passport');
  return res.json();
}

export async function getRAGStatus() {
  const res = await fetch(`${API_BASE_URL}/rag/status`);
  if (!res.ok) throw new Error('Failed to fetch RAG status');
  return res.json();
}

export async function reindexKnowledgeBase() {
  const res = await fetch(`${API_BASE_URL}/rag/reindex`, { method: 'POST' });
  if (!res.ok) throw new Error('Reindex failed');
  return res.json();
}

// ─── Unified RAG Search (Hybrid / Production / Graph / Agentic) ─────────────
export type RagArchitecture = 'hybrid' | 'production' | 'graph' | 'agentic' | 'auto' | 'combined';

export interface RagSearchOptions {
  jurisdiction?: string;
  category?: string;
  top_k?: number;
  rag_type?: RagArchitecture;
  filters?: Record<string, any>;
  user_key?: string;
  answer?: boolean;
}

export async function ragSearch(query: string, options?: RagSearchOptions) {
  const res = await fetch(`${API_BASE_URL}/rag/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, ...options })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'RAG search failed');
  }
  return res.json();
}

export async function getRAGSearchStats() {
  const res = await fetch(`${API_BASE_URL}/rag/search/stats`);
  if (!res.ok) throw new Error('Failed to fetch RAG search stats');
  return res.json();
}

export async function configureRAG(payload: {
  rag_type?: RagArchitecture;
  cache_ttl?: number;
  rate_limit?: number;
}) {
  const res = await fetch(`${API_BASE_URL}/rag/configure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'RAG configure failed');
  }
  return res.json();
}
