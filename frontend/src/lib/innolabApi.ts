const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1';

export interface InnolabAgent {
  slug: string;
  label: string;
  phase: string;
  category_label: string;
  description: string;
  enabled_by_default: boolean;
  requires_evidence: boolean;
  live_default: string;
}

export interface InnolabAgentField {
  key: string;
  label: string;
  kind: 'text' | 'textarea' | 'multi';
  required: boolean;
  default: unknown;
}

export interface InnolabAgentDetail extends InnolabAgent {
  inputs_schema: InnolabAgentField[];
  sample_query: string;
}

export interface InnolabWorkflowStep {
  label: string;
  description: string;
}

export interface InnolabAgentQuestion {
  key: string;
  label: string;
  question: string;
  kind: 'text' | 'textarea' | 'multi' | 'select' | 'bool';
  required: boolean;
  options: string[];
  placeholder: string;
  help: string;
}

export interface InnolabAgentWorkflow extends InnolabAgent {
  steps: InnolabWorkflowStep[];
  questions: InnolabAgentQuestion[];
  auto_run?: boolean;
}

export interface ExtractedFeature {
  text: string;
  kind: string;
}

export interface AgentUnderstanding {
  slug: string;
  summary: string;
  features: ExtractedFeature[];
  markets: string[];
  ingredients: string[];
  resolved: string[];
}

export interface OrchestratorIntent {
  intent: string;
  label: string;
}

export interface OrchestratorPlannedAgent {
  slug: string;
  label: string;
  phase: string;
  description: string;
  reason: string;
  tools: string[];
  workflow_steps: string[];
  questions: number;
}

export interface OrchestratorPlan {
  brief: string;
  intents: OrchestratorIntent[];
  entities: {
    target_markets?: string[];
    ingredients?: string[];
  };
  agents: OrchestratorPlannedAgent[];
  total_steps: number;
}

export interface OrchestratorVerification {
  confidence: number;
  band: 'high' | 'medium' | 'low';
  checks: Array<{ name: string; status: string; detail: string; score: number }>;
  note: string;
}

export interface OrchestratorRun {
  run_id: string;
  project_id: string;
  status: string;
  chain: OrchestratorPlannedAgent[];
  base_inputs: Record<string, unknown>;
  steps: Array<{
    seq: number;
    agent_slug: string;
    label: string;
    status: string;
    summary: string;
    output: InnolabAgentRunResult['result'] & { workflow?: InspectStep[]; tools_used?: string[]; execution?: unknown };
  }>;
  verification: OrchestratorVerification;
}

export interface InspectStep {
  label: string;
  status?: string;
}

export interface ReportSection {
  title: string;
  caption?: string;
  columns?: string[];
  rows: Record<string, string | number>[];
}

export interface InnolabAgentRunResult {
  agent_slug: string;
  run_id: string | null;
  status: string;
  result: {
    agent_slug: string;
    phase: string;
    ok: boolean;
    summary: string;
    note: string;
    findings: Array<{ id: string; title: string; detail: string; severity: string }>;
    evidence: Array<{ kind: string; label: string; source: string; citation_ref?: string }>;
    citations: Array<{
      act_title: string;
      section_reference: string;
      authority: string;
      effective_date: string;
      exact_passage: string;
      source_url: string;
      authority_rank: number;
    }>;
    claims: string[];
    suggestions: string[];
    sections: ReportSection[];
    workflow: InspectStep[];
    tools_used: string[];
    execution: { status?: string; reasoning?: string } | null;
  };
}

export interface InnolabProvider {
  slug: string;
  label: string;
  available: boolean;
  live_mode_enabled: boolean;
  configured: boolean;
  capabilities: string[];
  notes: string[];
}

export interface InnolabProject {
  id: string;
  name: string;
  description: string | null;
  status: string;
  sensitivity: string;
  created_at: string | null;
}

export interface InnolabRunStep {
  seq: number;
  agent_slug: string;
  status: string;
  input_payload: Record<string, unknown> | null;
  output_payload: Record<string, unknown> | null;
  error: string | null;
}

export interface InnolabRun {
  id: string;
  project_id: string;
  status: string;
  run_type: string;
  current_step: string | null;
  steps: InnolabRunStep[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export const innolabApi = {
  agents: () => req<{ count: number; phases: string[]; agents: InnolabAgent[] }>('/innolab/agents'),
  getAgent: (slug: string) => req<InnolabAgentDetail>(`/innolab/agents/${slug}`),
  getAgentWorkflow: (slug: string) => req<InnolabAgentWorkflow>(`/innolab/agents/${slug}/workflow`),
  uploadAgentDocument: async (slug: string, file: File): Promise<{ slug: string; filename: string; ext: string; char_count: number; extracted_text: string; threats: string[] }> => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE_URL}/innolab/agents/${slug}/upload-document`, { method: 'POST', body: form });
    if (!res.ok) {
      const msg = await res.text().catch(() => res.statusText);
      throw new Error(msg);
    }
    return res.json();
  },
  extractAgentFeatures: (slug: string, payload: { inputs: Record<string, unknown> }) =>
    req<AgentUnderstanding>(`/innolab/agents/${slug}/extract-features`, { method: 'POST', body: JSON.stringify(payload) }),
  runAgent: (slug: string, payload: { project_id?: string; inputs: Record<string, unknown> }) =>
    req<InnolabAgentRunResult>(`/innolab/agents/${slug}/run`, { method: 'POST', body: JSON.stringify(payload) }),
  exportAgentResult: async (slug: string, result: InnolabAgentRunResult['result']): Promise<Blob> => {
    const res = await fetch(`${API_BASE_URL}/innolab/agents/${slug}/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ result }),
    });
    if (!res.ok) {
      const msg = await res.text().catch(() => res.statusText);
      throw new Error(msg);
    }
    return res.blob();
  },
  orchestratorPlan: (brief: string) =>
    req<OrchestratorPlan>('/innolab/orchestrator/plan', { method: 'POST', body: JSON.stringify({ brief }) }),
  orchestratorRun: (payload: { brief: string; agents?: string[]; project_id?: string; answers?: Record<string, unknown> }) =>
    req<OrchestratorRun>('/innolab/orchestrator/run', { method: 'POST', body: JSON.stringify(payload) }),
  providers: () => req<InnolabProvider[]>('/innolab/providers'),
  pulse: () => req<Record<string, unknown>>('/innolab/pulse'),
  listProjects: () => req<InnolabProject[]>('/innolab/projects'),
  createProject: (payload: { name: string; description?: string }) =>
    req<InnolabProject>('/innolab/projects', { method: 'POST', body: JSON.stringify(payload) }),
  createRun: (payload: { project_id: string; run_type?: string; agent_slugs?: string[] }) =>
    req<InnolabRun>('/innolab/runs', { method: 'POST', body: JSON.stringify(payload) }),
  getRun: (runId: string) => req<InnolabRun>(`/innolab/runs/${runId}`),
};