'use client';
import React, { useState, useCallback, useEffect } from 'react';
import {
  FlaskConical, Loader2, ArrowRight, AlertTriangle, Sparkles, Landmark,
  FileText, BadgeCheck, Layers, ChevronLeft, GitBranch, CheckCircle2, Wand2,
  ScrollText, ShieldCheck, Target, Activity,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { classifyProduct, checkABS } from '../lib/api';
import { ProductClassifierResponse, ABSComplianceResponse } from '../types';
import { InnovationPassport } from '../types';

const confBadge: Record<string, 'success' | 'warning' | 'danger'> = {
  HIGH: 'success',
  MEDIUM: 'warning',
  LOW: 'danger',
};

const riskMeta: Record<string, { color: string; label: string }> = {
  LOW: { color: 'bg-emerald-100 text-emerald-700 border-emerald-300', label: 'LOW RISK' },
  MODERATE: { color: 'bg-amber-100 text-amber-700 border-amber-300', label: 'MODERATE RISK' },
  HIGH: { color: 'bg-red-100 text-red-700 border-red-300', label: 'HIGH RISK' },
};

const ruleStatusMeta: Record<string, { badge: 'success' | 'warning' | 'danger' | 'info'; chip: string }> = {
  SATISFIED: { badge: 'success', chip: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
  INSUFFICIENT: { badge: 'warning', chip: 'bg-amber-100 text-amber-700 border-amber-300' },
  NOT_SATISFIED: { badge: 'danger', chip: 'bg-red-100 text-red-700 border-red-300' },
};

const pathColor: Record<string, string> = {
  classical_medicine: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  ayurvedic_drug: 'bg-red-100 text-red-700 border-red-300',
  proprietary_ayurveda: 'bg-orange-100 text-orange-700 border-orange-300',
  new_drug: 'bg-red-100 text-red-700 border-red-300',
  phytopharmaceutical: 'bg-cyan-100 text-cyan-700 border-cyan-300',
  ayurveda_aahara: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  cosmetic: 'bg-pink-100 text-pink-700 border-pink-300',
  nutraceutical: 'bg-violet-100 text-violet-700 border-violet-300',
  unresolved: 'bg-slate-100 text-slate-600 border-slate-300',
};

const PATH_LABEL: Record<string, string> = {
  classical_medicine: 'Classical Medicine',
  ayurvedic_drug: 'Ayurvedic Drug',
  proprietary_ayurveda: 'Patent & Proprietary Ayurveda',
  new_drug: 'New Drug',
  phytopharmaceutical: 'Phytopharmaceutical',
  ayurveda_aahara: 'Ayurveda Aahar',
  cosmetic: 'Cosmetic',
  nutraceutical: 'Nutraceutical / Supplement',
  unresolved: 'Unresolved',
};

interface WizardStepOption {
  label: string;
  hint?: string;
  value: Record<string, any>;
}

interface WizardStep {
  q: string;
  help: string;
  options: WizardStepOption[];
}

const WIZARD_STEPS: WizardStep[] = [
  {
    q: 'Is your formulation based on a classical text reference from the First Schedule?',
    help: 'First Schedule lists formulations cited in classical authoritative texts (Charaka, Sushruta, Ayurvedic Pharmacopoeia…).',
    options: [
      { label: 'Yes — classical First Schedule formulation', hint: 'Matches a classical text reference', value: { first_schedule: true } },
      { label: 'No — my own combination', hint: 'Not found in First Schedule texts', value: { first_schedule: false } },
      { label: 'I am not sure', hint: 'Treated as unconfirmed', value: { first_schedule: null } },
    ],
  },
  {
    q: 'Does the formulation contain an ingredient NOT listed in the First Schedule?',
    help: 'An ingredient with no First Schedule/classical reference is legally “new” material.',
    options: [
      { label: 'Yes — a novel ingredient', hint: 'Candidate for New Drug classification', value: { new_ingredient: true } },
      { label: 'No — all ingredients are known & scheduled', value: { new_ingredient: false } },
      { label: 'Not sure', value: { new_ingredient: null } },
    ],
  },
  {
    q: 'What is the primary intended use?',
    help: 'Curative wording is what separates a drug from food or cosmetic in the D&C Act and FSSAI schemes.',
    options: [
      { label: 'Therapeutic / medicinal use', hint: 'Treats or manages a condition', value: { declared_use: 'medicine' } },
      { label: 'Wellness / supplement', hint: 'Structure-function support', value: { declared_use: 'wellness' } },
      { label: 'Daily dietary food (Aahar)', hint: 'Nutrition, daily intake', value: { declared_use: 'dietary' } },
      { label: 'Cosmetic skin / hair care', hint: 'Topical appearance care', value: { declared_use: 'cosmetic' } },
    ],
  },
  {
    q: 'How is it extracted / manufactured?',
    help: 'Classical processing keeps a formulation inside the traditional frame; advanced extraction can push it toward a Phytopharmaceutical.',
    options: [
      { label: 'Classical method (Kwatha / traditional)', hint: 'Aqueous decoction, classical form', value: { extraction_method: 'classical', novel_process: false } },
      { label: 'Standardised / titrated extract', hint: 'Quantified markers, purified actives', value: { extraction_method: 'standardised', novel_process: true } },
      { label: 'Supercritical-CO2 / solvent extraction', hint: 'Advanced non-classical extraction', value: { extraction_method: 'supercritical', novel_process: true } },
      { label: 'Enzyme / fermentation / ultrasound / membrane', hint: 'Biotech-assisted processing', value: { extraction_method: 'enzyme', novel_process: true } },
    ],
  },
];

interface ProductClassifierProps {
  passportId?: string;
  passport?: InnovationPassport | null;
}

const ABS_USER_TYPES: { id: string; label: string }[] = [
  { id: 'registered_ayush_practitioner', label: 'Registered AYUSH practitioner' },
  { id: 'researcher', label: 'Researcher / academic' },
  { id: 'msme', label: 'MSME / small business' },
  { id: 'startup', label: 'Startup' },
  { id: 'company', label: 'Company / corporate' },
  { id: 'individual', label: 'Individual' },
];

const absStatusChip: Record<string, string> = {
  exempt: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  compliance_required: 'bg-amber-100 text-amber-700 border-amber-300',
  info_required: 'bg-red-100 text-red-700 border-red-300',
  not_applicable: 'bg-slate-100 text-slate-600 border-slate-300',
};

export function ABSCalculator({ passportId, ingredients }: { passportId?: string; ingredients?: string[] }) {
  const [userType, setUserType] = useState('company');
  const [turnover, setTurnover] = useState('');
  const [wildCollected, setWildCollected] = useState(false);
  const [commercial, setCommercial] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ABSComplianceResponse | null>(null);
  const [error, setError] = useState('');

  const run = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const turnoverNum = turnover.trim() ? Number(turnover) : undefined;
      const res = await checkABS({
        passport_id: passportId || undefined,
        ingredients: ingredients && ingredients.length ? ingredients : undefined,
        user_type: userType,
        turnover_inr: turnoverNum,
        wild_collected: wildCollected,
        commercial_use: commercial,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || 'ABS check failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [passportId, ingredients, userType, turnover, wildCollected, commercial]);

  const inputCls = 'w-full px-3 py-2 bg-emerald-50/50 border border-emerald-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:border-emerald-500';

  return (
    <GlassCard padding="md">
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <ShieldCheck className="w-5 h-5 text-emerald-600" />
        <h3 className="text-sm font-bold text-slate-900 font-display">ABS Compliance Helper</h3>
        <Badge variant="info" className="ml-auto">BDA 2002 · Rules 2024 · NBA</Badge>
      </div>
      <p className="text-xs text-slate-500 mb-3">Access & Benefit Sharing position: turnovers, user type and wild-collection drive Rule 14(2) exemption and NBA obligations.</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 mb-3">
        <div>
          <label className="text-[11px] text-slate-500 mb-1 block">User type</label>
          <select value={userType} onChange={(e) => setUserType(e.target.value)} className={inputCls}>
            {ABS_USER_TYPES.map((u) => <option key={u.id} value={u.id}>{u.label}</option>)}
          </select>
        </div>
        <div>
          <label className="text-[11px] text-slate-500 mb-1 block">Turnover (₹, optional)</label>
          <input value={turnover} onChange={(e) => setTurnover(e.target.value.replace(/[^\d]/g, ''))} placeholder="e.g. 50000000" className={inputCls} />
        </div>
        <div className="flex items-end gap-2">
          <label className="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer">
            <input type="checkbox" checked={wildCollected} onChange={(e) => setWildCollected(e.target.checked)} className="accent-emerald-600" />
            Wild-collected
          </label>
          <label className="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer">
            <input type="checkbox" checked={commercial} onChange={(e) => setCommercial(e.target.checked)} className="accent-emerald-600" />
            Commercial use
          </label>
        </div>
        <Button variant="primary" className="w-full" onClick={run} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
          Check ABS
        </Button>
      </div>

      {error && <div className="flex items-center gap-2 text-xs text-red-700 mb-2"><AlertTriangle className="w-4 h-4" /> {error}</div>}

      {result && (
        <div className="space-y-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-[10px] font-bold border ${absStatusChip[result.status] || absStatusChip.not_applicable}`}>{result.status.replace(/_/g, ' ').toUpperCase()}</span>
            {result.status === 'exempt' && <span className="text-[10px] text-emerald-700 font-semibold">{result.exemption_reason}</span>}
          </div>

          {result.benefit_sharing.applicable && (
            <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-2.5 flex items-center gap-2 flex-wrap">
              <BadgeCheck className="w-4 h-4 text-emerald-600" />
              <span className="text-[11px] font-bold text-emerald-800">Benefit-sharing</span>
              <span className="text-[11px] text-emerald-700">{result.benefit_sharing.slab} @ {result.benefit_sharing.rate_pct}%</span>
              {result.benefit_sharing.amount_inr !== null && result.benefit_sharing.amount_inr !== undefined && (
                <span className="text-[11px] text-emerald-800 font-mono">≈ ₹{result.benefit_sharing.amount_inr.toLocaleString('en-IN')}</span>
              )}
            </div>
          )}

          {result.required_approvals.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-2.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-amber-700 mb-1">Required approvals</div>
              <ul className="space-y-1">
                {result.required_approvals.map((a, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[11px] text-slate-700"><AlertTriangle className="w-3 h-3 text-amber-600 flex-shrink-0 mt-0.5" /> {a}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-1.5">
            {result.obligations.map((o, i) => (
              <div key={i} className="flex items-start gap-2 text-[11px] text-slate-600">
                <ScrollText className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-slate-700">{o.obligation}</div>
                  <div className="text-[9px] text-blue-700 mt-0.5">{o.citation}</div>
                </div>
              </div>
            ))}
          </div>

          <p className="text-[9px] text-slate-400 italic">{result.disclaimer}</p>
        </div>
      )}
    </GlassCard>
  );
}

type Mode = 'wizard' | 'manual';

export function ProductClassifier({ passportId, passport }: ProductClassifierProps) {
  const [mode, setMode] = useState<Mode>('wizard');
  const [step, setStep] = useState(0);
  const [wizAnswers, setWizAnswers] = useState<Record<string, any>>({});
  const [form, setForm] = useState({
    product_name: passport?.case_title || '',
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
        product_name: passport.case_title || '',
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

  const pickOption = (option: WizardStepOption) => {
    setWizAnswers((prev) => ({ ...prev, ...option.value }));
    if (step < WIZARD_STEPS.length - 1) {
      setStep((s) => s + 1);
      setResult(null);
    } else {
      setResult(null);
    }
  };

  const run = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await classifyProduct({
        passport_id: passportId || undefined,
        product_name: form.product_name,
        product_form: form.product_form,
        dosage_form: form.dosage_form,
        intended_use: form.intended_use,
        claims: form.claims.split('\n').map((s) => s.trim()).filter(Boolean),
        ingredients: form.ingredients.split(',').map((s) => s.trim()).filter(Boolean),
        process_description: form.process_description,
        ...wizAnswers,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || 'Classification failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [passportId, form, wizAnswers]);

  const inputCls = 'w-full px-4 py-2.5 bg-emerald-50/50 border border-emerald-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:border-emerald-500';

  return (
    <div className="space-y-4">
      <GlassCard padding="md">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <FlaskConical className="w-5 h-5 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900 font-display">Formulation Classification Wizard</h3>
          <Badge variant="info" className="ml-auto">7-step · RAG + Rule Engine</Badge>
        </div>

        <div className="flex items-center gap-1.5 mb-3 flex-wrap">
          <button
            type="button"
            onClick={() => setMode('wizard')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold border transition ${mode === 'wizard' ? 'bg-violet-600 border-violet-600 text-white' : 'bg-white border-slate-200 text-slate-500 hover:border-violet-400'}`}
          >
            <Wand2 className="w-3 h-3" /> Step-by-step Wizard
          </button>
          <button
            type="button"
            onClick={() => setMode('manual')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold border transition ${mode === 'manual' ? 'bg-violet-600 border-violet-600 text-white' : 'bg-white border-slate-200 text-slate-500 hover:border-violet-400'}`}
          >
            <Layers className="w-3 h-3" /> Manual entry
          </button>
        </div>

        {mode === 'wizard' && (
          <div className="mb-4 rounded-xl border border-violet-200 bg-violet-50/60 p-4">
            <div className="flex items-center gap-1.5 mb-3">
              {WIZARD_STEPS.map((s, i) => (
                <div key={i} className="flex items-center gap-1.5 flex-1 last:flex-none">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${i < step || (i === step && WIZARD_STEPS[i].options.some((o) => Object.keys(o.value).some((k) => wizAnswers[k] !== undefined))) ? 'bg-violet-600 text-white' : 'bg-white text-slate-400 border border-violet-200'}`}>
                    {i < step || WIZARD_STEPS[i].options.some((o) => Object.keys(o.value).some((k) => wizAnswers[k] !== undefined)) ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
                  </div>
                  <span className={`text-[10px] font-semibold hidden sm:block ${i === step ? 'text-violet-700' : 'text-slate-400'}`}>{s.q.split('?')[0].slice(0, 34)}…</span>
                  {i < WIZARD_STEPS.length - 1 && <div className="h-px flex-1 bg-violet-200" />}
                </div>
              ))}
            </div>

            <div className="text-xs font-bold text-slate-800 mb-1">Step {step + 1} of {WIZARD_STEPS.length}</div>
            <div className="text-sm font-bold text-violet-900 mb-2">{WIZARD_STEPS[step].q}</div>
            <div className="text-[11px] text-slate-500 mb-3">{WIZARD_STEPS[step].help}</div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {WIZARD_STEPS[step].options.map((opt) => {
                const chosen = Object.keys(opt.value).every((k) => wizAnswers[k] === opt.value[k]);
                return (
                  <button
                    key={opt.label}
                    type="button"
                    onClick={() => pickOption(opt)}
                    className={`px-3.5 py-3 rounded-xl border text-left transition ${chosen ? 'bg-violet-600 border-violet-600 text-white shadow-sm' : 'bg-white border-slate-200 text-slate-600 hover:border-violet-400'}`}
                  >
                    <div className="text-[11px] font-bold leading-snug">{opt.label}</div>
                    {opt.hint && <div className={`text-[10px] mt-0.5 ${chosen ? 'text-white/80' : 'text-slate-400'}`}>{opt.hint}</div>}
                  </button>
                );
              })}
            </div>

            {step > 0 && (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                className="mt-3 inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500 hover:text-violet-700 transition"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Back to previous step
              </button>
            )}
          </div>
        )}

        <p className="text-xs text-slate-500">
          {mode === 'wizard'
            ? 'Answer the 4 classification questions, then confirm the product facts below and run the classification.'
            : 'Proposes the likely regulatory class (ASU drug / Ayurveda Aahar / health supplement / cosmetic / new drug / phytopharmaceutical) from the declared product facts and why.'}
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <div>
            <label className="text-xs text-slate-500 mb-1.5 block">Product name</label>
            <input value={form.product_name} onChange={set('product_name')} placeholder="e.g. Ashwagandha + Guduchi Capsule" className={`${inputCls} mb-3`} />
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

      <ABSCalculator passportId={passportId} />

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
                <div className="text-[11px] text-slate-500 uppercase tracking-wider">Step 6 · Final classification {result.classification_mode === 'wizard_based' && <span className="text-violet-500 normal-case">· wizard classified</span>}</div>
                <div className="text-base font-bold text-slate-900 font-display">{result.likely_pathway}</div>
              </div>
              <span className={`px-3 py-1.5 rounded-xl text-xs font-bold border ${pathColor[result.pathway_category] || pathColor.unresolved}`}>{PATH_LABEL[result.pathway_category] || result.pathway_category.replace(/_/g, ' ')}</span>
              <Badge variant={confBadge[result.pathway_confidence] || 'warning'} dot>Confidence {result.pathway_confidence}</Badge>
              <span className={`px-3 py-1.5 rounded-xl text-[10px] font-bold border ${riskMeta[result.risk_level]?.color || riskMeta.MODERATE.color}`}>{riskMeta[result.risk_level]?.label || 'MODERATE RISK'}</span>
            </div>
            {result.intent_detected && (
              <div className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-500">
                <Target className="w-3.5 h-3.5 text-violet-500" />
                Step 3 · Intent detected: <span className="font-bold text-slate-700">{result.intent_detected}</span>
              </div>
            )}
          </GlassCard>

          {result.decision_path && result.decision_path.length > 0 && (
            <GlassCard padding="md">
              <button
                type="button"
                className="flex items-center gap-2 text-sm font-bold text-slate-900 font-display mb-2"
                onClick={(e) => { (e.currentTarget.parentElement as HTMLElement).querySelector('.trace-body')?.classList.toggle('hidden'); }}
              >
                <GitBranch className="w-4 h-4 text-blue-600" /> How was this classified?
                <ChevronLeft className="w-4 h-4 text-slate-400 ml-auto rotate-90" />
              </button>
              <div className="trace-body">
                <div className="rounded-lg bg-[#0D1425] px-3 py-2.5 space-y-1.5 mt-1">
                  {result.decision_path.map((line, i) => (
                    <div key={i} className="flex items-start gap-2 text-[10px] text-slate-300">
                      <BadgeCheck className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                      <span>{line}</span>
                    </div>
                  ))}
                </div>
              </div>
            </GlassCard>
          )}

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
                      <span className="w-44 flex-shrink-0 text-[11px] text-slate-600 capitalize">{PATH_LABEL[a.pathway] || a.pathway.replace(/_/g, ' ')}</span>
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
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-600" /> Step 5 · Rule Engine Validation</h3>
            <div className="space-y-2.5">
              {result.rule_validation.map((c, i) => (
                <div key={i} className="rounded-lg border border-slate-100 bg-slate-50/50 p-2.5 flex items-start gap-2.5">
                  <span className={`mt-0.5 px-2 py-0.5 rounded-full text-[9px] font-bold border flex-shrink-0 ${ruleStatusMeta[c.status]?.chip || 'bg-slate-100 text-slate-600 border-slate-300'}`}>{c.verdict}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-bold text-slate-800">{c.rule}</div>
                    <p className="text-[10px] text-slate-500 mt-0.5 leading-snug">{c.reason}</p>
                    <div className="text-[9px] text-blue-700 mt-1 font-medium">{c.source}</div>
                  </div>
                </div>
              ))}
              {(!result.rule_validation || result.rule_validation.length === 0) && (
                <p className="text-[11px] text-slate-500">No rule checks returned for this classification.</p>
              )}
            </div>
          </GlassCard>

          <GlassCard padding="md">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><ScrollText className="w-4 h-4 text-blue-600" /> Step 4 · RAG Retrieval — Official Evidence</h3>
            {result.evidence && result.evidence.length > 0 ? (
              <div className="space-y-2.5">
                {result.evidence.map((ev, i) => (
                  <div key={i} className="rounded-lg border border-slate-100 bg-slate-50/50 p-2.5">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {ev.collection && <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold border bg-blue-50 text-blue-700 border-blue-200 uppercase tracking-wide">{ev.collection}</span>}
                      <div className="text-[11px] font-bold text-slate-800 flex-1 min-w-0 truncate">{ev.title}</div>
                    </div>
                    {ev.passage && <p className="text-[10px] text-slate-500 mt-1 leading-snug line-clamp-3">{ev.passage}</p>}
                    <div className="flex items-center justify-between gap-2 mt-1">
                      <div className="text-[9px] text-blue-700 font-medium truncate">{ev.source}</div>
                      {ev.authority && <div className="text-[9px] text-slate-400 flex-shrink-0">{ev.authority}</div>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-slate-500">RAG retrieval returned no passages (retrieval service offline / index cold). Rule-based classification still applies.</p>
            )}
          </GlassCard>

          <GlassCard padding="md">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Landmark className="w-4 h-4 text-blue-600" /> Applicable authority</h3>
            <p className="text-xs text-slate-700 mb-1">{result.applicable_authority}</p>
            <div className="flex flex-wrap gap-1 mb-3">
              {result.applicable_sources.map((s, i) => <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">{s}</span>)}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
              <div className="rounded-lg border border-violet-100 bg-violet-50/50 p-2.5">
                <div className="text-[9px] font-bold uppercase tracking-wider text-violet-600 mb-0.5 flex items-center gap-1"><Landmark className="w-3 h-3" /> Regulatory pathway</div>
                <div className="text-[10px] text-slate-700 leading-snug">{result.regulatory_pathway}</div>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-indigo-50/50 p-2.5">
                <div className="text-[9px] font-bold uppercase tracking-wider text-indigo-600 mb-0.5 flex items-center gap-1"><FileText className="w-3 h-3" /> IP readiness</div>
                <div className="text-[10px] text-slate-700 leading-snug">{result.ip_readiness}</div>
              </div>
              <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-2.5">
                <div className="text-[9px] font-bold uppercase tracking-wider text-emerald-600 mb-0.5 flex items-center gap-1"><BadgeCheck className="w-3 h-3" /> ABS status</div>
                <div className="text-[10px] text-slate-700 leading-snug">{result.abs_status}</div>
              </div>
              <div className="rounded-lg border border-amber-100 bg-amber-50/50 p-2.5">
                <div className="text-[9px] font-bold uppercase tracking-wider text-amber-600 mb-0.5 flex items-center gap-1"><Activity className="w-3 h-3" /> Risk level</div>
                <div className="text-[10px] text-slate-800 font-bold">{result.risk_level}</div>
              </div>
            </div>

            <div className="rounded-lg border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50 p-3 mb-3">
              <div className="text-[9px] font-bold uppercase tracking-wider text-emerald-700 mb-1 flex items-center gap-1"><Sparkles className="w-3 h-3" /> Recommended next step</div>
              <div className="text-[11px] font-semibold text-slate-800 leading-snug">{result.recommended_next_step}</div>
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