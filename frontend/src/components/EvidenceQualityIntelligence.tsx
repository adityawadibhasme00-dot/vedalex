'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  FlaskConical, CheckCircle2, XCircle, AlertTriangle, Loader2,
  ArrowRight, Activity, BadgeCheck, FileCheck2, Sparkles, ClipboardCheck,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { getEvidenceQualityIntelligence } from '../lib/api';
import { EvidenceQualityIntelligenceResponse, IngredientIntelligence } from '../types';

const statusStyle: Record<string, { badge: 'success' | 'warning' | 'danger'; bar: string; label: string }> = {
  documented: { badge: 'success', bar: 'from-emerald-500 to-teal-400', label: 'Documented' },
  partially_documented: { badge: 'warning', bar: 'from-amber-400 to-yellow-400', label: 'Partial' },
  insufficient: { badge: 'danger', bar: 'from-red-400 to-rose-400', label: 'Insufficient' },
};

function Meter({ label, value, icon, barClass }: { label: string; value: number; icon: React.ReactNode; barClass: string }) {
  return (
    <GlassCard padding="md">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs font-semibold text-slate-700">{label}</span>
        <Badge variant={value >= 60 ? 'success' : value >= 40 ? 'warning' : 'danger'} className="ml-auto">{value}%</Badge>
      </div>
      <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full bg-gradient-to-r ${barClass} transition-all duration-700`} style={{ width: `${value}%` }} />
      </div>
    </GlassCard>
  );
}

function IngredientCard({ ing }: { ing: IngredientIntelligence }) {
  return (
    <GlassCard padding="md">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <div className="text-sm font-bold text-slate-900 font-display">{ing.botanical_name}</div>
          <div className="text-[11px] text-slate-500">Monograph: <code className="font-mono">{ing.api_monograph_id}</code> · {ing.canonical_id}</div>
        </div>
        <div className="flex gap-1.5">
          <Badge variant={ing.evidence_support_pct >= 60 ? 'success' : 'warning'}>Evidence {ing.evidence_support_pct}%</Badge>
          <Badge variant={ing.quality_readiness_pct >= 60 ? 'success' : 'warning'}>Quality {ing.quality_readiness_pct}%</Badge>
        </div>
      </div>

      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Evidence ladder</h4>
      <div className="space-y-2 mb-4">
        {ing.evidence_ladder.map((cell, i) => {
          const s = statusStyle[cell.support_status] || statusStyle.insufficient;
          return (
            <div key={i} className="px-3 py-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <div className="flex items-center justify-between gap-2 flex-wrap mb-1.5">
                <span className="text-xs font-semibold text-slate-800">{cell.level_label}</span>
                <Badge variant={s.badge} dot>{s.label} · {cell.support_pct}%</Badge>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-200 overflow-hidden mb-1.5">
                <div className={`h-full rounded-full bg-gradient-to-r ${s.bar}`} style={{ width: `${cell.support_pct}%` }} />
              </div>
              <p className="text-[11px] text-slate-600 leading-relaxed">{cell.note}</p>
              {cell.gap_reason && (
                <p className="text-[11px] text-red-600 mt-1 flex items-start gap-1"><AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" /> {cell.gap_reason}</p>
              )}
              <div className="flex flex-wrap gap-1 mt-1.5">
                {cell.sources.map((src, j) => (
                  <span key={j} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">{src}</span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Pharmacopoeia quality parameters</h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 mb-4">
        {ing.quality_parameters.map((p, i) => (
          <div key={i} className="flex items-start gap-2 px-2.5 py-2 rounded-xl border text-xs"
            style={{ borderColor: p.available ? '#a7f3d0' : '#fecaca', background: p.available ? '#f0fdf4' : '#fef2f2' }}>
            {p.available
              ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
              : <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />}
            <div>
              <div className="text-[11px] font-semibold text-slate-800">{p.param_name}</div>
              <div className="text-[10px] text-slate-500">{p.spec} · {p.test_method}</div>
            </div>
          </div>
        ))}
      </div>

      {ing.quality_gaps.length > 0 && (
        <div className="px-3 py-2 rounded-xl bg-red-50 border border-red-200">
          <div className="flex items-center gap-1.5 mb-1"><AlertTriangle className="w-3.5 h-3.5 text-red-600" /><span className="text-[11px] font-semibold text-red-700">Missing test coverage</span></div>
          <div className="flex flex-wrap gap-1">
            {ing.quality_gaps.map((g, j) => <span key={j} className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-700">{g}</span>)}
          </div>
        </div>
      )}
    </GlassCard>
  );
}

export function EvidenceQualityIntelligence({ passportId }: { passportId?: string }) {
  const [data, setData] = useState<EvidenceQualityIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!passportId) return;
    setLoading(true);
    setError('');
    try {
      const res = await getEvidenceQualityIntelligence(passportId);
      setData(res);
    } catch (e: any) {
      setError(e.message || 'Failed to load intelligence');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [passportId]);

  useEffect(() => { load(); }, [load]);

  if (!passportId) {
    return (
      <GlassCard padding="lg">
        <div className="flex items-center gap-3 text-sm text-slate-600">
          <FlaskConical className="w-5 h-5 text-amber-600" />
          Create an Innovation Passport first to run Evidence &amp; Quality Intelligence.
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-4">
      <GlassCard padding="md">
        <div className="flex items-center gap-2 mb-1">
          <FlaskConical className="w-5 h-5 text-amber-600" />
          <h3 className="text-sm font-bold text-slate-900 font-display">Evidence &amp; Quality Intelligence</h3>
          <Badge variant="info" className="ml-auto">API · e-AUSHADHI · NAMASTE aware</Badge>
        </div>
        <p className="text-xs text-slate-500">Research-evidence ladder + pharmacopoeia quality readiness per ingredient, compiled from the curated knowledge base.</p>
        {error && <p className="mt-2 text-xs text-red-600 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> {error}</p>}
      </GlassCard>

      {loading && (
        <GlassCard padding="lg"><div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-emerald-600" /></div></GlassCard>
      )}

      {data && data.ingredients.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Meter label="Overall evidence support" value={data.overall_evidence_support_pct} icon={<Activity className="w-4 h-4 text-emerald-600" />} barClass="from-emerald-500 to-teal-400" />
            <Meter label="Overall quality readiness" value={data.overall_quality_readiness_pct} icon={<ClipboardCheck className="w-4 h-4 text-blue-600" />} barClass="from-blue-500 to-cyan-400" />
          </div>

          <div className="space-y-4">
            {data.ingredients.map((ing) => <IngredientCard key={ing.canonical_id} ing={ing} />)}
          </div>

          <GlassCard padding="md">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Sparkles className="w-4 h-4 text-violet-600" /> Recommended actions</h3>
            <ul className="space-y-1.5">
              {data.recommended_actions.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-600">
                  <ArrowRight className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 mt-0.5" /> {a}
                </li>
              ))}
            </ul>
            <p className="text-xs text-emerald-800 mt-3 flex items-center gap-1.5"><BadgeCheck className="w-4 h-4" /> Feed verified gaps into the Evidence Matrix to track documents through their lifecycle.</p>
          </GlassCard>

          <p className="text-[10px] text-slate-400 italic px-1">{data.disclaimer}</p>
        </>
      )}

      {data && data.ingredients.length === 0 && (
        <GlassCard padding="md">
          <div className="flex items-start gap-2 text-xs text-slate-600">
            <FileCheck2 className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-slate-800 mb-1">No resolved ingredients found</div>
              {data.recommended_actions[0]}
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  );
}