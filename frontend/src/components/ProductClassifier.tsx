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
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

const confBadge: Record<string, 'success' | 'warning' | 'danger'> = {
  HIGH: 'success',
  MEDIUM: 'warning',
  LOW: 'danger',
};

const riskMeta: Record<string, { color: string; labelKey: string }> = {
  LOW: { color: 'bg-emerald-100 text-emerald-700 border-emerald-300', labelKey: 'pc_risk_low' },
  MODERATE: { color: 'bg-amber-100 text-amber-700 border-amber-300', labelKey: 'pc_risk_moderate' },
  HIGH: { color: 'bg-red-100 text-red-700 border-red-300', labelKey: 'pc_risk_high' },
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

const PATH_LABEL_KEY: Record<string, string> = {
  classical_medicine: 'pc_path_classical',
  ayurvedic_drug: 'pc_path_ayurvedic_drug',
  proprietary_ayurveda: 'pc_path_proprietary',
  new_drug: 'pc_path_new_drug',
  phytopharmaceutical: 'pc_path_phytopharmaceutical',
  ayurveda_aahara: 'pc_path_aahara',
  cosmetic: 'pc_path_cosmetic',
  nutraceutical: 'pc_path_nutraceutical',
  unresolved: 'pc_path_unresolved',
};

interface WizardStepOption {
  labelKey: string;
  hintKey?: string;
  value: Record<string, any>;
}

interface WizardStep {
  qKey: string;
  helpKey: string;
  options: WizardStepOption[];
}

const WIZARD_STEPS: WizardStep[] = [
  {
    qKey: 'pc_w1_q',
    helpKey: 'pc_w1_help',
    options: [
      { labelKey: 'pc_w1_o1', hintKey: 'pc_w1_o1_h', value: { first_schedule: true } },
      { labelKey: 'pc_w1_o2', hintKey: 'pc_w1_o2_h', value: { first_schedule: false } },
      { labelKey: 'pc_w1_o3', hintKey: 'pc_w1_o3_h', value: { first_schedule: null } },
    ],
  },
  {
    qKey: 'pc_w2_q',
    helpKey: 'pc_w2_help',
    options: [
      { labelKey: 'pc_w2_o1', hintKey: 'pc_w2_o1_h', value: { new_ingredient: true } },
      { labelKey: 'pc_w2_o2', value: { new_ingredient: false } },
      { labelKey: 'pc_w2_o3', value: { new_ingredient: null } },
    ],
  },
  {
    qKey: 'pc_w3_q',
    helpKey: 'pc_w3_help',
    options: [
      { labelKey: 'pc_w3_o1', hintKey: 'pc_w3_o1_h', value: { declared_use: 'medicine' } },
      { labelKey: 'pc_w3_o2', hintKey: 'pc_w3_o2_h', value: { declared_use: 'wellness' } },
      { labelKey: 'pc_w3_o3', hintKey: 'pc_w3_o3_h', value: { declared_use: 'dietary' } },
      { labelKey: 'pc_w3_o4', hintKey: 'pc_w3_o4_h', value: { declared_use: 'cosmetic' } },
    ],
  },
  {
    qKey: 'pc_w4_q',
    helpKey: 'pc_w4_help',
    options: [
      { labelKey: 'pc_w4_o1', hintKey: 'pc_w4_o1_h', value: { extraction_method: 'classical', novel_process: false } },
      { labelKey: 'pc_w4_o2', hintKey: 'pc_w4_o2_h', value: { extraction_method: 'standardised', novel_process: true } },
      { labelKey: 'pc_w4_o3', hintKey: 'pc_w4_o3_h', value: { extraction_method: 'supercritical', novel_process: true } },
      { labelKey: 'pc_w4_o4', hintKey: 'pc_w4_o4_h', value: { extraction_method: 'enzyme', novel_process: true } },
    ],
  },
];

interface ProductClassifierProps {
  passportId?: string;
  passport?: InnovationPassport | null;
}

const ABS_USER_TYPES: { id: string; labelKey: string }[] = [
  { id: 'registered_ayush_practitioner', labelKey: 'abs_user_practitioner' },
  { id: 'researcher', labelKey: 'abs_user_researcher' },
  { id: 'msme', labelKey: 'abs_user_msme' },
  { id: 'startup', labelKey: 'abs_user_startup' },
  { id: 'company', labelKey: 'abs_user_company' },
  { id: 'individual', labelKey: 'abs_user_individual' },
];

const absStatusChip: Record<string, string> = {
  exempt: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  compliance_required: 'bg-amber-100 text-amber-700 border-amber-300',
  info_required: 'bg-red-100 text-red-700 border-red-300',
  not_applicable: 'bg-slate-100 text-slate-600 border-slate-300',
};

export function ABSCalculator({ passportId, ingredients }: { passportId?: string; ingredients?: string[] }) {
  const { lang } = useLang();
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
      setError(e.message || t('pc_abs_failed', lang));
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
        <h3 className="text-sm font-bold text-slate-900 font-display">{t('abs_compliance_helper', lang)}</h3>
        <Badge variant="info" className="ml-auto">{t('abs_badge', lang)}</Badge>
      </div>
      <p className="text-xs text-slate-500 mb-3">{t('abs_subtitle', lang)}</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 mb-3">
        <div>
          <label className="text-[11px] text-slate-500 mb-1 block">{t('pc_user_type', lang)}</label>
          <select value={userType} onChange={(e) => setUserType(e.target.value)} className={inputCls}>
            {ABS_USER_TYPES.map((u) => <option key={u.id} value={u.id}>{t(u.labelKey, lang)}</option>)}
          </select>
        </div>
        <div>
          <label className="text-[11px] text-slate-500 mb-1 block">{t('pc_turnover', lang)}</label>
          <input value={turnover} onChange={(e) => setTurnover(e.target.value.replace(/[^\d]/g, ''))} placeholder="e.g. 50000000" className={inputCls} />
        </div>
        <div className="flex items-end gap-2">
          <label className="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer">
            <input type="checkbox" checked={wildCollected} onChange={(e) => setWildCollected(e.target.checked)} className="accent-emerald-600" />
            {t('pc_wild_collected', lang)}
          </label>
          <label className="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer">
            <input type="checkbox" checked={commercial} onChange={(e) => setCommercial(e.target.checked)} className="accent-emerald-600" />
            {t('pc_commercial_use', lang)}
          </label>
        </div>
        <Button variant="primary" className="w-full" onClick={run} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
          {t('abs_check_btn', lang)}
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
              <span className="text-[11px] font-bold text-emerald-800">{t('abs_benefit_sharing', lang)}</span>
              <span className="text-[11px] text-emerald-700">{result.benefit_sharing.slab} @ {result.benefit_sharing.rate_pct}%</span>
              {result.benefit_sharing.amount_inr !== null && result.benefit_sharing.amount_inr !== undefined && (
                <span className="text-[11px] text-emerald-800 font-mono">≈ ₹{result.benefit_sharing.amount_inr.toLocaleString('en-IN')}</span>
              )}
            </div>
          )}

          {result.required_approvals.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-2.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-amber-700 mb-1">{t('abs_required_approvals', lang)}</div>
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
  const { lang } = useLang();
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
      setError(e.message || t('pc_classify_failed', lang));
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
          <h3 className="text-sm font-bold text-slate-900 font-display">{t('pc_title', lang)}</h3>
          <Badge variant="info" className="ml-auto">{t('pc_badge', lang)}</Badge>
        </div>

        <div className="flex items-center gap-1.5 mb-3 flex-wrap">
          <button
            type="button"
            onClick={() => setMode('wizard')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold border transition ${mode === 'wizard' ? 'bg-violet-600 border-violet-600 text-white' : 'bg-white border-slate-200 text-slate-500 hover:border-violet-400'}`}
          >
            <Wand2 className="w-3 h-3" /> {t('pc_mode_wizard', lang)}
          </button>
          <button
            type="button"
            onClick={() => setMode('manual')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold border transition ${mode === 'manual' ? 'bg-violet-600 border-violet-600 text-white' : 'bg-white border-slate-200 text-slate-500 hover:border-violet-400'}`}
          >
            <Layers className="w-3 h-3" /> {t('pc_mode_manual', lang)}
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
                  <span className={`text-[10px] font-semibold hidden sm:block ${i === step ? 'text-violet-700' : 'text-slate-400'}`}>{t('pc_step_short', lang)} {i + 1}</span>
                  {i < WIZARD_STEPS.length - 1 && <div className="h-px flex-1 bg-violet-200" />}
                </div>
              ))}
            </div>

            <div className="text-xs font-bold text-slate-800 mb-1">{t('pc_step_of', lang).replace('{a}', String(step + 1)).replace('{b}', String(WIZARD_STEPS.length))}</div>
            <div className="text-sm font-bold text-violet-900 mb-2">{t(WIZARD_STEPS[step].qKey, lang)}</div>
            <div className="text-[11px] text-slate-500 mb-3">{t(WIZARD_STEPS[step].helpKey, lang)}</div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {WIZARD_STEPS[step].options.map((opt) => {
                const chosen = Object.keys(opt.value).every((k) => wizAnswers[k] === opt.value[k]);
                return (
                  <button
                    key={opt.labelKey}
                    type="button"
                    onClick={() => pickOption(opt)}
                    className={`px-3.5 py-3 rounded-xl border text-left transition ${chosen ? 'bg-violet-600 border-violet-600 text-white shadow-sm' : 'bg-white border-slate-200 text-slate-600 hover:border-violet-400'}`}
                  >
                    <div className="text-[11px] font-bold leading-snug">{t(opt.labelKey, lang)}</div>
                    {opt.hintKey && <div className={`text-[10px] mt-0.5 ${chosen ? 'text-white/80' : 'text-slate-400'}`}>{t(opt.hintKey, lang)}</div>}
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
                <ChevronLeft className="w-3.5 h-3.5" /> {t('pc_back', lang)}
              </button>
            )}
          </div>
        )}

        <p className="text-xs text-slate-500">
          {mode === 'wizard' ? t('pc_help_wizard', lang) : t('pc_help_manual', lang)}
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <div>
            <label className="text-xs text-slate-500 mb-1.5 block">{t('pc_lbl_product_name', lang)}</label>
            <input value={form.product_name} onChange={set('product_name')} placeholder={t('pc_ph_product_name', lang)} className={`${inputCls} mb-3`} />
            <label className="text-xs text-slate-500 mb-1.5 block">{t('pc_lbl_product_form', lang)}</label>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <input value={form.product_form} onChange={set('product_form')} placeholder={t('pc_ph_product_form', lang)} className={inputCls} />
              <input value={form.dosage_form} onChange={set('dosage_form')} placeholder={t('pc_ph_dosage_form', lang)} className={inputCls} />
            </div>
            <label className="text-xs text-slate-500 mb-1.5 block">{t('pc_lbl_intended_use', lang)}</label>
            <input value={form.intended_use} onChange={set('intended_use')} placeholder={t('pc_ph_intended_use', lang)} className={`${inputCls} mb-3`} />
            <label className="text-xs text-slate-500 mb-1.5 block">{t('pc_lbl_process', lang)}</label>
            <input value={form.process_description} onChange={set('process_description')} placeholder={t('pc_ph_process', lang)} className={inputCls} />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1.5 block">{t('pc_lbl_claims', lang)}</label>
            <textarea value={form.claims} onChange={set('claims')} rows={3} placeholder={t('pc_ph_claims', lang)} className={`${inputCls} mb-3`} />
            <label className="text-xs text-slate-500 mb-1.5 block">{t('pc_lbl_ingredients', lang)}</label>
            <input value={form.ingredients} onChange={set('ingredients')} placeholder={t('pc_ph_ingredients', lang)} className={inputCls} />
          </div>
        </div>

        <Button variant="primary" className="w-full mt-4" onClick={run} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
          {loading ? t('pc_classifying', lang) : t('pc_run_btn', lang)}
        </Button>
        {passportId && (
          <p className="mt-2 text-[11px] text-slate-500">
            {t('pc_linked_passport', lang)} <code className="font-mono">{passportId}</code> — {t('pc_linked_note_cls', lang)}
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
                <div className="text-[11px] text-slate-500 uppercase tracking-wider">{t('pc_step_final', lang)} {result.classification_mode === 'wizard_based' && <span className="text-violet-500 normal-case">· {t('pc_wizard_classified', lang)}</span>}</div>
                <div className="text-base font-bold text-slate-900 font-display">{result.likely_pathway}</div>
              </div>
              <span className={`px-3 py-1.5 rounded-xl text-xs font-bold border ${pathColor[result.pathway_category] || pathColor.unresolved}`}>{t(PATH_LABEL_KEY[result.pathway_category] || 'pc_path_unresolved', lang)}</span>
              <Badge variant={confBadge[result.pathway_confidence] || 'warning'} dot>{t('pc_confidence', lang)} {result.pathway_confidence}</Badge>
              <span className={`px-3 py-1.5 rounded-xl text-[10px] font-bold border ${riskMeta[result.risk_level]?.color || riskMeta.MODERATE.color}`}>{t(riskMeta[result.risk_level]?.labelKey || 'pc_risk_moderate', lang)}</span>
            </div>
            {result.intent_detected && (
              <div className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-500">
                <Target className="w-3.5 h-3.5 text-violet-500" />
                {t('pc_step_intent', lang)} <span className="font-bold text-slate-700">{result.intent_detected}</span>
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
                <GitBranch className="w-4 h-4 text-blue-600" /> {t('pc_how_classified', lang)}
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
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Sparkles className="w-4 h-4 text-violet-600" /> {t('pc_why_pathway', lang)}</h3>
            <ul className="space-y-1.5">
              {result.reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-600"><ArrowRight className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 mt-0.5" /> {r}</li>
              ))}
            </ul>

            {result.alternative_pathways.length > 1 && (
              <div className="mt-4">
                <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">{t('pc_alt_pathways', lang)}</div>
                <div className="space-y-2">
                  {result.alternative_pathways.map((a, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="w-44 flex-shrink-0 text-[11px] text-slate-600 capitalize">{t(PATH_LABEL_KEY[a.pathway] || 'pc_path_unresolved', lang)}</span>
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
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-600" /> {t('pc_step_rule', lang)}</h3>
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
                <p className="text-[11px] text-slate-500">{t('pc_no_rules', lang)}</p>
              )}
            </div>
          </GlassCard>

          <GlassCard padding="md">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><ScrollText className="w-4 h-4 text-blue-600" /> {t('pc_step_rag', lang)}</h3>
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
              <p className="text-[11px] text-slate-500">{t('pc_no_passages', lang)}</p>
            )}
          </GlassCard>

          <GlassCard padding="md">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Landmark className="w-4 h-4 text-blue-600" /> {t('pc_applicable_authority', lang)}</h3>
            <p className="text-xs text-slate-700 mb-1">{result.applicable_authority}</p>
            <div className="flex flex-wrap gap-1 mb-3">
              {result.applicable_sources.map((s, i) => <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">{s}</span>)}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
              <div className="rounded-lg border border-violet-100 bg-violet-50/50 p-2.5">
                <div className="text-[9px] font-bold uppercase tracking-wider text-violet-600 mb-0.5 flex items-center gap-1"><Landmark className="w-3 h-3" /> {t('pc_reg_pathway', lang)}</div>
                <div className="text-[10px] text-slate-700 leading-snug">{result.regulatory_pathway}</div>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-indigo-50/50 p-2.5">
                <div className="text-[9px] font-bold uppercase tracking-wider text-indigo-600 mb-0.5 flex items-center gap-1"><FileText className="w-3 h-3" /> {t('pc_ip_readiness', lang)}</div>
                <div className="text-[10px] text-slate-700 leading-snug">{result.ip_readiness}</div>
              </div>
              <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-2.5">
                <div className="text-[9px] font-bold uppercase tracking-wider text-emerald-600 mb-0.5 flex items-center gap-1"><BadgeCheck className="w-3 h-3" /> {t('pc_abs_status', lang)}</div>
                <div className="text-[10px] text-slate-700 leading-snug">{result.abs_status}</div>
              </div>
              <div className="rounded-lg border border-amber-100 bg-amber-50/50 p-2.5">
                <div className="text-[9px] font-bold uppercase tracking-wider text-amber-600 mb-0.5 flex items-center gap-1"><Activity className="w-3 h-3" /> {t('pc_risk_level', lang)}</div>
                <div className="text-[10px] text-slate-800 font-bold">{result.risk_level}</div>
              </div>
            </div>

            <div className="rounded-lg border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50 p-3 mb-3">
              <div className="text-[9px] font-bold uppercase tracking-wider text-emerald-700 mb-1 flex items-center gap-1"><Sparkles className="w-3 h-3" /> {t('pc_recommended_step', lang)}</div>
              <div className="text-[11px] font-semibold text-slate-800 leading-snug">{result.recommended_next_step}</div>
            </div>

            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5"><FileText className="w-3.5 h-3.5" /> {t('pc_next_actions', lang)}</h4>
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