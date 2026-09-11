'use client';
import React, { useState } from 'react';
import {
  BookMarked, Loader2, Search, AlertTriangle, CheckCircle2, XCircle,
  Languages, Library, Sparkles, ArrowRight, ScanSearch, Link2,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { mapTerminology } from '../lib/api';
import { TerminologyMapResponse } from '../types';

const viaBadge: Record<string, 'success' | 'warning' | 'neutral' | 'danger'> = {
  exact: 'success',
  synonym: 'success',
  fuzzy: 'warning',
  none: 'neutral',
};

const SUGGESTIONS = ['Amukkuram', 'Aśvagandhā', 'ബ്രഹ്മി', 'Shankhahuli', 'Halad', 'Managing', 'ḥalad'];

interface TerminologyMapperProps {
  passportIngredients?: string[];
}

export function TerminologyMapper({ passportIngredients = [] }: TerminologyMapperProps) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<TerminologyMapResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const unique = Array.from(new Set(passportIngredients.map((s) => s.trim()).filter(Boolean)));

  const run = async (q?: string) => {
    const qs = (q ?? query).trim();
    if (!qs) return;
    setLoading(true);
    setError('');
    try {
      const res = await mapTerminology(qs);
      setResult(res);
    } catch (e: any) {
      setError(e.message || 'Mapping failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const inputCls = 'w-full px-4 py-2.5 bg-emerald-50/50 border border-emerald-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:border-emerald-500';

  return (
    <div className="space-y-4">
      <GlassCard padding="md">
        <div className="flex items-center gap-2 mb-1">
          <BookMarked className="w-5 h-5 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900 font-display">Terminology Mapper</h3>
          <Badge variant="info" className="ml-auto">For RAG indexing</Badge>
        </div>
        <p className="text-xs text-slate-500">Resolve any written form of an Ayurvedic botanical — script native name, IAST transliteration, regional synonym or binomial — to one canonical entity key used by the passport and retrieval index.</p>

        <div className="flex gap-2 mt-4">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') run(); }}
            placeholder="e.g. Amukkuram, Aśvagandhā, ബ്രഹ്മി, Withania somnifera"
            className={inputCls}
          />
          <Button variant="primary" onClick={() => run()} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          </Button>
        </div>

        <div className="flex flex-wrap gap-1.5 mt-3">
          {SUGGESTIONS.map((s, i) => (
            <button key={i} onClick={() => { setQuery(s); run(s); }}
              className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-slate-50 text-slate-600 border border-slate-200 hover:bg-emerald-50 hover:border-emerald-300 transition">
              {s}
            </button>
          ))}
        </div>

        {unique.length > 0 && (
          <div className="mt-4">
            <div className="flex items-center gap-2 mb-1.5">
              <Link2 className="w-3.5 h-3.5 text-emerald-600" />
              <span className="text-[11px] font-semibold text-slate-600">From this passport</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {unique.map((n, i) => (
                <button key={i} onClick={() => { setQuery(n); run(n); }}
                  className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition">
                  {n}
                </button>
              ))}
            </div>
          </div>
        )}
      </GlassCard>

      {error && (
        <GlassCard padding="sm" className="border-red-300">
          <div className="flex items-center gap-2 text-xs text-red-700"><AlertTriangle className="w-4 h-4" /> {error}</div>
        </GlassCard>
      )}

      {result && (
        <>
          <GlassCard padding="sm" className={result.matched ? 'border-emerald-300' : 'border-amber-300'}>
            <div className="flex flex-wrap items-center gap-3">
              {result.matched ? <CheckCircle2 className="w-6 h-6 text-emerald-600" /> : <XCircle className="w-6 h-6 text-amber-500" />}
              <div className="flex-1 min-w-[180px]">
                <div className="text-[11px] text-slate-500 uppercase tracking-wider">Query · “{result.query}”</div>
                {result.matched ? (
                  <div className="text-base font-bold text-slate-900 font-display italic">{result.botanical_name}</div>
                ) : (
                  <div className="text-sm font-semibold text-slate-800">No canonical match</div>
                )}
              </div>
              <Badge variant={viaBadge[result.matched_via] || 'neutral'} dot>matched via {result.matched_via}</Badge>
            </div>
          </GlassCard>

          {result.matched && result.canonical_id && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <GlassCard padding="md">
                  <div className="text-[11px] text-slate-500 uppercase tracking-wider mb-1">Canonical entity key</div>
                  <div className="text-sm font-bold font-mono text-slate-900">{result.canonical_id}</div>
                  <div className="text-[11px] text-slate-500 mt-1">{result.family}</div>
                </GlassCard>
                <GlassCard padding="md">
                  <div className="text-[11px] text-slate-500 uppercase tracking-wider mb-1">API monograph</div>
                  <div className="text-sm font-bold font-mono text-slate-900">{result.api_monograph_id || '—'}</div>
                </GlassCard>
                <GlassCard padding="md">
                  <div className="text-[11px] text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1"><Languages className="w-3 h-3" /> Transliterations</div>
                  <div className="flex flex-wrap gap-1">
                    {result.transliterations.map((t, i) => <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">{t}</span>)}
                  </div>
                </GlassCard>
              </div>

              <GlassCard padding="md">
                <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Library className="w-4 h-4 text-blue-600" /> Classical Ayurvedic uses</h3>
                <div className="flex flex-wrap gap-1.5">
                  {result.classical_uses.map((u, i) => <Badge key={i} variant="info">{u}</Badge>)}
                </div>
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  {Object.entries(result.names).map(([lang, names]) => (
                    <div key={lang} className="px-3 py-2 rounded-xl bg-slate-50 border border-slate-100">
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">{lang}</div>
                      <div className="flex flex-wrap gap-1">
                        {names.slice(0, 4).map((n, i) => <span key={i} className="text-[11px] text-slate-700">{n}</span>)}
                      </div>
                    </div>
                  ))}
                </div>
              </GlassCard>

              <GlassCard padding="md" className="border-violet-200">
                <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><ScanSearch className="w-4 h-4 text-violet-600" /> RAG hint</h3>
                <p className="text-xs text-slate-600 leading-relaxed flex items-start gap-2"><Sparkles className="w-3.5 h-3.5 text-violet-500 flex-shrink-0 mt-0.5" /> {result.rag_hint}</p>
              </GlassCard>
            </>
          )}

          {!result.matched && result.nearest_possible.length > 0 && (
            <GlassCard padding="md">
              <div className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-1.5"><ArrowRight className="w-3.5 h-3.5 text-amber-600" /> Nearest vocabulary entries</div>
              <div className="flex flex-wrap gap-1.5">
                {result.nearest_possible.map((n, i) => (
                  <button key={i} onClick={() => { setQuery(n); run(n); }}
                    className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 hover:bg-amber-100 transition">
                    {n}
                  </button>
                ))}
              </div>
            </GlassCard>
          )}

          <p className="text-[10px] text-slate-400 italic px-1">Source: {result.source}</p>
        </>
      )}
    </div>
  );
}