'use client';
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Sparkles, Loader2, ChevronRight, ChevronLeft, FlaskConical, Leaf,
  ShieldCheck, Languages, User, ClipboardList, Check, CheckCircle2, FileText,
} from 'lucide-react';
import { parseFormulation } from '../lib/api';
import { FormulationParseResponse } from '../types';
import { GlassCard } from './ui/GlassCard';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';

interface PassportFormProps {
  onSubmit: (data: any) => void;
  isLoading?: boolean;
}

const STEPS = [
  { label: 'Basic Info', icon: User },
  { label: 'Formulation', icon: Languages },
  { label: 'Process', icon: FlaskConical },
  { label: 'Claims', icon: ShieldCheck },
  { label: 'Review', icon: ClipboardList },
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
      setParseError('Failed to parse formulation. Backend must be running.');
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
        ? { status: 'High Risk — drug claim detected', color: 'red' }
        : { status: 'Safe — claims appear compliant', color: 'green' }
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
              key={s.label}
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
                    {s.label}
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
            <User className="w-4 h-4 text-blue-600" /> Basic Information
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="text-xs text-slate-500 mb-1.5 block">Innovation Name</label>
              <input value={formData.innovationName} onChange={(e) => handleInput('innovationName', e.target.value)} placeholder="e.g. TriHerb Restful Sleep Vati" className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Applicant</label>
              <input value={formData.applicant} onChange={(e) => handleInput('applicant', e.target.value)} placeholder="Full name or organization" className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Institution</label>
              <input value={formData.institution} onChange={(e) => handleInput('institution', e.target.value)} placeholder="e.g. NIPER, Startup, MSME" className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Product Type</label>
              <select value={formData.productType} onChange={(e) => handleInput('productType', e.target.value)} className={inputCls}>
                <option>Nutraceutical</option><option>Ayurvedic Medicine</option><option>Cosmetic</option><option>Food Supplement</option><option>Herbal Supplement</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Category</label>
              <select value={formData.category} onChange={(e) => handleInput('category', e.target.value)} className={inputCls}>
                <option>Herbal Supplement</option><option>Traditional Medicine</option><option>Cosmeceutical</option><option>Functional Food</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-slate-500 mb-1.5 block">Target Market</label>
              <select value={formData.targetMarket} onChange={(e) => handleInput('targetMarket', e.target.value)} className={inputCls}>
                <option>India</option><option>United States</option><option>Canada</option><option>European Union</option><option>All (Global)</option>
              </select>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Step 2: Multilingual Formulation */}
      {step === 1 && (
        <GlassCard padding="lg" className="animate-fadeInUp">
          <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
            <Languages className="w-4 h-4 text-blue-600" /> Multilingual Formulation
          </h3>
          <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
            {LANGUAGES.map((lang) => (
              <span key={lang} className="px-2.5 py-1 rounded-full text-[10px] bg-emerald-50/70 text-slate-500 border border-emerald-200 whitespace-nowrap">{lang}</span>
            ))}
          </div>
          <textarea
            value={formData.formulationInput}
            onChange={(e) => handleInput('formulationInput', e.target.value)}
            rows={3}
            placeholder="हळद, नीम, तुळस / Turmeric, Neem, Tulsi..."
            className={`${inputCls} resize-none`}
          />
          <div className="flex items-center gap-3 mt-3">
            <Button variant="primary" size="sm" icon={isParsing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />} onClick={handleParseFormulation} disabled={isParsing}>
              {isParsing ? 'Parsing...' : 'Parse & Canonicalize'}
            </Button>
            {parsedFormulation && (
              <Badge variant="success" dot>Detected: {parsedFormulation.detected_language} · {parsedFormulation.ingredients.length} botanicals</Badge>
            )}
          </div>

          {parseError && <div className="mt-3 px-3 py-2 rounded-lg bg-red-100 border border-red-500/20 text-xs text-red-600">{parseError}</div>}

          {parsedFormulation && (
            <div className="mt-5 rounded-2xl bg-emerald-50/70 border border-emerald-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-emerald-200 flex items-center gap-2 text-xs font-bold text-slate-900">
                <Leaf className="w-4 h-4 text-emerald-600" /> Botanical Mapping Preview
              </div>
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-emerald-200">
                    <th className="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Common / Input</th>
                    <th className="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Scientific (Canonical)</th>
                    <th className="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">API Monograph</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-200">
                  {parsedFormulation.ingredients.map((ing, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3 text-sm text-slate-900">{ing.raw_name}</td>
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
            <FlaskConical className="w-4 h-4 text-blue-600" /> Preparation Process
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Extraction Method</label>
              <select value={formData.extractionMethod} onChange={(e) => handleInput('extractionMethod', e.target.value)} className={inputCls}>
                <option value="">Select method</option><option>Decoction (Kwatha)</option><option>Hydroalcoholic</option><option>Supercritical CO2</option><option>Cold Pressed</option><option>Steam Distillation</option><option>Soxhlet Extraction</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Solvent</label>
              <select value={formData.solvent} onChange={(e) => handleInput('solvent', e.target.value)} className={inputCls}>
                <option value="">Select solvent</option><option>Water (Aqueous)</option><option>Ethanol 70%</option><option>Ethanol 95%</option><option>Methanol</option><option>CO2</option><option>Ghee / Oil</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Temperature (°C)</label>
              <input value={formData.temperature} onChange={(e) => handleInput('temperature', e.target.value)} placeholder="e.g. 80°C" className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1.5 block">Time (hours)</label>
              <input value={formData.time} onChange={(e) => handleInput('time', e.target.value)} placeholder="e.g. 4 hours" className={inputCls} />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-slate-500 mb-1.5 block">Processing Steps</label>
              <textarea value={formData.processingSteps} onChange={(e) => handleInput('processingSteps', e.target.value)} rows={3} placeholder="Describe the step-by-step manufacturing process..." className={`${inputCls} resize-none`} />
            </div>
          </div>
        </GlassCard>
      )}

      {/* Step 4: Health Claims */}
      {step === 3 && (
        <GlassCard padding="lg" className="animate-fadeInUp">
          <h3 className="text-sm font-bold text-slate-900 mb-5 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-600" /> Health Claims
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
              <span className="text-xs font-bold text-slate-900 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-amber-600" /> Claim Firewall</span>
              <Button variant="secondary" size="sm" onClick={runClaimFirewall}>Run Claim Firewall Check</Button>
            </div>
            {firewallResult ? (
              <div className={`px-4 py-3 rounded-xl border text-sm ${firewallResult.color === 'green' ? 'bg-emerald-100 border-emerald-500/30 text-emerald-700' : 'bg-red-100 border-red-500/30 text-red-700'}`}>
                {firewallResult.status}
              </div>
            ) : (
              <div className="px-4 py-3 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-slate-500">
                Run a check to validate these claims against regulatory requirements
              </div>
            )}
          </div>
        </GlassCard>
      )}

      {/* Step 5: Review */}
      {step === 4 && (
        <GlassCard padding="lg" className="animate-fadeInUp">
          <h3 className="text-sm font-bold text-slate-900 mb-5 flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" /> Review & Generate Passport
          </h3>
          <div className="space-y-3 rounded-2xl bg-emerald-50/70 border border-emerald-200 p-5">
            {[
              { k: 'Innovation Name', v: formData.innovationName || 'Untitled Innovation' },
              { k: 'Applicant', v: formData.applicant || '—' },
              { k: 'Product Type', v: formData.productType },
              { k: 'Target Market', v: formData.targetMarket },
              { k: 'Extraction', v: `${formData.extractionMethod || '—'} · ${formData.solvent || '—'}` },
              { k: 'Ingredients', v: parsedFormulation?.ingredients.map((i) => i.raw_name).join(', ') || formData.formulationInput },
              { k: 'Claims', v: formData.claims.length ? formData.claims.map((c) => CLAIM_OPTIONS.find((o) => o.id === c)!.label).join(', ') : 'None selected' },
            ].map((r) => (
              <div key={r.k} className="flex items-start justify-between gap-4 py-1.5 border-b border-emerald-200 last:border-0">
                <span className="text-xs text-slate-500 flex-shrink-0">{r.k}</span>
                <span className="text-xs text-slate-700 text-right">{r.v}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="success" dot>Passport Ready</Badge>
            <Badge variant="info" dot>QR Included</Badge>
            <Badge variant="neutral" dot>Version 1.0</Badge>
          </div>
        </GlassCard>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between mt-6">
        <Button variant="ghost" size="md" icon={<ChevronLeft className="w-4 h-4" />} onClick={prevStep} disabled={step === 0}>
          Back
        </Button>
        <Button
          variant={step === totalSteps - 1 ? 'primary' : 'secondary'}
          size="lg"
          icon={isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : step === totalSteps - 1 ? <Sparkles className="w-4 h-4" /> : undefined}
          onClick={nextStep}
          disabled={isLoading}
        >
          {isLoading ? 'Generating...' : step === totalSteps - 1 ? 'Generate Innovation Passport' : 'Continue'}
          {step < totalSteps - 1 && <ChevronRight className="w-4 h-4" />}
        </Button>
      </div>
    </motion.div>
  );
}
