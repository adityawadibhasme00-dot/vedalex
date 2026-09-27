'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Wrench, Scale, Dna, FlaskConical, ArrowUpRight, Sparkles, Loader2,
  Zap, Bot, ChevronRight, CheckCircle2, AlertTriangle, GitBranch,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import {
  innolabApi, InnolabAgent, InnolabAgentWorkflow, OrchestratorPlan, OrchestratorRun,
} from '../lib/innolabApi';
import { AGENT_BLURBS } from '../lib/agentBlurbs';

const CATEGORY_META: Record<string, { label: string; icon: React.ReactNode; blurb: string; accent: string }> = {
  engineering: {
    label: 'Engineering',
    icon: <Wrench className="w-4 h-4" />,
    blurb: 'Innovation, technology intelligence & technical problem-solving',
    accent: 'from-cyan-600 to-sky-600',
  },
  ip: {
    label: 'Intellectual Property',
    icon: <Scale className="w-4 h-4" />,
    blurb: 'Prior art, freedom-to-operate, drafting & legal response',
    accent: 'from-indigo-600 to-violet-600',
  },
  life_sciences: {
    label: 'Life Sciences',
    icon: <Dna className="w-4 h-4" />,
    blurb: 'Document science, bio & pharma analytics',
    accent: 'from-rose-600 to-pink-600',
  },
  materials: {
    label: 'Materials & Formulation',
    icon: <FlaskConical className="w-4 h-4" />,
    blurb: 'Lab-ready formulation & material optimization',
    accent: 'from-emerald-600 to-teal-600',
  },
};

export function AgentHub() {
  const router = useRouter();

  const [agents, setAgents] = useState<InnolabAgent[]>([]);
  const [phases, setPhases] = useState<string[]>([]);
  const [workflows, setWorkflows] = useState<Record<string, InnolabAgentWorkflow>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [brief, setBrief] = useState('');
  const [plan, setPlan] = useState<OrchestratorPlan | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [run, setRun] = useState<OrchestratorRun | null>(null);
  const [runLoading, setRunLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const a = await innolabApi.agents();
      setAgents(a.agents);
      setPhases(a.phases);
      const wfMap: Record<string, InnolabAgentWorkflow> = {};
      const results = await Promise.allSettled(a.agents.map((x) => innolabApi.getAgentWorkflow(x.slug)));
      results.forEach((res, i) => {
        if (res.status === 'fulfilled') wfMap[a.agents[i].slug] = res.value;
      });
      setWorkflows(wfMap);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load the Agent Hub');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handlePlan = async () => {
    if (!brief.trim()) return;
    setPlanLoading(true);
    setRun(null);
    setError(null);
    try {
      setPlan(await innolabApi.orchestratorPlan(brief.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not plan this brief');
    } finally {
      setPlanLoading(false);
    }
  };

  const handleRunPlan = async () => {
    if (!plan) return;
    setRunLoading(true);
    setError(null);
    try {
      setRun(await innolabApi.orchestratorRun({ brief: plan.brief }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run the orchestrated plan');
    } finally {
      setRunLoading(false);
    }
  };

  const openAgent = (slug: string) => {
    const briefParam = plan && plan.brief?.trim()
      ? `?brief=${encodeURIComponent(plan.brief.trim())}`
      : '';
    router.push(`/innovation-lab/agents/${slug}${briefParam}`);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="relative overflow-hidden rounded-3xl border border-emerald-200 bg-gradient-to-br from-emerald-700 via-teal-700 to-cyan-800 text-white p-6 md:p-8">
        <div className="absolute -right-8 -top-10 opacity-10 rotate-12">
          <Bot className="w-48 h-48" />
        </div>
        <div className="flex items-start justify-between gap-4">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 border border-white/20 px-3 py-1 text-[11px] font-medium">
              <Zap className="w-3.5 h-3.5" /> POWERED BY THE IP-SAKTI ORCHESTRATION ENGINE
            </div>
            <h1 className="mt-4 text-2xl md:text-3xl font-bold font-display">Agent Hub</h1>
            <p className="mt-2 text-sm text-emerald-50/90 leading-relaxed">
              Domain-expert AI agents that combine planning, tools, reasoning and verification.
              Each agent takes a <span className="font-semibold text-white">brief intake</span> (1–2 questions),
              confirms how it understood your input, then runs its workflow autonomously — reporting every
              tool it used and every source it grounded on.
            </p>
          </div>
          <div className="hidden md:flex flex-col items-center gap-1 shrink-0">
            <span className="text-4xl font-bold">{agents.length}</span>
            <span className="text-[11px] uppercase tracking-wider text-emerald-100">agents</span>
          </div>
        </div>
      </div>

      {/* Orchestrator smart brief */}
      <GlassCard className="p-5 md:p-6">
        <div className="flex items-center gap-2 mb-1">
          <GitBranch className="w-4 h-4 text-emerald-600" />
          <h2 className="text-sm font-semibold text-slate-900">Orchestrator — one brief, many agents</h2>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Describe your goal in one sentence. The Orchestration Engine splits it into intents, plans an
          ordered agent chain, and runs them together.
        </p>
        <div className="flex flex-col sm:flex-row gap-2">
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) void handlePlan(); }}
            rows={2}
            placeholder="e.g. Ashwagandha aur Brahmi ka hydroalcoholic extract Canada export karna hai"
            className="flex-1 rounded-xl border border-emerald-200 bg-white/80 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300"
          />
          <button
            onClick={() => void handlePlan()}
            disabled={planLoading || !brief.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {planLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Plan
          </button>
        </div>

        {plan && (
          <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4">
            <div className="flex flex-wrap items-center gap-2 mb-3">
              {plan.intents.map((i) => (
                <Badge key={i.intent} variant="success" className="capitalize">{i.label}</Badge>
              ))}
              <span className="text-[11px] text-slate-500">→ {plan.agents.length} agents · {plan.total_steps} workflow steps</span>
            </div>
            <div className="space-y-2">
              {plan.agents.map((a, idx) => (
                <div key={a.slug} className="flex items-start gap-3">
                  <span className="inline-flex w-6 h-6 items-center justify-center rounded-full bg-emerald-600 text-white text-xs font-bold shrink-0">{idx + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900">{a.label} <span className="text-[11px] font-normal text-slate-400">· {a.slug}</span></p>
                    <p className="text-xs text-slate-500">{a.reason}</p>
                    <p className="text-[11px] text-teal-600 mt-0.5">tools: {a.tools.join(' · ')}</p>
                  </div>
                  <button
                    onClick={() => openAgent(a.slug)}
                    className="text-teal-600 hover:text-teal-800 text-xs font-medium flex items-center gap-1 shrink-0"
                  >
                    Open <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={() => void handleRunPlan()}
                disabled={runLoading}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {runLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                Run this plan (multi-agent)
              </button>
              <button onClick={() => { setPlan(null); setRun(null); }} className="text-xs text-slate-500 hover:text-emerald-700">Clear</button>
            </div>
          </div>
        )}

        {run && (
          <div className="mt-4 rounded-2xl border p-4 space-y-3" style={{ borderColor: run.verification.band === 'high' ? 'var(--emerald-200, #a7f3d0)' : 'var(--amber-200, #fde68a)', background: 'rgba(236,253,245,0.5)' }}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-slate-900">Run {run.run_id.slice(0, 8)} · {run.verification.band.toUpperCase()} verification · {run.verification.confidence}% confidence</p>
              <div className="flex gap-1.5">
                {run.verification.checks.map((c) => (
                  <span key={c.name} className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white border border-emerald-200 text-slate-600">{c.status}</span>
                ))}
              </div>
            </div>
            {run.steps.map((s) => (
              <div key={s.seq} className="flex items-start gap-3">
                {s.status === 'completed'
                  ? <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                  : <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />}
                <div className="flex-1">
                  <p className="text-sm text-slate-800">{s.label} <span className="text-xs text-slate-400">· {s.agent_slug}</span></p>
                  <p className="text-xs text-slate-500">{s.summary}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
          <button onClick={() => void load()} className="ml-2 text-red-600 underline">Retry</button>
        </div>
      )}

      {/* Only the agents — grouped by category */}
      {loading ? (
        <div className="flex items-center gap-3 py-24 justify-center text-slate-500">
          <Loader2 className="w-5 h-5 animate-spin" /> Loading Agent Hub…
        </div>
      ) : (
        phases.map((phase) => {
          const group = agents.filter((a) => a.phase === phase);
          if (group.length === 0) return null;
          const meta = CATEGORY_META[phase] || { label: phase, icon: <Bot className="w-4 h-4" />, blurb: '', accent: 'from-emerald-600 to-teal-600' };
          return (
            <section key={phase}>
              <div className="flex items-center gap-3 mb-3">
                <span className={`inline-flex w-9 h-9 items-center justify-center rounded-xl bg-gradient-to-br text-white ${meta.accent}`}>
                  {meta.icon}
                </span>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    {meta.label} <span className="text-sm font-medium text-slate-400">({group.length})</span>
                  </h2>
                  <p className="text-xs text-slate-500">{meta.blurb}</p>
                </div>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {group.map((agent) => {
                  return (
                    <GlassCard
                      key={agent.slug}
                      hover
                      className="p-5 flex flex-col"
                      onClick={() => openAgent(agent.slug)}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className={`inline-flex w-9 h-9 items-center justify-center rounded-xl bg-gradient-to-br text-white ${meta.accent}`}>
                          {meta.icon}
                        </span>
                        <p className="text-sm font-semibold text-slate-900">{agent.label}</p>
                      </div>
                      <p className="mt-3 text-xs text-slate-600 leading-relaxed flex-1 line-clamp-2">
                        {AGENT_BLURBS[agent.slug] || agent.description}
                      </p>
                      <button
                        onClick={(e) => { e.stopPropagation(); openAgent(agent.slug); }}
                        className="mt-4 inline-flex w-full items-center justify-center gap-1 rounded-xl bg-teal-600 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-700"
                      >
                        Start Agent <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </GlassCard>
                  );
                })}
              </div>
            </section>
          );
        })
      )}

      <p className="pt-2 text-center text-xs text-slate-400">
        AI-assisted research material — must be reviewed by a qualified professional. Not legal, medical, safety, regulatory, or patentability advice.
      </p>
    </div>
  );
}