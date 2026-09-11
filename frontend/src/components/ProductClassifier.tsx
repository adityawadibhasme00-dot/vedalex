'use client';
import React, { useState, useCallback, useEffect } from 'react';
import {
  FlaskConical, Loader2, ArrowRight, AlertTriangle, Sparkles, Landmark,
  FileText, BadgeCheck, Layers,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { classifyProduct } from '../lib/api';
import { ProductClassifierResponse } from '../types';
import { InnovationPassport } from '../types';

const confBadge: Record<string, 'success' | 'warning' | 'danger'> = {
  HIGH: 'success',
  MEDIUM: 'warning',
  LOW: 'danger',
};

const pathColor: Record<string, string> = {
  ayurvedic_drug: 'bg-red-100 text-red-700 border-red-300',
  proprietary_ayurveda: 'bg-orange-100 text-orange-700 border-orange-300',
  ayurveda_aahara: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  cosmetic: 'bg-pink-100 text-pink-700 border-pink-300',
  nutraceutical: 'bg-violet-100 text-violet-700 border-violet-300',
  unresolved: 'bg-slate-100 text-slate-600 border-slate-300',
};

interface ProductClassifierProps {
  passportId?: string;
  passport?: InnovationPassport | null;
}

export function ProductClassifier({ passportId, passport }: ProductClassifierProps) {
  const [form, setForm] = useState({
    product_form: (passport?.product_form || '').split(' (')[0] || '',
    dosage_form: passport?.dosage_form || '',
    intended_use: passport?.intended_use || '',
    claims: (passport?.proposed_claims || []).join('\n'),
    ingredients: (passport?.ingredients || []).map((i) => i.raw_name).join(', '),
    process_description: passport?.process_description || '',
  });
  const [result, setResult] = useState<ProductClassifierResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (passport) {
      setForm({
        product_form: (passport.product_form || '').split(' (')[0] || '',
        dosage_form: passport.dosage_form || '',
        intended_use: passport.intended_use || '',
        claims: (passport.proposed_claims || []).join('\n'),
        ingredients: (passport.ingredients || []).map((i) => i.raw_name).join(', '),
        process_description: passport.process_description || '',
      });
    }
  }, [passport]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const run = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await classifyProduct({
        passport_id: passportId || undefined,
        product_form: form.product_form,
        dosage_form: form.dosage_form,
        intended_use: form.intended_use,
        claims: form.claims.split('\n').map((s) => s.trim()).filter(Boolean),
        ingredients: form.ingredients.split(',').map((s) => s.trim()).filter(Boolean),
        process_description: form.process_description,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || 'Classification failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [passportId, form]);

  const inputCls = 'w-full px-4 py-2.5 bg-emerald-50/50 border border-emerald-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:border-emerald-500';

  return (
    <div className="space-y-4">
      <GlassCard padding="md">
        <div className="flex items-center gap-2 mb-1">
          <FlaskConical className="w-5 h-5 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900 font-display">Product Classifier</h3>
          <Badge variant="info" className="ml-auto">FSSAI Aahara · D&amp;C 1940 aware</Badge>
        </div>
        <p className="text-xs text-slate-500">Proposes the likely regulatory class (ASU drug / Ayurveda Aahara / health supplement / cosmetic) from the declared product facts and why.</p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <div>
            <label className="text-xs text-slate-500 mb-1.5 block">Product form / dosage form</label>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <input value={form.product_form} onChange={set('product_form')} placeholder="Tablet / Vati / Churna / Kwatha / Taila / Capsule" className={inputCls} />
              <input value={form.dosage_form} onChange={set('dosage_form')} placeholder="e.g. 500mg twice daily" className={inputCls} />
            </div>
            <label className="text-xs text-slate-500 mb-1.5 block">Intended use</label>
            <input value={form.intended_use} onChange={set('intended_use')} placeholder="e.g. daily digestion wellness" className={`${inputCls} mb-3`} />
            <label className="text-xs text-slate-500 mb-1.5 block">Process description</label>
            <input value={form.process_description} onChange={set('process_description')} placeholder="e.g. Classical aqueous decoction (Kwatha)" className={inputCls} />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1.5 block">Proposed label claims (one per line)</label>
            <textarea value={form.claims} onChange={set('claims')} rows={3} placeholder={'Supports healthy sleep\nPromotes mental relaxation'} className={`${inputCls} mb-3`} />
            <label className="text-xs text-slate-500 mb-1.5 block">Ingredients (comma separated)</label>
            <input value={form.ingredients} onChange={set('ingredients')} placeholder="Ashwagandha, Brahmi" className={inputCls} />
          </div>
        </div>

        <Button variant="primary" className="w-full mt-4" onClick={run} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
          {loading ? 'Classifying…' : 'Run Product Classification'}
        </Button>
        {passportId && (
          <p className="mt-2 text-[11px] text-slate-500">
            Linked passport <code className="font-mono">{passportId}</code> — inputs are prefilled; leave blank to classify strictly from the passport.
          </p>
        )}
      </GlassCard>

      {error && (
        <GlassCard padding="sm" className="border-red-300">
          <div className="flex items-center gap-2 text-xs text-red-700"><AlertTriangle className="w-4 h-4" /> {error}</div>
        </GlassCard>
      )}

      {result && (
        <>
          <GlassCard padding="sm" className="border-emerald-300">
            <div className="flex flex-wrap items-center gap-3">
              <FlaskConical className="w-6 h-6 text-emerald-600" />
              <div className="flex-1 min-w-[200px]">
                <div className="text-[11px] text-slate-500 uppercase tracking-wider">Likely regulatory pathway</div>
                <div className="text-base font-bold text-slate-900 font-display">{result.likely_pathway}</div>
              </div>
              <span className={`px-3 py-1.5 rounded-xl text-xs font-bold border ${pathColor[result.pathway_category] || pathColor.unresolved}`}>{result.pathway_category.replace(/_/g, ' ')}</span>
              <Badge variant={confBadge[result.pathway_confidence] || 'warning'} dot>Confidence {result.pathway_confidence}</Badge>
            </div>
          </GlassCard>

          <GlassCard padding="md">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Sparkles className="w-4 h-4 text-violet-600" /> Why this pathway</h3>
            <ul className="space-y-1.5">
              {result.reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-600"><ArrowRight className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 mt-0.5" /> {r}</li>
              ))}
            </ul>

            {result.alternative_pathways.length > 1 && (
              <div className="mt-4">
                <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Alternative pathways scored</div>
                <div className="space-y-2">
                  {result.alternative_pathways.map((a, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="w-44 flex-shrink-0 text-[11px] text-slate-600 capitalize">{a.pathway.replace(/_/g, ' ')}</span>
                      <div className="h-2 flex-1 rounded-full bg-slate-100 overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-emerald-500 to-teal-400" style={{ width: `${Math.min(100, a.score)}%` }} />
                      </div>
                      <span className="text-[11px] font-mono text-slate-500 w-8 text-right">{a.score}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </GlassCard>

          <GlassCard padding="md">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Landmark className="w-4 h-4 text-blue-600" /> Applicable authority</h3>
            <p className="text-xs text-slate-700 mb-1">{result.applicable_authority}</p>
            <div className="flex flex-wrap gap-1 mb-3">
              {result.applicable_sources.map((s, i) => <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">{s}</span>)}
            </div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5"><FileText className="w-3.5 h-3.5" /> Next actions</h4>
            <ul className="space-y-1.5">
              {result.next_actions.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-600"><BadgeCheck className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" /> {a}</li>
              ))}
            </ul>
          </GlassCard>

          <p className="text-[10px] text-slate-400 italic px-1">{result.disclaimer}</p>
        </>
      )}
    </div>
  );
}