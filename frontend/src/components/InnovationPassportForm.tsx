'use client';
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Sparkles, Loader2, ChevronRight, ChevronLeft, FlaskConical, Leaf,
  ShieldCheck, Languages, User, ClipboardList, Check, CheckCircle2, FileText,
  AlertTriangle,
} from 'lucide-react';
import { parseFormulation } from '../lib/api';
import { FormulationParseResponse } from '../types';
import { GlassCard } from './ui/GlassCard';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { SelectOrOther } from './ui/SelectOrOther';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface PassportFormProps {
  onSubmit: (data: any) => void;
  isLoading?: boolean;
}

const STEPS = [
  { id: 'basic', icon: User },
  { id: 'formulation', icon: Languages },
  { id: 'process', icon: FlaskConical },
  { id: 'claims', icon: ShieldCheck },
  { id: 'review', icon: ClipboardList },
];

const CLAIM_OPTIONS = [
  { id: 'healthy_skin', label: 'Supports Healthy Skin', risk: 'Low', riskColor: 'success' },
  { id: 'moisturizes', label: 'Moisturizes', risk: 'Low', riskColor: 'success' },
  { id: 'anti_inflam', label: 'Anti-inflammatory Support', risk: 'Review', riskColor: 'warning' },
  { id: 'cures_eczema', label: 'Cures Eczema', risk: 'High', riskColor: 'danger' },
] as const;

const LANGUAGES = ['English', 'हिन्दी', 'मराठी', 'தமிழ்', 'తెలుగు', 'ಕನ್ನಡ', 'മലയാളം', 'বাংলা'];

const inputCls = "w-full px-4 py-3 bg-emerald-50/70 border border-emerald-200 rounded-xl text-sm text-slate-900 placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition";

export default function InnovationPassportForm({ onSubmit, isLoading }: PassportFormProps) {
  const { lang } = useLang();
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({
    innovationName: '',
    applicant: '',
    institution: '',
    productType: 'Nutraceutical',
    category: 'Herbal Supplement',
    targetMarket: 'India',
    formulationInput: 'हळद, नीम, तुळस',
    formulationLang: 'auto',
    extractionMethod: '',
    solvent: '',
    temperature: '',
    time: '',
    processingSteps: '',
    claims: [] as string[],
  });

  const [parsedFormulation, setParsedFormulation] = useState<FormulationParseResponse | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [firewallResult, setFirewallResult] = useState<{ status: string; color: string } | null>(null);

  const handleInput = (field: string, value: string) => setFormData((prev) => ({ ...prev, [field]: value }));

  const handleClaimToggle = (claimId: string) => {
    setFormData((prev) => {
      const hasClaim = prev.claims.includes(claimId);
      const claims = hasClaim ? prev.claims.filter((c) => c !== claimId) : [...prev.claims, claimId];
      return { ...prev, claims };
    });
  };

  const handleParseFormulation = async () => {
    setIsParsing(true);
    setParseError(null);
    try {
      const res = await parseFormulation(formData.formulationInput, formData.formulationLang);
      setParsedFormulation(res);
    } catch (err) {
      setParseError('passportform_parse_error');
    } finally {
      setIsParsing(false);
    }
  };

  const runClaimFirewall = () => {
    const therapeutic = ['treat', 'cure', 'heal', 'prevent', 'diagnose'];
    const labelText = formData.formulationInput.toLowerCase() + formData.claims.join(' ').toLowerCase();
    const hasDrugClaim = therapeutic.some((tt) => labelText.includes(tt));
    setFirewallResult(
      hasDrugClaim
        ? { status: 'passportform_firewall_high', color: 'red' }
        : { status: 'passportform_firewall_safe', color: 'green' }
    );
  };

  const totalSteps = STEPS.length;

  const nextStep = () => {
    if (step < totalSteps - 1) setStep(step + 1);
    else handleSubmit();
  };

  const prevStep = () => {
    if (step > 0) setStep(step - 1);
  };

  const handleSubmit = () => {
    onSubmit({
      case_title: formData.innovationName || 'Untitled Innovation',
      applicant: formData.applicant,
      institution: formData.institution,
      product_type: formData.productType,
      category: formData.category,
      target_markets: [formData.targetMarket],
      raw_text: formData.formulationInput,
      language: formData.formulationLang,
      extraction_method: formData.extractionMethod,
      solvent: formData.solvent,
      temperature: formData.temperature,
      time: formData.time,
      processing_steps: formData.processingSteps,
      proposed_claims: formData.claims.map((c) => CLAIM_OPTIONS.find((o) => o.id === c)!.label),
    });
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-3xl mx-auto">
      {/* Step indicator */}
      <div className="flex items-start gap-2 mb-8">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const active = i === step;
          const done = i < step;
          return (
            <button
              key={s.id}
              onClick={() => i < step && setStep(i)}
              className="flex-1 group"
            >
              <div className={`flex items-center gap-2`}>
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all flex-shrink-0 ${
                  active
                    ? 'bg-gradient-to-br from-blue-500 to-violet-600 text-white shadow-glow-blue'
                    : done
                      ? 'bg-emerald-100 text-emerald-600 border border-emerald-500/30'
                      : 'bg-emerald-50/70 text-slate-500 border border-emerald-200'
                }`}>
                  {done ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>
                <div className="hidden sm:block">
                  <div className={`text-[10px] font-semibold ${active ? 'text-blue-600' : done ? 'text-emerald-600' : 'text-slate-500'}`}>
                    {t(`passportform_step_${s.id}` as any, lang)}
                  </div>
                </div>
              </div>
              {i < totalSteps - 1 && (
                <div className={`hidden sm:block h-0.5 flex-1 mt-4 ml-2 ${i < step ? 'bg-emerald-500/40' : 'bg-emerald-200'}`} />
              )}
            </button>
          );
        })}
      </div>

      {/* Step 1: Basic Information */}
      {step === 0 && (
        <GlassCard padding="lg" className="animate-fadeInUp">
          <h3 className="text-sm font-bold text-slate-900 mb-5 flex items-center gap-2">
            <User className="w-4 h-4 text-blue-600" /> {t('passportform_basic_info', lang)}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="text-xs text-slate-500 mb-1.5 block">{t('passportform_innovation_name', lang)}</label>
              <input value={formData.innovationName} onChange={(e) => handleInput('innovationName', e.target.value)} placeholder={t('passportform_innovation_name_ph', lang)} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">{t('passportform_applicant', lang)}</label>
              <input value={formData.applicant} onChange={(e) => handleInput('applicant', e.target.value)} placeholder={t('passportform_applicant_ph', lang)} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">{t('passportform_institution', lang)}</label>
              <input value={formData.institution} onChange={(e) => handleInput('institution', e.target.value)} placeholder={t('passportform_institution_ph', lang)} className={inputCls} />
            </div>
            <div>
              <SelectOrOther
                label={t('passportform_product_type', lang)}
                options={['Nutraceutical', 'Ayurvedic Medicine', 'Cosmetic', 'Food Supplement', 'Herbal Supplement']}
                value={formData.productType}
                onChange={(v) => handleInput('productType', v)}
                inputPlaceholder={t('passportform_product_type_ph', lang)}
              />
            </div>
            <div>
              <SelectOrOther
                label={t('passportform_category', lang)}
                options={['Herbal Supplement', 'Traditional Medicine', 'Cosmeceutical', 'Functional Food']}
                value={formData.category}
                onChange={(v) => handleInput('category', v)}
                inputPlaceholder={t('passportform_category_ph', lang)}
              />
            </div>
            <div className="md:col-span-2">
              <SelectOrOther
                label={t('passportform_target_market', lang)}
                options={['India', 'United States', 'Canada', 'European Union', 'All (Global)']}
                value={formData.targetMarket}
                onChange={(v) => handleInput('targetMarket', v)}
                inputPlaceholder={t('passportform_target_market_ph', lang)}
              />
            </div>
          </div>
        </GlassCard>
      )}

      {/* Step 2: Multilingual Formulation */}
      {step === 1 && (
        <GlassCard padding="lg" className="animate-fadeInUp">
          <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
            <Languages className="w-4 h-4 text-blue-600" /> {t('passportform_multilingual_formulation', lang)}
          </h3>
          <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
            {LANGUAGES.map((l) => (
              <span key={l} className="px-2.5 py-1 rounded-full text-[10px] bg-emerald-50/70 text-slate-500 border border-emerald-200 whitespace-nowrap">{l}</span>
            ))}
          </div>
          <textarea
            value={formData.formulationInput}
            onChange={(e) => handleInput('formulationInput', e.target.value)}
            rows={3}
            placeholder={t('passportform_formulation_ph', lang)}
            className={`${inputCls} resize-none`}
          />
          <div className="flex items-center gap-3 mt-3">
            <Button variant="primary" size="sm" icon={isParsing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />} onClick={handleParseFormulation} disabled={isParsing}>
              {isParsing ? t('passportform_parsing', lang) : t('passportform_parse_canonicalize', lang)}
            </Button>
            {parsedFormulation && (
              <Badge variant="success" dot>{t('passportform_detected', lang)} {parsedFormulation.detected_language} · {parsedFormulation.ingredients.length} {t('passportform_botanicals', lang)}</Badge>
            )}
          </div>

          {parseError && <div className="mt-3 px-3 py-2 rounded-lg bg-red-100 border border-red-500/20 text-xs text-red-600">{t(parseError as any, lang)}</div>}

          {parsedFormulation && (
            <div className="mt-5 rounded-2xl bg-emerald-50/70 border border-emerald-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-emerald-200 flex items-center gap-2 text-xs font-bold text-slate-900">
                <Leaf className="w-4 h-4 text-emerald-600" /> {t('passportform_botanical_preview', lang)}
              </div>
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-emerald-200">
                    <th className="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">{t('passportform_common_input', lang)}</th>
                    <th className="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">{t('passportform_scientific_canonical', lang)}</th>
                    <th className="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">{t('passport_api_monograph', lang)}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-200">
                  {parsedFormulation.ingredients.map((ing, i) => (
                    <tr key={i} className={ing.status === 'unresolved' ? 'bg-amber-50/60' : ''}>
                      <td className="px-4 py-3 text-sm text-slate-900">
                        {ing.raw_name}
                        {ing.status === 'unresolved' && (
                          <span className="ml-2 inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-100 rounded-full px-2 py-0.5">
                            <AlertTriangle className="w-3 h-3" /> {t('passportform_not_in_glossary', lang)}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs font-semibold text-blue-600">{ing.botanical_name || '—'}</td>
                      <td className="px-4 py-3 text-[11px] text-slate-500">{ing.api_monograph_id || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassCard>
      )}

      {/* Step 3: Preparation Process */}
      {step === 2 && (
        <GlassCard padding="lg" className="animate-fadeInUp">
          <h3 className="text-sm font-bold text-slate-900 mb-5 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-blue-600" /> {t('passportform_preparation_process', lang)}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <SelectOrOther
                label={t('passportform_extraction_method', lang)}
                options={['Decoction (Kwatha)', 'Hydroalcoholic', 'Supercritical CO2', 'Cold Pressed', 'Steam Distillation', 'Soxhlet Extraction']}
                value={formData.extractionMethod}
                onChange={(v) => handleInput('extractionMethod', v)}
                placeholder={t('passportform_select_method', lang)}
                inputPlaceholder={t('passportform_extraction_method_ph', lang)}
              />
            </div>
            <div>
              <SelectOrOther
                label={t('passportform_solvent', lang)}
                options={['Water (Aqueous)', 'Ethanol 70%', 'Ethanol 95%', 'Methanol', 'CO2', 'Ghee / Oil']}
                value={formData.solvent}
                onChange={(v) => handleInput('solvent', v)}
                placeholder={t('passportform_select_solvent', lang)}
                hint={t('passportform_solvent_hint', lang)}
                inputPlaceholder={t('passportform_solvent_ph', lang)}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">{t('passportform_temperature', lang)}</label>
              <input value={formData.temperature} onChange={(e) => handleInput('temperature', e.target.value)} placeholder={t('passportform_temperature_ph', lang)} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">{t('passportform_time', lang)}</label>
              <input value={formData.time} onChange={(e) => handleInput('time', e.target.value)} placeholder={t('passportform_time_ph', lang)} className={inputCls} />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-slate-500 mb-1.5 block">{t('passportform_processing_steps', lang)}</label>
              <textarea value={formData.processingSteps} onChange={(e) => handleInput('processingSteps', e.target.value)} rows={3} placeholder={t('passportform_processing_steps_ph', lang)} className={`${inputCls} resize-none`} />
            </div>
          </div>
        </GlassCard>
      )}

      {/* Step 4: Health Claims */}
      {step === 3 && (
        <GlassCard padding="lg" className="animate-fadeInUp">
          <h3 className="text-sm font-bold text-slate-900 mb-5 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-600" /> {t('passportform_health_claims', lang)}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {CLAIM_OPTIONS.map((claim) => {
              const checked = formData.claims.includes(claim.id);
              return (
                <button
                  key={claim.id}
                  onClick={() => handleClaimToggle(claim.id)}
                  className={`p-4 rounded-2xl border text-sm text-left transition flex items-start justify-between gap-3 ${
                    checked ? 'bg-blue-100 border-blue-500/40' : 'bg-emerald-50/70 border-emerald-200 hover:border-blue-500/25'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-5 h-5 rounded-lg border flex items-center justify-center flex-shrink-0 ${checked ? 'bg-blue-500 border-blue-500' : 'border-slate-500'}`}>
                      {checked && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                    </div>
                    <span className={checked ? 'text-blue-600' : 'text-slate-600'}>{claim.label}</span>
                  </div>
                  <Badge variant={claim.riskColor as any} dot>{claim.risk}</Badge>
                </button>
              );
            })}
          </div>

          <div className="mt-6 pt-6 border-t border-emerald-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-900 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-amber-600" /> {t('passportform_claim_firewall', lang)}</span>
              <Button variant="secondary" size="sm" onClick={runClaimFirewall}>{t('passportform_run_firewall', lang)}</Button>
            </div>
            {firewallResult ? (
              <div className={`px-4 py-3 rounded-xl border text-sm ${firewallResult.color === 'green' ? 'bg-emerald-100 border-emerald-500/30 text-emerald-700' : 'bg-red-100 border-red-500/30 text-red-700'}`}>
                {t(firewallResult.status as any, lang)}
              </div>
            ) : (
              <div className="px-4 py-3 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-slate-500">
                {t('passportform_firewall_hint', lang)}
              </div>
            )}
          </div>
        </GlassCard>
      )}

      {/* Step 5: Review */}
      {step === 4 && (
        <GlassCard padding="lg" className="animate-fadeInUp">
          <h3 className="text-sm font-bold text-slate-900 mb-5 flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" /> {t('passportform_review_generate', lang)}
          </h3>
          <div className="space-y-3 rounded-2xl bg-emerald-50/70 border border-emerald-200 p-5">
            {[
              { k: t('passportform_innovation_name', lang), v: formData.innovationName || t('passportform_untitled', lang) },
              { k: t('passportform_applicant', lang), v: formData.applicant || '—' },
              { k: t('passportform_product_type', lang), v: formData.productType },
              { k: t('passportform_rv_target_market', lang), v: formData.targetMarket },
              { k: t('passportform_rv_extraction', lang), v: `${formData.extractionMethod || '—'} · ${formData.solvent || '—'}` },
              { k: t('passportform_rv_ingredients', lang), v: parsedFormulation?.ingredients.map((i) => i.raw_name).join(', ') || formData.formulationInput },
              { k: t('passportform_rv_claims', lang), v: formData.claims.length ? formData.claims.map((c) => CLAIM_OPTIONS.find((o) => o.id === c)!.label).join(', ') : t('passportform_none_selected', lang) },
            ].map((r) => (
              <div key={r.k} className="flex items-start justify-between gap-4 py-1.5 border-b border-emerald-200 last:border-0">
                <span className="text-xs text-slate-500 flex-shrink-0">{r.k}</span>
                <span className="text-xs text-slate-700 text-right">{r.v}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="success" dot>{t('passportform_badge_ready', lang)}</Badge>
            <Badge variant="info" dot>{t('passportform_badge_qr', lang)}</Badge>
            <Badge variant="neutral" dot>{t('passport_version', lang)} 1.0</Badge>
          </div>
        </GlassCard>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between mt-6">
        <Button variant="ghost" size="md" icon={<ChevronLeft className="w-4 h-4" />} onClick={prevStep} disabled={step === 0}>
          {t('passportform_back', lang)}
        </Button>
        <Button
          variant={step === totalSteps - 1 ? 'primary' : 'secondary'}
          size="lg"
          icon={isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : step === totalSteps - 1 ? <Sparkles className="w-4 h-4" /> : undefined}
          onClick={nextStep}
          disabled={isLoading}
        >
          {isLoading ? t('passportform_generating', lang) : step === totalSteps - 1 ? t('passportform_generate_passport', lang) : t('passportform_continue', lang)}
          {step < totalSteps - 1 && <ChevronRight className="w-4 h-4" />}
        </Button>
      </div>
    </motion.div>
  );
}
