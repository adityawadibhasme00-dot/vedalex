'use client';
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Sparkles, Compass, Target, Database, AlertTriangle, CheckCircle2,
  ArrowRight, Lightbulb, Layers, TrendingUp, RefreshCw, GitBranch,
  ShieldAlert, Scale, Hash, ListChecks, MapPin,
} from 'lucide-react';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { Skeleton } from './ui/Skeleton';
import { Button } from './ui/Button';
import { ReadinessGauge } from './ReadinessGauge';
import { getWhiteSpaceAnalysis } from '../lib/api';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';
import {
  WhiteSpaceResponse, WhiteSpaceCard, WhiteSpaceHeatmap, WhiteSpaceLandscape,
} from '../types';

interface WhiteSpaceNavigatorProps {
  passportId?: string;
}

const BAND_META: Record<string, { color: string; variant: 'success' | 'warning' | 'danger'; labelKey: string }> = {
  'High Innovation Opportunity': { color: '#10B981', variant: 'success', labelKey: 'ws_band_blue_ocean' },
  'Good Opportunity': { color: '#34D399', variant: 'success', labelKey: 'ws_band_promising' },
  Moderate: { color: '#F59E0B', variant: 'warning', labelKey: 'ws_band_balanced' },
  Crowded: { color: '#EF4444', variant: 'danger', labelKey: 'ws_band_saturated' },
};

const CARD_BADGE: Record<string, { variant: 'success' | 'warning' | 'danger'; labelKey: string }> = {
  opportunity: { variant: 'success', labelKey: 'ws_badge_opportunity' },
  medium: { variant: 'warning', labelKey: 'ws_badge_medium' },
  crowded: { variant: 'danger', labelKey: 'ws_badge_crowded' },
};

function overallBand(status: string): { color: string; variant: 'success' | 'warning' | 'danger'; labelKey: string } {
  return BAND_META[status] ?? BAND_META.Moderate;
}

function riskTone(v: number) {
  if (v >= 60) return { variant: 'danger' as const, noteKey: 'ws_risk_high' };
  if (v >= 35) return { variant: 'warning' as const, noteKey: 'ws_risk_moderate' };
  return { variant: 'success' as const, noteKey: 'ws_risk_low' };
}

function OpportunityHeatmap({ heatmap }: { heatmap: WhiteSpaceHeatmap }) {
  const { lang } = useLang();
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px] border-separate border-spacing-1.5">
        <thead>
          <tr>
            <th className="text-left text-slate-500 font-semibold px-1">{t('ws_ingredient_x_delivery', lang)}</th>
            {heatmap.forms.map((f) => (
              <th key={f} className="text-center text-slate-500 font-semibold">{f}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {heatmap.herbs.map((herb) => (
            <tr key={herb}>
              <td className="font-bold text-slate-700 px-1 whitespace-nowrap">{herb}</td>
              {heatmap.forms.map((form) => {
                const cell = heatmap.cells.find((c) => c.herb === herb && c.form === form);
                const fill = cell ? heatmap.colors[cell.label] ?? '#e2e8f0' : '#e2e8f0';
                return (
                  <td key={form} className="text-center">
                    <div
                      className="rounded-xl px-1.5 py-2.5 min-w-[4.2rem] font-bold text-white shadow-sm"
                      style={{ background: fill }}
                      title={cell?.rationale}
                    >
                      {cell?.value ?? '—'}
                    </div>
                    <div className="text-[8px] text-slate-400 mt-0.5">{cell?.label ?? ''}</div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center justify-center gap-4 mt-2 text-[10px] text-slate-500">
        {Object.entries(heatmap.colors).map(([key, color]) => (
          <span key={key} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            {key[0].toUpperCase() + key.slice(1)}
          </span>
        ))}
      </div>
    </div>
  );
}

function OpportunityCard({ card, index }: { card: WhiteSpaceCard; index: number }) {
  const { lang } = useLang();
  const meta = CARD_BADGE[card.badge] ?? CARD_BADGE.medium;
  const [open, setOpen] = useState(false);
  return (
    <GlassCard padding="md" className="flex flex-col animate-slide-up">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 text-white text-sm font-black flex items-center justify-center shadow-sm">
            {index + 1}
          </span>
          <div>
            <h4 className="text-sm font-bold text-slate-900 font-display">{card.title}</h4>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Badge variant={meta.variant} dot>{t(meta.labelKey, lang)}</Badge>
              <span className="text-[10px] text-slate-500">{t('ws_patent_density', lang).replace('{n}', String(card.patent_density))}</span>
            </div>
          </div>
        </div>
        <div className="text-center flex-shrink-0">
          <div className={`text-2xl font-black leading-none ${card.score >= 66 ? 'text-emerald-600' : card.score >= 40 ? 'text-amber-600' : 'text-red-500'}`}>
            {card.score}
          </div>
          <div className="text-[9px] text-slate-500 font-semibold">{t('ws_score', lang)}</div>
        </div>
      </div>

      <p className="text-xs text-slate-600 leading-relaxed mt-3">{card.why}</p>

      <div className="mt-3 rounded-xl bg-emerald-50 border border-emerald-200 p-3">
        <div className="flex items-center gap-1.5 text-[10px] font-bold text-emerald-700 uppercase tracking-wider mb-1">
          <ArrowRight className="w-3 h-3" /> {t('ws_next_action_label', lang)}
        </div>
        <p className="text-[11px] text-slate-600 leading-relaxed">{card.next_action}</p>
      </div>

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="mt-3 flex items-center gap-1.5 text-[10px] font-bold text-slate-500 hover:text-blue-600 transition"
        aria-expanded={open}
      >
        <GitBranch className="w-3 h-3" /> {t('ws_how_scored', lang)} <ArrowRight className={`w-3 h-3 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>

      {open && (
        <div className="mt-2 space-y-2 rounded-xl border border-slate-200 bg-white/70 p-3 text-[10px] text-slate-500">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-600">{t('ws_scored_dimensions', lang)}</span>
            <span className="font-bold text-slate-700">{card.xai.confidence}%</span>
          </div>
          {card.xai.tkdl_overlap && (
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-600">{t('ws_tkdl_overlap', lang)}</span>
              <span>{card.xai.tkdl_overlap}</span>
            </div>
          )}
          <div className="flex items-start gap-1.5">
            <Scale className="w-3 h-3 text-amber-500 mt-0.5 flex-shrink-0" />
            <span>{card.xai.section3p}</span>
          </div>
          <div className="flex items-start gap-1.5">
            <Lightbulb className="w-3 h-3 text-blue-500 mt-0.5 flex-shrink-0" />
            <span>{card.xai.rationale}</span>
          </div>
          {card.xai.insufficient && (
            <div className="flex items-start gap-1.5 text-amber-700">
              <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
              <span>{t('ws_insufficient_evidence', lang)}</span>
            </div>
          )}
        </div>
      )}
    </GlassCard>
  );
}

function LandscapeGraph({ landscape }: { landscape: WhiteSpaceLandscape }) {
  const { lang } = useLang();
  const patentNodes = landscape.nodes.filter((n) => n.type === 'patent' || n.type === 'tk');
  const methodNodes = landscape.nodes.filter((n) => n.type === 'method');
  const ingredientNodes = landscape.nodes.filter((n) => n.type === 'ingredient');
  return (
    <div className="space-y-3">
      {ingredientNodes.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
            <MapPin className="w-3 h-3 text-emerald-600" /> {t('ws_formulation_ingredients', lang)}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {ingredientNodes.map((n) => (
              <span key={n.id} className="px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-800 text-[11px] font-semibold border border-emerald-300">
                {n.label}
              </span>
            ))}
          </div>
        </div>
      )}
      {methodNodes.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
            <Layers className="w-3 h-3 text-violet-600" /> {t('ws_extraction_methods', lang)}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {methodNodes.map((n) => (
              <span key={n.id} className="px-2.5 py-1 rounded-lg bg-violet-100 text-violet-800 text-[11px] font-semibold border border-violet-300">
                {n.label}
              </span>
            ))}
          </div>
        </div>
      )}
      {patentNodes.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
            <Database className="w-3 h-3 text-blue-600" /> {t('ws_patent_tk_clusters', lang)}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {patentNodes.map((n) => (
              <span key={n.id} className="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-800 text-[11px] font-semibold border border-blue-200 flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${n.type === 'tk' ? 'bg-amber-500' : 'bg-blue-500'}`} />
                {n.label}
                {n.type === 'patent' && (
                  <span className="text-[9px] text-blue-500 font-normal">
                    {t('ws_links_count', lang).replace('{n}', String(landscape.links.filter((l) => l.target === n.id).length))}
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-2 border-t border-slate-100">
        <span>{t('ws_entities_count', lang).replace('{n}', String(landscape.nodes.length))}</span>
        <span>{t('ws_relationships_count', lang).replace('{n}', String(landscape.links.length))}</span>
      </div>
    </div>
  );
}

export function WhiteSpaceNavigator({ passportId }: WhiteSpaceNavigatorProps) {
  const { lang } = useLang();
  const [data, setData] = useState<WhiteSpaceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const fetchAnalysis = useCallback(async (silent = false) => {
    if (!passportId) return;
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError('');
    try {
      const res = await getWhiteSpaceAnalysis(passportId);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('ws_load_failed', lang));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [passportId]);

  useEffect(() => {
    fetchAnalysis();
  }, [fetchAnalysis]);

  const radarData = useMemo(() => {
    if (!data) return [];
    return (data.radar.labels || []).map((label, i) => ({
      name: label,
      value: data.radar.values[i] || 0,
    }));
  }, [data]);

  if (loading) {
    return (
      <GlassCard padding="lg">
        <Skeleton lines={6} />
      </GlassCard>
    );
  }

  if (!passportId) {
    return (
      <GlassCard padding="lg">
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <Compass className="w-5 h-5 text-emerald-600" />
          {t('ws_no_passport', lang)}
        </div>
      </GlassCard>
    );
  }

  if (error) {
    return (
      <GlassCard padding="lg">
        <div className="flex items-start gap-3 text-sm text-red-600">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-bold">{t('ws_analysis_failed', lang)}</div>
            <div className="text-xs text-slate-500 mt-1">{error}</div>
            <Button variant="secondary" size="sm" className="mt-3" onClick={() => fetchAnalysis()}>
              <RefreshCw className="w-3.5 h-3.5" /> {t('common_retry', lang)}
            </Button>
          </div>
        </div>
      </GlassCard>
    );
  }

  if (!data) return null;

  const band = overallBand(data.status);
  const tk = riskTone(data.tk_risk);

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header band */}
      <GlassCard padding="lg" className="relative overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-4 relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-600 to-emerald-800 flex items-center justify-center text-white shadow-md shadow-emerald-900/20">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 font-display flex items-center gap-2">
                {t('ws_navigator_title', lang)}
                <Badge variant={band.variant} dot><Target className="w-3 h-3" /> {data.status}</Badge>
              </h3>
              <p className="text-[11px] text-slate-500">{data.case_title} · {t('ws_generated_at', lang)} {new Date(data.generated_at).toLocaleString()}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="neutral"><Hash className="w-3 h-3" /> {t('common_confidence', lang)} {data.confidence}%</Badge>
            <Button variant="secondary" size="sm" onClick={() => fetchAnalysis(true)} disabled={refreshing}>
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} /> {t('common_refresh', lang)}
            </Button>
          </div>
        </div>
        <Compass className="w-32 h-32 text-emerald-500/10 absolute -right-6 -top-8 rotate-12 pointer-events-none" />
      </GlassCard>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Overall score gauge */}
        <GlassCard padding="lg" className="flex flex-col items-center">
          <ReadinessGauge value={data.overall_score} label={t('ws_opportunity_score_label', lang)} size={220} />
          <div className="flex items-center gap-1.5 mt-2 text-[11px] text-slate-500">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
            {t('ws_innovation_window', lang).replace('{band}', t(band.labelKey, lang))}
          </div>
        </GlassCard>

        {/* Dimension radar */}
        <GlassCard padding="lg" className="lg:col-span-1">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-blue-600" />
            <h4 className="text-sm font-bold text-slate-900">{t('ws_scored_dimensions', lang)}</h4>
          </div>
          <div className="h-56">
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius="68%">
                  <PolarGrid stroke="#cbd5e1" />
                  <PolarAngleAxis dataKey="name" tick={{ fill: '#475569', fontSize: 9 }} />
                  <Radar dataKey="value" stroke="#10B981" fill="#10B981" fillOpacity={0.35} strokeWidth={1.5} />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 12, fontSize: 11 }}
                    itemStyle={{ color: '#0f172a' }}
                    labelStyle={{ color: '#334155' }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">{t('ws_no_dimension_data', lang)}</div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-1.5 mt-2">
            {(data.dimensions || []).slice(0, 6).map((d) => (
              <div key={d.label} className="rounded-lg bg-emerald-50 border border-emerald-200 px-2 py-1.5 flex items-center justify-between">
                <span className="text-[10px] text-slate-500">{d.label}</span>
                <span className="text-[11px] font-bold text-slate-800">{d.value}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* Risk / readiness status */}
        <GlassCard padding="lg" className="space-y-3">
          <h4 className="text-sm font-bold text-slate-900">{t('ws_tk_patent_posture', lang)}</h4>
          <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500 font-medium flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-500" /> {t('ws_tk_risk', lang)}
              </span>
              <Badge variant={tk.variant} dot>{data.tk_risk}%</Badge>
            </div>
            <p className="text-[11px] text-slate-500 mt-1.5 leading-relaxed">{t(tk.noteKey, lang)}</p>
          </div>
          <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500 font-medium flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> {t('ws_patent_readiness', lang)}
              </span>
              <span className="font-bold text-slate-800">{data.patent_readiness}/100</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden mt-2">
              <div
                className="h-full rounded-full"
                style={{ width: `${Math.min(100, data.patent_readiness)}%`, background: data.patent_readiness >= 70 ? '#10B981' : data.patent_readiness >= 40 ? '#F59E0B' : '#EF4444' }}
              />
            </div>
          </div>
          <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200">
            <div className="flex items-start gap-1.5 text-[11px] text-amber-800">
              <Scale className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
              <span className="leading-relaxed">{data.section3p}</span>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Opportunity heatmap */}
      <GlassCard padding="lg">
        <div className="flex items-center gap-2 mb-3">
          <Layers className="w-4 h-4 text-emerald-600" />
          <h4 className="text-sm font-bold text-slate-900">{data.heatmap.title}</h4>
          <span className="ml-auto text-[10px] text-slate-400">{t('ws_heatmap_note', lang)}</span>
        </div>
        <OpportunityHeatmap heatmap={data.heatmap} />
      </GlassCard>

      {/* Opportunity cards */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-blue-600" />
          <h4 className="text-sm font-bold text-slate-700 uppercase tracking-wider">{t('ws_top_opportunities', lang)}</h4>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {data.cards.map((card, i) => (
            <OpportunityCard key={card.title} card={card} index={i} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recommendations */}
        <GlassCard padding="lg">
          <div className="flex items-center gap-2 mb-3">
            <ListChecks className="w-4 h-4 text-blue-600" />
            <h4 className="text-sm font-bold text-slate-900">{t('ws_recommendations', lang)}</h4>
          </div>
          <ol className="space-y-2">
            {data.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-2 text-[11px] text-slate-600 leading-relaxed">
                <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 text-[9px] font-bold flex items-center justify-center flex-shrink-0 mt-px">
                  {i + 1}
                </span>
                <span>{rec}</span>
              </li>
            ))}
          </ol>
        </GlassCard>

        {/* Landscape clusters */}
        <GlassCard padding="lg">
          <div className="flex items-center gap-2 mb-3">
            <Database className="w-4 h-4 text-violet-600" />
            <h4 className="text-sm font-bold text-slate-900">{t('ws_patent_tk_landscape', lang)}</h4>
          </div>
          <LandscapeGraph landscape={data.landscape} />
        </GlassCard>
      </div>
    </div>
  );
}