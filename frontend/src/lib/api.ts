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
  ProductClassifierResponse,
  ExportReadinessResponse,
  TerminologyMapResponse
} from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1';

export async function createPassportFromIntake(
  rawText: string,
  userLang: string = 'en',
  title?: string
): Promise<InnovationPassport> {
  const res = await fetch(`${API_BASE_URL}/passport/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      raw_text: rawText,
      user_lang: userLang,
      case_title: title
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

export async function classifyProduct(payload: {
  passport_id?: string;
  product_form?: string;
  dosage_form?: string;
  intended_use?: string;
  claims?: string[];
  ingredients?: string[];
  process_description?: string;
  label_disclaimer?: string;
}): Promise<ProductClassifierResponse> {
  const res = await fetch(`${API_BASE_URL}/intelligence/product-classify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to classify product');
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
