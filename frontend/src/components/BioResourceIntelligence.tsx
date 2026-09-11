'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  Leaf, Globe2, AlertTriangle, Loader2, MapPin, Scale, BookOpenText,
  Lightbulb, ShieldCheck, TrendingUp, Recycle, Sprout,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { getBioResourceIntelligence } from '../lib/api';
import { BioResourceGraphResponse, BioResourcePlant } from '../types';

const geoBadge: Record<string, 'success' | 'warning' | 'danger'> = {
  verified: 'success',
  supplier_confirmed: 'warning',
  pending: 'danger',
};

function NamesSection({ plant }: { plant: BioResourcePlant }) {
  return (
    <div className="mb-3">
      <div className="flex flex-wrap gap-1.5">
        {plant.english_names.map((n, i) => (
          <Badge key={i} variant="info">{n}</Badge>
        ))}
        {plant.ayurvedic_names['sanskrit']?.slice(0, 2).map((n, i) => (
          <span key={i} className="text-[11px] px-2 py-1 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 font-semibold">{n}</span>
        ))}
        {plant.plant_parts.map((p, i) => (
          <Badge key={i} variant="neutral">{p}</Badge>
        ))}
      </div>
    </div>
  );
}

function PlantCard({ plant }: { plant: BioResourcePlant }) {
  return (
    <GlassCard padding="md">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <div className="text-sm font-bold text-slate-900 font-display italic">{plant.botanical_name}</div>
          <div className="text-[11px] text-slate-500">{plant.family} · Monograph <code className="font-mono">{plant.api_monograph_id}</code></div>
        </div>
        <Badge variant={plant.evidence_support_pct >= 60 ? 'success' : 'warning'}>Evidence bridge {plant.evidence_support_pct}%</Badge>
      </div>

      <NamesSection plant={plant} />

      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5 text-emerald-600" /> Provenance &amp; geography</h4>
      <div className="space-y-1.5 mb-4">
        {plant.geography.map((g, i) => (
          <div key={i} className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-slate-50 border border-slate-100">
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-slate-800">{g.state}</div>
              <div className="text-[11px] text-slate-500 truncate">{g.note}</div>
              <div className="text-[10px] text-slate-400 italic mt-0.5">{g.source}</div>
            </div>
            <Badge variant={geoBadge[g.status] || 'warning'} dot>{g.status.replace('_', ' ')}</Badge>
          </div>
        ))}
        {plant.provenance_options.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {plant.provenance_options.map((o, i) => <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">{o}</span>)}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-4">
        <div className="px-3 py-2.5 rounded-xl bg-amber-50/60 border border-amber-200">
          <div className="flex items-center gap-1.5 mb-1"><TrendingUp className="w-3.5 h-3.5 text-amber-600" /><span className="text-[11px] font-bold text-slate-800">Trade demand</span></div>
          <p className="text-[11px] text-slate-600">{plant.trade_demand_class}</p>
          <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">{plant.price_trend_note}</p>
        </div>
        <div className="px-3 py-2.5 rounded-xl bg-emerald-50/60 border border-emerald-200">
          <div className="flex items-center gap-1.5 mb-1"><Recycle className="w-3.5 h-3.5 text-emerald-700" /><span className="text-[11px] font-bold text-slate-800">Conservation</span></div>
          <p className="text-[11px] text-slate-600">{plant.conservation_status}</p>
        </div>
      </div>

      {[
        { icon: <Scale className="w-3.5 h-3.5 text-violet-600 mt-0.5" />, title: 'ABS considerations', items: plant.abs_considerations, tone: 'bg-violet-50 border-violet-200 text-violet-900' },
        { icon: <BookOpenText className="w-3.5 h-3.5 text-blue-600 mt-0.5" />, title: 'Traditional knowledge (TKDL)', items: plant.tk_considerations, tone: 'bg-blue-50 border-blue-200 text-blue-900' },
        { icon: <Lightbulb className="w-3.5 h-3.5 text-amber-600 mt-0.5" />, title: 'IP considerations', items: plant.ip_considerations, tone: 'bg-amber-50 border-amber-200 text-amber-900' },
      ].map((s, i) => (
        <div key={i} className={`px-3 py-2.5 rounded-xl border mb-2 ${s.tone}`}>
          <div className="flex items-center gap-1.5 mb-1 relative">
            {s.icon}
            <span className="text-[11px] font-bold">{s.title}</span>
          </div>
          <ul className="space-y-1">
            {s.items.map((item, j) => (
              <li key={j} className="flex items-start gap-1.5 text-[11px] leading-relaxed"><span className="mt-1.5 w-1 h-1 rounded-full bg-current flex-shrink-0" />{item}</li>
            ))}
          </ul>
        </div>
      ))}
    </GlassCard>
  );
}

export function BioResourceIntelligence({ passportId }: { passportId?: string }) {
  const [data, setData] = useState<BioResourceGraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!passportId) return;
    setLoading(true);
    setError('');
    try {
      const res = await getBioResourceIntelligence(passportId);
      setData(res);
    } catch (e: any) {
      setError(e.message || 'Failed to load bio-resource graph');
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
          <Leaf className="w-5 h-5 text-emerald-600" />
          Create an Innovation Passport first to build the Bio-Resource Intelligence Graph.
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-4">
      <GlassCard padding="md">
        <div className="flex items-center gap-2 mb-1">
          <Sprout className="w-5 h-5 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900 font-display">Bio-Resource Intelligence Graph</h3>
          <Badge variant="info" className="ml-auto">NMPB · NBA · TKDL aware</Badge>
        </div>
        <p className="text-xs text-slate-500">Per-plant graph: identity &amp; names, provenance, conservation, ABS, TK and IP posture — bridged to the evidence ladder.</p>
        {error && <p className="mt-2 text-xs text-red-600 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> {error}</p>}
      </GlassCard>

      {loading && (
        <GlassCard padding="lg"><div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-emerald-600" /></div></GlassCard>
      )}

      {data && data.plants.length > 0 && (
        <>
          <div className="space-y-4">
            {data.plants.map((p) => <PlantCard key={p.canonical_id} plant={p} />)}
          </div>

          <GlassCard padding="md" className="border-emerald-300">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-600" /> Sourcing recommendations</h3>
            <ul className="space-y-1.5">
              {data.recommendations.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-600">
                  <Globe2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" /> {r}
                </li>
              ))}
            </ul>
          </GlassCard>

          <p className="text-[10px] text-slate-400 italic px-1">{data.disclaimer}</p>
        </>
      )}

      {data && data.plants.length === 0 && (
        <GlassCard padding="md">
          <div className="flex items-start gap-2 text-xs text-slate-600">
            <Leaf className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-slate-800 mb-1">No resolved botanicals found</div>
              {(data.recommendations[0]) || 'Add ingredients to the passport to map their bio-resources.'}
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  );
}