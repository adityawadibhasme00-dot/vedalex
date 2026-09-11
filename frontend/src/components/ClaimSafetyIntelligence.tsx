'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2, XCircle,
  Activity, Loader2, ArrowRight, Sparkles, FlaskConical, BadgeCheck, Scale,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { analyzeClaimSafety } from '../lib/api';
import { ClaimSafetyAnalysisResponse } from '../types';

const MARKETS = ['India', 'United States', 'Canada'];

const riskBadge: Record<string, 'danger' | 'warning' | 'success' | 'info'> = {
  HIGH_RISK: 'danger',
  CRITICAL: 'danger',
  WARNING: 'warning',
  SAFE: 'success',
};

const alignBadge: Record<string, 'success' | 'warning' | 'danger' | 'neutral'> = {
  supported: 'success',
  partial: 'warning',
  unsupported: 'danger',
  not_evaluated: 'neutral',
};

const sevBadge: Record<string, 'danger' | 'warning' | 'info'> = {
  HIGH: 'danger',
  MEDIUM: 'warning',
  LOW: 'info',
};

interface ClaimSafetyIntelligenceProps {
  passportId?: string;
  initialClaims?: string[];
}

export function ClaimSafetyIntelligence({ passportId, initialClaims }: ClaimSafetyIntelligenceProps) {
  const [claimsText, setClaimsText] = useState((initialClaims || []).join('\n'));
  const [ingredientsText, setIngredientsText] = useState('');
  const [markets, setMarkets] = useState<string[]>(MARKETS);
  const [result, setResult] = useState<ClaimSafetyAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const splitLines = (s: string) => s.split('\n').map((l) => l.trim()).filter(Boolean);
  const splitComma = (s: string) => s.split(',').map((l) => l.trim()).filter(Boolean);

  const run = useCallback(async (claimsOverride?: string[]) => {
    setLoading(true);
    setError('');
    try {
      const res = await analyzeClaimSafety({
        claims: claimsOverride || (claimsText ? splitLines(claimsText) : undefined),
        ingredients: ingredientsText ? splitComma(ingredientsText) : undefined,
        target_markets: markets,
        passport_id: passportId || undefined,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || 'Analysis failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [claimsText, ingredientsText, markets, passportId]);

  useEffect(() => {
    if (passportId) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [passportId]);

  const toggleMarket = (m: string) =>
    setMarkets((prev) => (prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]));

  return (
    <div className="space-y-4">
      <GlassCard padding="md">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="w-5 h-5 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900 font-display">Claim &amp; Safety Intelligence</h3>
          <Badge variant="info" className="ml-auto">Ayush Suraksha aware</Badge>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1.5 block">Proposed claims (one per line)</label>
            <textarea
              value={claimsText}
              onChange={(e) => setClaimsText(e.target.value)}
              rows={4}
              placeholder={'Supports healthy sleep\nTreats chronic insomnia'}
              className="w-full px-4 py-2.5 bg-emerald-50/50 border border-emerald-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Ingredients (comma separated)</label>
              <input
                value={ingredientsText}
                onChange={(e) => setIngredientsText(e.target.value)}
                placeholder={'Ashwagandha, Brahmi'}
                className="w-full px-4 py-2.5 bg-emerald-50/50 border border-emerald-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Target markets</label>
              <div className="flex flex-wrap gap-2">
                {MARKETS.map((m) => (
                  <button
                    key={m}
                    onClick={() => toggleMarket(m)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                      markets.includes(m)
                        ? 'bg-emerald-600 text-white border-emerald-600'
                        : 'bg-white text-slate-600 border-emerald-200 hover:bg-emerald-50'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
            <Button variant="primary" className="w-full" onClick={() => run()} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldAlert className="w-4 h-4" />}
              {loading ? 'Scanning claims…' : 'Analyze Claims'}
            </Button>
          </div>
        </div>
        {passportId && (
          <p className="mt-2 text-[11px] text-slate-500">
            Linked passport <code className="font-mono">{passportId}</code> — leave claims &amp; ingredients blank to pull them from the passport.
          </p>
        )}
      </GlassCard>

      {error && (
        <GlassCard padding="sm" className="border-red-300">
          <div className="flex items-center gap-2 text-xs text-red-700"><AlertTriangle className="w-4 h-4" /> {error}</div>
        </GlassCard>
      )}
      {loading && !result && (
        <GlassCard padding="lg"><div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-emerald-600" /></div></GlassCard>
      )}

      {result && (
        <>
          {/* Verdict banner */}
          <GlassCard padding="sm" className={result.overall_color === 'red' ? 'border-red-300' : result.overall_color === 'yellow' ? 'border-amber-300' : 'border-emerald-300'}>
            <div className="flex flex-wrap items-center gap-3">
              {result.overall_color === 'red' ? <ShieldAlert className="w-6 h-6 text-red-600" /> : result.overall_color === 'yellow' ? <AlertTriangle className="w-6 h-6 text-amber-600" /> : <ShieldCheck className="w-6 h-6 text-emerald-600" />}
              <div className="flex-1 min-w-[200px]">
                <div className="text-sm font-bold text-slate-900">
                  {result.overall_verdict} <span className="font-normal text-slate-500">— {result.summary}</span>
                </div>
              </div>
              <Badge variant={riskBadge[result.overall_verdict] || 'warning'} dot>{result.overall_verdict}</Badge>
            </div>
          </GlassCard>

          {/* Claim results */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-900 font-display flex items-center gap-2"><Scale className="w-4 h-4 text-blue-600" /> Per-claim assessment</h3>
            {result.claims.map((c, i) => (
              <GlassCard key={i} padding="sm">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex-1 min-w-[220px]">
                    <div className="text-sm font-semibold text-slate-900">{c.claim_text}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5 capitalize">{c.claim_category} claim · {c.regulation}</div>
                  </div>
                  <div className="flex gap-1.5 flex-wrap">
                    <Badge variant={riskBadge[c.risk_level] || 'warning'}>{c.risk_level}</Badge>
                    <Badge variant={alignBadge[c.evidence_alignment] || 'neutral'}>{c.evidence_alignment}</Badge>
                  </div>
                </div>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">{c.note}</p>
                {c.suggested_alternative && (
                  <div className="mt-3 flex items-start gap-2 px-3 py-2 rounded-xl bg-emerald-50 border border-emerald-200">
                    <BadgeCheck className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-emerald-800">
                      <span className="font-semibold">Compliant alternative wording:</span> “{c.suggested_alternative}”
                    </div>
                  </div>
                )}
              </GlassCard>
            ))}
          </div>

          {/* Misleading ads */}
          {result.misleading_ad_risk.flagged_phrases.length > 0 && (
            <GlassCard padding="sm" className="border-red-300">
              <div className="flex items-center gap-2 mb-2">
                <ShieldAlert className="w-5 h-5 text-red-600" />
                <h3 className="text-sm font-bold text-slate-900 font-display">Misleading advertising risk</h3>
              </div>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {result.misleading_ad_risk.flagged_phrases.map((p, i) => (
                  <Badge key={i} variant="danger" dot>{p}</Badge>
                ))}
              </div>
              <p className="text-xs text-slate-600">{result.misleading_ad_risk.act_citation}</p>
              <p className="text-xs text-slate-600 mt-1">{result.misleading_ad_risk.action}</p>
            </GlassCard>
          )}

          {/* Safety signals */}
          {result.safety_signals.length > 0 && (
            <GlassCard padding="sm">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="w-5 h-5 text-amber-600" />
                <h3 className="text-sm font-bold text-slate-900 font-display">Pharmacovigilance signals</h3>
                <Badge variant="warning" className="ml-auto">{result.safety_signals.length} signals</Badge>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {result.safety_signals.map((s, i) => (
                  <div key={i} className="px-3 py-2.5 rounded-xl bg-amber-50/60 border border-amber-200">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-slate-800">{s.ingredient}</span>
                      <Badge variant={sevBadge[s.severity] || 'info'}>{s.severity}</Badge>
                    </div>
                    <p className="text-xs text-slate-700 mt-1.5">{s.signal}</p>
                    <p className="text-[11px] text-amber-700 mt-1">⚠ {s.precaution}</p>
                    <p className="text-[10px] text-slate-500 mt-1 italic">Source: {s.evidence_source}</p>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          {/* Regulatory alerts */}
          <GlassCard padding="sm">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Sparkles className="w-4 h-4 text-violet-600" /> Regulatory alerts</h3>
            <ul className="space-y-1.5">
              {result.regulatory_alerts.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-600">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" /> {a}
                </li>
              ))}
            </ul>
          </GlassCard>

          <p className="text-[10px] text-slate-400 italic px-1">{result.disclaimer}</p>
        </>
      )}
    </div>
  );
}