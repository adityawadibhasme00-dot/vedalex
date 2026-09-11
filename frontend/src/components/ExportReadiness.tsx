'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  TrafficCone, Loader2, CheckCircle2, XCircle, MinusCircle,
  AlertTriangle, ArrowRight, Compass, Globe2, Sparkles,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { getExportReadiness } from '../lib/api';
import { ExportReadinessResponse, MarketReadinessItem } from '../types';

const overallBadge: Record<string, 'success' | 'warning' | 'danger'> = {
  ready: 'success',
  partial: 'warning',
  not_ready: 'danger',
};

const statusIcon: Record<string, React.ReactNode> = {
  satisfied: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />,
  partial: <MinusCircle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />,
  missing: <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />,
};

const statusColor: Record<string, string> = {
  satisfied: 'bg-emerald-50 border-emerald-200',
  partial: 'bg-amber-50 border-amber-200',
  missing: 'bg-red-50 border-red-200',
};

function MarketCard({ m, recommended }: { m: MarketReadinessItem; recommended: boolean }) {
  return (
    <GlassCard padding="md" className={recommended ? 'border-emerald-400' : ''}>
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{m.flag}</span>
          <h4 className="text-sm font-bold text-slate-900 font-display">{m.market}</h4>
          {recommended && <Badge variant="success" dot>Recommended</Badge>}
        </div>
        <Badge variant={overallBadge[m.overall_status] || 'warning'} dot>{m.overall_status.replace('_', ' ')}</Badge>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <div className="h-2.5 flex-1 rounded-full bg-slate-100 overflow-hidden">
          <div className={`h-full rounded-full bg-gradient-to-r transition-all duration-700 ${
            m.readiness_pct >= 75 ? 'from-emerald-500 to-teal-400' : m.readiness_pct >= 40 ? 'from-amber-400 to-yellow-400' : 'from-red-400 to-rose-400'
          }`} style={{ width: `${m.readiness_pct}%` }} />
        </div>
        <span className="text-sm font-bold text-slate-800">{m.readiness_pct}%</span>
      </div>

      {m.prerequisites_satisfied.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {m.prerequisites_satisfied.map((p, i) => <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">✓ {p}</span>)}
        </div>
      )}

      <div className="space-y-1.5">
        {m.gaps.map((g, i) => (
          <div key={i} className={`px-3 py-2.5 rounded-xl border ${statusColor[g.status]}`}>
            <div className="flex items-start gap-2">
              {statusIcon[g.status]}
              <div className="flex-1 min-w-0">
                <div className="text-[11px] font-semibold text-slate-800">{g.area} <span className="text-[10px] text-slate-400 font-normal">· {g.status}</span></div>
                <div className="text-[11px] text-slate-600 leading-relaxed">{g.requirement}</div>
                {g.status !== 'satisfied' && <div className="text-[10px] text-slate-500 mt-1 italic">{g.action}</div>}
                <div className="text-[10px] text-slate-400 mt-1">Source: {g.source}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

export function ExportReadiness({ passportId }: { passportId?: string }) {
  const [data, setData] = useState<ExportReadinessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!passportId) return;
    setLoading(true);
    setError('');
    try {
      const res = await getExportReadiness(passportId);
      setData(res);
    } catch (e: any) {
      setError(e.message || 'Failed to load export readiness');
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
          <TrafficCone className="w-5 h-5 text-emerald-600" />
          Create an Innovation Passport first to run the Market / Export Readiness Engine.
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-4">
      <GlassCard padding="md">
        <div className="flex items-center gap-2 mb-1">
          <TrafficCone className="w-5 h-5 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900 font-display">Market / Export Readiness Engine</h3>
          <Badge variant="info" className="ml-auto">{data?.origin_market || 'India'} origin</Badge>
        </div>
        <p className="text-xs text-slate-500">Deterministic gap comparison of the product posture against India, US, EU and Canada requirement sets — every gap carries an action and a source.</p>
        {error && <p className="mt-2 text-xs text-red-600 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> {error}</p>}
      </GlassCard>

      {loading && (
        <GlassCard padding="lg"><div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-emerald-600" /></div></GlassCard>
      )}

      {data && (
        <>
          {data.summary && (
            <GlassCard padding="sm" className="border-emerald-300">
              <div className="flex items-start gap-2 text-xs text-slate-700">
                <Compass className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Recommended first market:</span> {data.recommended_first_market}
                  <p className="text-slate-500 mt-1">{data.summary}</p>
                </div>
              </div>
            </GlassCard>
          )}

          <div className="space-y-4">
            {data.markets.map((m) => (
              <MarketCard key={m.market} m={m} recommended={m.market === data.recommended_first_market.split(' ')[0]} />
            ))}
          </div>

          <GlassCard padding="md">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Sparkles className="w-4 h-4 text-violet-600" /> Next actions</h3>
            <ul className="space-y-1.5">
              {data.next_actions.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-600"><ArrowRight className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 mt-0.5" /> {a}</li>
              ))}
            </ul>
            <p className="text-xs text-emerald-800 mt-3 flex items-center gap-1.5"><Globe2 className="w-4 h-4" /> Pair each missing gap with the Evidence Matrix to start assembling the dossier.</p>
          </GlassCard>

          <p className="text-[10px] text-slate-400 italic px-1">{data.disclaimer}</p>
        </>
      )}
    </div>
  );
}