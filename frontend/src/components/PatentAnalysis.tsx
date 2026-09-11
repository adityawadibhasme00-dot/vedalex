'use client';
import React, { useState, useEffect } from 'react';
import {
  Loader2, TrendingUp, Lightbulb, AlertTriangle, FileSearch,
  CheckCircle2, Award, BarChart3, ThumbsUp, ShieldAlert, ArrowRight, Scale,
} from 'lucide-react';
import { getPatentReadiness } from '../lib/api';
import { PatentReadiness } from '../types';
import { GlassCard } from './ui/GlassCard';
import { ReadinessGauge } from './ReadinessGauge';
import { Badge } from './ui/Badge';

interface PatentAnalysisProps {
  passportId: string;
}

const COMPONENT_COLORS: Record<string, string> = {
  novelty: '#22C55E',
  prior_art: '#3B82F6',
  section3p: '#8B5CF6',
  disclosure: '#F59E0B',
  evidence: '#06B6D4',
  ownership: '#EC4899',
  fto: '#F97316',
  documentation: '#10B981',
};

const statusStyles = {
  good: { bar: 'bg-emerald-500', chip: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  warn: { bar: 'bg-amber-500', chip: 'bg-amber-100 text-amber-700 border-amber-200' },
  risk: { bar: 'bg-red-500', chip: 'bg-red-100 text-red-700 border-red-200' },
};

const statusLabel: Record<string, string> = { good: 'On track', warn: 'Improve', risk: 'High risk' };

export default function PatentAnalysis({ passportId }: PatentAnalysisProps) {
  const [data, setData] = useState<PatentReadiness | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (passportId) {
      setIsLoading(true);
      setError(null);
      getPatentReadiness(passportId)
        .then(setData)
        .catch((e) => setError(e.message))
        .finally(() => setIsLoading(false));
    }
  }, [passportId]);

  if (isLoading) {
    return (
      <GlassCard padding="lg" className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600 mr-3" />
        <span className="text-slate-500 text-sm">Calculating patent readiness from 8 engines...</span>
      </GlassCard>
    );
  }

  if (error) {
    return (
      <GlassCard padding="lg" className="flex items-center justify-center h-64">
        <span className="text-red-600 text-sm">{error}</span>
      </GlassCard>
    );
  }

  if (!data) {
    return (
      <GlassCard padding="lg" className="flex items-center justify-center h-64">
        <span className="text-slate-500 text-sm">Create an Innovation Passport to see patent analysis</span>
      </GlassCard>
    );
  }

  const sorted = [...(data.components || [])].sort((a, b) => b.earned / b.max - a.earned / a.max);

  return (
    <div className="space-y-6 animate-slide-up">
      {/* ─── Gauge + side summary ─────────────────────────────── */}
      <GlassCard padding="lg">
        <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-8 items-center">
          <ReadinessGauge value={data.overall_readiness} />
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Scale className="w-4 h-4 text-emerald-600" />
              <h3 className="text-sm font-bold text-slate-900">How this score is calculated</h3>
            </div>
            <p className="text-[12px] text-slate-500 leading-relaxed mb-4">
              Deterministic output of <span className="font-semibold text-slate-700">8 engines</span> — Patent Search (prior art),
              Ingredient &amp; Novelty analysis, Section 3(p) check, Disclosure Sentinel, Evidence-to-Claim matrix,
              Ownership audit, FTO scan and Documentation completeness. No random scores.
            </p>
            <div className="flex flex-wrap gap-2">
              {data.patent_ready ? (
                <Badge variant="success" dot><CheckCircle2 className="w-3 h-3 inline mr-1" /> Patent Ready</Badge>
              ) : (
                <Badge variant="warning" dot><AlertTriangle className="w-3 h-3 inline mr-1" /> Patent Not Ready Yet</Badge>
              )}
              <Badge variant="info" dot><BarChart3 className="w-3 h-3 inline mr-1" /> {data.overall_readiness}% overall</Badge>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-5">
              <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3">
                <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-600">Novelty</div>
                <div className="text-2xl font-black text-emerald-900">{Math.round(data.novelty_score)}%</div>
              </div>
              <div className="rounded-xl bg-blue-50 border border-blue-200 px-4 py-3">
                <div className="text-[11px] font-bold uppercase tracking-wide text-blue-600">Inventive Step</div>
                <div className="text-2xl font-black text-blue-900">{Math.round(data.inventive_step_score)}%</div>
              </div>
              <div className="rounded-xl bg-violet-50 border border-violet-200 px-4 py-3">
                <div className="text-[11px] font-bold uppercase tracking-wide text-violet-600">Prior Art Overlap</div>
                <div className="text-2xl font-black text-violet-900">{data.prior_art_overlap}%</div>
              </div>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* ─── 8-component weighted breakdown ──────────────────── */}
      <GlassCard padding="lg">
        <div className="flex items-center gap-2 mb-1">
          <BarChart3 className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Score Breakdown — Weighted Engines</h3>
        </div>
        <p className="text-[11px] text-slate-500 mb-4">
          30 Novelty + 20 Prior Art + 15 Section 3(p) + 10 Disclosure + 10 Evidence + 5 Ownership + 5 FTO + 5 Documentation = 100
        </p>
        <div className="space-y-3">
          {[...(data.components || [])]
            .sort((a, b) => b.max - a.max)
            .map((c) => {
              const ratio = c.earned / c.max;
              const ss = statusStyles[c.status] || statusStyles.warn;
              return (
                <div key={c.code}>
                  <div className="flex items-center justify-between mb-1 gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: COMPONENT_COLORS[c.code] }} />
                      <span className="text-[12px] font-semibold text-slate-800 capitalize">{c.code.replace('_', ' ')}</span>
                      <Badge variant={c.status === 'good' ? 'success' : c.status === 'warn' ? 'warning' : 'danger'} className={`text-[9px] ${ss.chip}`}>
                        {statusLabel[c.status]}
                      </Badge>
                    </div>
                    <span className="text-[12px] font-bold text-slate-700">{c.earned} / {c.max}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${ss.bar}`}
                      style={{ width: `${ratio * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
        </div>
        <div className="mt-4 flex items-center gap-2 text-[11px] text-slate-500">
          <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
          Every sub-score is derived deterministically from passport facts + knowledge base — never random.
        </div>
      </GlassCard>

      {/* ─── Strengths / Weaknesses / Next Actions ─────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <GlassCard padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <ThumbsUp className="w-4 h-4 text-emerald-600" />
            <h3 className="text-sm font-bold text-slate-900">Strengths</h3>
          </div>
          <div className="space-y-2">
            {(data.strengths?.length ? data.strengths : ['Consistent score computation']).map((s, i) => (
              <div key={i} className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-emerald-50/70 border border-emerald-200 text-xs text-emerald-800">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" /> {s}
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <h3 className="text-sm font-bold text-slate-900">Weaknesses</h3>
          </div>
          <div className="space-y-2">
            {(data.weaknesses?.length ? data.weaknesses : ['No significant risks detected']).map((w, i) => (
              <div key={i} className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-amber-50/70 border border-amber-200 text-xs text-amber-800">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" /> {w}
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* ─── Next Recommended Actions ─────────────────────────── */}
      <GlassCard padding="lg">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Next Recommended Actions</h3>
        </div>
        <div className="space-y-2.5">
          {(data.next_actions?.length ? data.next_actions : data.recommendations).map((rec, i) => (
            <div key={i} className="flex items-center gap-3 px-3.5 py-3 rounded-xl bg-blue-50/70 border border-blue-200 text-xs text-blue-800">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-[11px] font-bold flex items-center justify-center flex-shrink-0">{i + 1}</span>
              {rec}
            </div>
          ))}
        </div>
      </GlassCard>

      {/* ─── Similar Patents ──────────────────────────────────── */}
      <GlassCard padding="lg">
        <div className="flex items-center gap-2 mb-4">
          <FileSearch className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-bold text-slate-900">Similar Patents (Prior Art Signals)</h3>
        </div>
        {data.similar_patents?.length ? (
          <div className="space-y-3">
            {data.similar_patents.map((p, i) => (
              <div key={i} className="flex items-center justify-between p-3.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition">
                <div>
                  <div className="text-sm text-slate-900 font-medium">{p.title}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{p.patent_id} · {p.jurisdiction}</div>
                </div>
                <Badge variant={p.similarity > 50 ? 'danger' : p.similarity > 30 ? 'warning' : 'success'}>{p.similarity}% overlap</Badge>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500">No close botanical prior-art matches found — favourable signal.</p>
        )}
      </GlassCard>

      {/* ─── Missing Evidence ─────────────────────────────────── */}
      <GlassCard padding="lg">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-4 h-4 text-amber-600" />
          <h3 className="text-sm font-bold text-slate-900">Evidence Gaps to Close</h3>
        </div>
        <div className="space-y-2">
          {(data.missing_evidence || []).map((ev, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-amber-50/70 border border-amber-200 text-xs text-amber-700">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" /> {ev}
            </div>
          ))}
        </div>
      </GlassCard>

      <div className="flex items-center gap-2 text-[11px] text-slate-500 px-1">
        <Award className="w-4 h-4 text-emerald-600" />
        Score = 30·Novelty + 20·Prior Art + 15·Section 3(p) + 10·Disclosure + 10·Evidence + 5·Ownership + 5·FTO + 5·Documentation
      </div>
    </div>
  );
}