'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft, Bot, Loader2, Play, Sparkles, Layers, CheckCircle2,
  AlertTriangle, FileText, Lightbulb, BookMarked, ChevronRight,
  ChevronLeft, Undo2, PauseCircle, Wand2, Wrench, GitBranch, Table2,
  FileDown, UploadCloud, FileUp, X, Send,
} from 'lucide-react';
import {
  innolabApi, InnolabAgentWorkflow, InnolabAgentQuestion, InnolabAgentRunResult,
  AgentUnderstanding, ExtractedFeature,
} from '../../../../lib/innolabApi';
import { AGENT_BLURBS } from '../../../../lib/agentBlurbs';

const PHASE_COLORS: Record<string, string> = {
  engineering: 'bg-cyan-500/10 text-cyan-700 border-cyan-200',
  ip: 'bg-indigo-500/10 text-indigo-700 border-indigo-200',
  life_sciences: 'bg-rose-500/10 text-rose-700 border-rose-200',
  materials: 'bg-emerald-500/10 text-emerald-700 border-emerald-200',
};

const SEVERITY_COLORS: Record<string, string> = {
  error: 'border-red-200 bg-red-50 text-red-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  info: 'border-emerald-200 bg-emerald-50 text-emerald-900',
};

function phaseKey(phase: string) {
  return PHASE_COLORS[phase] || 'bg-slate-100 text-slate-600 border-slate-200';
}

function AnswerBox({ kind, label, value, onChange, options }: {
  kind: string; label: string; value: string | string[]; onChange: (v: string | string[]) => void; options: string[];
}) {
  const [tagInput, setTagInput] = useState('');
  const arr = Array.isArray(value) ? value : value ? [value] : [];

  const addTag = (raw: string) => {
    const parts = raw.split(/[,;+|]/).map((x) => x.trim()).filter(Boolean);
    if (parts.length === 0) return;
    const next = [...arr];
    for (const p of parts) if (!next.includes(p)) next.push(p);
    onChange(next);
    setTagInput('');
  };

  if (kind === 'textarea') {
    return (
      <textarea
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(e.target.value)}
        rows={5}
        autoFocus
        placeholder="Type your answer…"
        className="w-full rounded-xl border border-emerald-200 bg-white/90 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300"
      />
    );
  }

  if (kind === 'select') {
    return (
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const active = value === opt;
          return (
            <button
              key={opt}
              onClick={() => onChange(active ? '' : opt)}
              className={`rounded-xl border px-4 py-2 text-sm transition ${
                active ? 'border-emerald-500 bg-emerald-600 text-white shadow-sm' : 'border-emerald-200 bg-white/90 text-slate-700 hover:border-emerald-300'
              }`}
            >
              {opt}
            </button>
          );
        })}
      </div>
    );
  }

  if (kind === 'bool') {
    return (
      <div className="flex gap-2">
        {['Yes', 'No'].map((opt) => {
          const active = value === opt.toLowerCase();
          return (
            <button
              key={opt}
              onClick={() => onChange(active ? '' : opt.toLowerCase())}
              className={`rounded-xl border px-5 py-2.5 text-sm font-medium transition ${
                active ? 'border-emerald-500 bg-emerald-600 text-white shadow-sm' : 'border-emerald-200 bg-white/90 text-slate-700 hover:border-emerald-300'
              }`}
            >
              {opt}
            </button>
          );
        })}
      </div>
    );
  }

  if (kind === 'multi') {
    return (
      <div className="space-y-2.5">
        {options.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {options.map((opt) => {
              const active = arr.includes(opt);
              return (
                <button
                  key={opt}
                  onClick={() => { const next = active ? arr.filter((x) => x !== opt) : [...arr, opt]; onChange(next); }}
                  className={`rounded-full border px-3 py-1 text-xs transition ${
                    active ? 'border-emerald-500 bg-emerald-600 text-white' : 'border-emerald-200 bg-white/90 text-slate-600 hover:border-emerald-300'
                  }`}
                >
                  {active ? '✓ ' : '+ '}{opt}
                </button>
              );
            })}
          </div>
        )}
        <div className="flex gap-2">
          <input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(tagInput); } }}
            placeholder="Add value and press Enter (comma separated ok)"
            className="flex-1 rounded-xl border border-emerald-200 bg-white/90 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300"
          />
          <button
            onClick={() => addTag(tagInput)}
            className="rounded-xl border border-emerald-300 px-4 py-2.5 text-sm text-emerald-700 hover:bg-emerald-50"
          >
            Add
          </button>
        </div>
        {arr.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {arr.map((v) => (
              <span key={v} className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 text-emerald-800 px-3 py-1 text-xs">
                {v}
                <button onClick={() => onChange(arr.filter((x) => x !== v))} className="text-emerald-600 hover:text-red-500">×</button>
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  // default: single-line text
  return (
    <input
      value={typeof value === 'string' ? value : ''}
      onChange={(e) => onChange(e.target.value)}
      autoFocus
      placeholder="Type your answer…"
      className="w-full rounded-xl border border-emerald-200 bg-white/90 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300"
    />
  );
}

function isAnswered(q: InnolabAgentQuestion, answers: Record<string, string | string[]>) {
  const v = answers[q.key];
  if (q.kind === 'multi') return Array.isArray(v) && v.length > 0;
  if (q.kind === 'bool') return v === 'yes' || v === 'no';
  return typeof v === 'string' && v.trim().length > 0;
}

export default function AgentDetailPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = decodeURIComponent(params.slug);

  const [agent, setAgent] = useState<InnolabAgentWorkflow | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingError, setLoadingError] = useState<string | null>(null);

  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [presetBrief, setPresetBrief] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<InnolabAgentRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFile, setShowFile] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // Eureka-style "confirm the agent's understanding" state
  const [understanding, setUnderstanding] = useState<AgentUnderstanding | null>(null);
  const [understandingLoading, setUnderstandingLoading] = useState(false);
  const [featureItems, setFeatureItems] = useState<ExtractedFeature[]>([]);
  const [featureDraft, setFeatureDraft] = useState('');

  // Uploaded document the agent reads as background
  const [doc, setDoc] = useState<{ name: string; text: string } | null>(null);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadingError(null);
    try {
      const [w] = await Promise.all([innolabApi.getAgentWorkflow(slug)]);
      const preset = typeof window !== 'undefined'
        ? (new URLSearchParams(window.location.search).get('brief') ?? '').trim()
        : '';
      const first = (w?.questions || []).find((q) => q.kind === 'text' || q.kind === 'textarea');
      setAgent(w);
      setStep(0);
      setResult(null);
      if (preset && first) {
        setPresetBrief(preset);
        setAnswers({ [first.key]: preset.slice(0, 2000) });
      } else {
        setPresetBrief('');
        setAnswers({});
      }
      setUnderstanding(null);
      setFeatureItems([]);
      setFeatureDraft('');
    } catch (e) {
      setLoadingError(e instanceof Error ? e.message : 'Agent not found');
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void load();
  }, [load]);

  const questions = useMemo(() => (agent?.questions?.length ? agent.questions : []), [agent]);
  const autoRun = Boolean(agent?.auto_run);
  const confirmStep = questions.length; // "confirm the agent's understanding"
  const reviewStep = questions.length + 1; // review/"run agent" is the final step
  const totalSteps = questions.length + 2;
  const progress = totalSteps <= 1 ? 0 : Math.round((step / (totalSteps - 1)) * 100);

  const current = step < questions.length ? questions[step] : null;

  const nextDisabled = current ? (current.required && !isAnswered(current, answers)) : false;

  const collectInputs = useCallback((): Record<string, unknown> => {
    const inputs: Record<string, unknown> = {};
    for (const q of questions) {
      const v = answers[q.key];
      if (q.kind === 'multi') {
        if (Array.isArray(v) && v.length) inputs[q.key] = v;
        else if (typeof v === 'string' && v.trim()) inputs[q.key] = v;
      } else if (typeof v === 'string' && v.trim()) {
        inputs[q.key] = v;
      }
    }
    if (doc?.text.trim()) inputs.document_text = doc.text.trim();
    return inputs;
  }, [questions, answers, doc]);

  const handleUploadDoc = async (file: File) => {
    if (!file || !agent) return;
    setUploadingDoc(true);
    setError(null);
    try {
      const res = await innolabApi.uploadAgentDocument(agent.slug, file);
      setDoc({ name: res.filename, text: res.extracted_text });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not read that document');
    } finally {
      setUploadingDoc(false);
    }
  };

  const runExtraction = useCallback(async () => {
    const inputs = collectInputs();
    if (Object.keys(inputs).length === 0) return;
    setUnderstandingLoading(true);
    try {
      const u = await innolabApi.extractAgentFeatures(slug, { inputs });
      setUnderstanding(u);
      const items = u.features.filter((f) => f.text.trim()).slice(0, 12);
      setFeatureItems(items.map((f) => ({ ...f })));
    } catch {
      setUnderstanding(null);
    } finally {
      setUnderstandingLoading(false);
    }
  }, [slug, collectInputs]);

  const handleContinue = () => {
    if (current && current.required && !isAnswered(current, answers)) return;
    if (step === confirmStep && (understandingLoading || understanding === null)) return; // wait for extraction
    if (step === confirmStep && autoRun) {
      void handleRun(); // Eureka-style autonomous run — no separate review step
      return;
    }
    if (step < reviewStep) setStep(step + 1);
  };

  const handleSkip = () => {
    if (current && !current.required) {
      setAnswers((a) => ({ ...a, [current.key]: '' }));
    }
    if (step < reviewStep) setStep(step + 1);
  };

  useEffect(() => {
    if (step === confirmStep && questions.length > 0 && understanding === null && !understandingLoading) {
      void runExtraction();
    }
  }, [step, confirmStep, questions.length, understanding, understandingLoading, runExtraction]);

  const addFeature = () => {
    const text = featureDraft.trim();
    if (!text) return;
    const next = [...featureItems, { text: text.slice(0, 90), kind: 'custom' }];
    setFeatureItems(next);
    setFeatureDraft('');
  };

  const updateFeature = (idx: number, text: string) => {
    setFeatureItems((items) => items.map((f, i) => (i === idx ? { ...f, text } : f)));
  };

  const removeFeature = (idx: number) => {
    setFeatureItems((items) => items.filter((_, i) => i !== idx));
  };

  const handleRun = async () => {
    if (!agent) return;
    setRunning(true);
    setError(null);
    try {
      const confirmed = featureItems.length > 0 ? featureItems.map((f) => f.text) : undefined;
      const r = await innolabApi.runAgent(agent.slug, {
        inputs: { ...collectInputs(), ...(confirmed ? { extracted_features: confirmed } : {}) },
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run agent');
    } finally {
      setRunning(false);
    }
  };

  const handleSendDoc = async () => {
    if (!agent || !doc) return;
    setRunning(true);
    setError(null);
    try {
      const r = await innolabApi.runAgent(agent.slug, {
        inputs: { document_text: doc.text.trim() },
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run the agent on this document');
    } finally {
      setRunning(false);
    }
  };

  const handleExport = async () => {
    if (!agent || !result) return;
    setExporting(true);
    setError(null);
    try {
      const blob = await innolabApi.exportAgentResult(agent.slug, result.result);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${agent.slug}_report.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not export the Word report');
    } finally {
      setExporting(false);
    }
  };

  const resetFlow = () => {
    setAnswers({});
    setStep(0);
    setResult(null);
    setError(null);
    setUnderstanding(null);
    setFeatureItems([]);
    setFeatureDraft('');
    setDoc(null);
    setPresetBrief('');
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center text-slate-500">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading agent…
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
        <p className="text-slate-600">{loadingError || 'Agent not found'}</p>
        <button onClick={() => router.push('/innovation-lab')} className="inline-flex items-center gap-2 rounded-xl border border-emerald-300 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50">
          <ArrowLeft className="w-4 h-4" /> Back to Agent Hub
        </button>
      </div>
    );
  }

  return (
    <main className="flex-1 p-4 md:p-6 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto py-2">
      <button
        onClick={() => router.push('/innovation-lab')}
        className="mb-6 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-emerald-700"
      >
        <ArrowLeft className="w-4 h-4" /> Agent Hub
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className="inline-flex w-14 h-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-900/20">
            <Bot className="w-7 h-7" />
          </span>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 font-display">{agent.label}</h1>
            <p className="text-sm text-slate-500">{agent.slug}</p>
          </div>
        </div>
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${phaseKey(agent.phase)}`}>
          <Layers className="w-3.5 h-3.5" /> {agent.phase.replace(/_/g, ' ')}
        </span>
      </div>

      <p className="mt-3 text-sm text-slate-600 leading-relaxed">{AGENT_BLURBS[slug] || agent.description}</p>

      <div className="mt-8 grid lg:grid-cols-[1fr_1.35fr] gap-6 items-start">
        {/* Internal workflow plan (visible, controllable) */}
        <div className="rounded-2xl border border-emerald-200 bg-white/80 backdrop-blur p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <GitBranch className="w-4 h-4 text-emerald-600" />
            <h2 className="text-sm font-semibold text-slate-900">Internal workflow</h2>
          </div>
          <p className="text-[11px] text-slate-400 mb-4">What this agent will execute — every step is reviewable after the run.</p>
          <ol className="space-y-2.5">
            {agent.steps.map((s, i) => {
              const done = result !== null || i < step && step < reviewStep;
              const active = i === step && step < reviewStep;
              return (
                <li key={i} className="flex items-start gap-3">
                  <span className={`inline-flex w-6 h-6 items-center justify-center rounded-full text-[10px] font-bold shrink-0 ${
                    done ? 'bg-emerald-600 text-white' : active ? 'bg-emerald-100 text-emerald-700 ring-2 ring-emerald-400' : 'bg-slate-100 text-slate-400'
                  }`}>
                    {done ? '✓' : i + 1}
                  </span>
                  <div className="min-w-0">
                    <p className={`text-xs font-medium ${done ? 'text-emerald-800' : active ? 'text-slate-900' : 'text-slate-500'}`}>{s.label}</p>
                    {s.description && <p className="text-[11px] text-slate-400 leading-snug">{s.description}</p>}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>

        {/* Step-by-step question flow / review / result */}
        <div className="space-y-4">
          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4 flex items-start justify-between gap-3">
              <p className="text-sm text-red-700">{error}</p>
              <button onClick={() => setError(null)} className="text-sm text-red-600 hover:underline">Dismiss</button>
            </div>
          )}

          {result === null ? (
            <>
              {presetBrief && (
                <div className="rounded-2xl border border-teal-300 bg-teal-50 p-4 flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <GitBranch className="w-4 h-4 text-teal-600 mt-0.5 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-teal-900">Prefilled from your Orchestrator brief</p>
                      <p className="text-[11px] text-teal-700 mt-0.5 line-clamp-2">{presetBrief}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => { setAnswers({}); setPresetBrief(''); }}
                    className="text-[11px] text-teal-700 hover:text-teal-900 underline shrink-0"
                  >
                    Clear & re-enter
                  </button>
                </div>
              )}
              {/* Document upload — the agent reads this document */}
              <div className="rounded-2xl border border-dashed border-teal-300 bg-teal-50/40 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <UploadCloud className="w-4 h-4 text-teal-600" />
                    <div>
                      <p className="text-xs font-semibold text-slate-800">Upload a document for the agent to read</p>
                      <p className="text-[11px] text-slate-500">PDF · DOCX · TXT · MD · CSV · image (OCR) — Send it straight to the agent, or answer the guided questions below (your choice).</p>
                    </div>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.md,.csv,.json,.png,.jpg,.jpeg"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void handleUploadDoc(f);
                      e.target.value = '';
                    }}
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadingDoc || questions.length === 0}
                    className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2 text-xs font-medium text-white hover:bg-teal-700 disabled:opacity-40"
                  >
                    {uploadingDoc ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileUp className="w-3.5 h-3.5" />}
                    {uploadingDoc ? 'Reading…' : doc ? 'Replace' : 'Upload'}
                  </button>
                </div>
                {doc && (
                  <div className="mt-3 flex items-center justify-between gap-2 rounded-xl border border-teal-200 bg-white px-3 py-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-4 h-4 text-teal-600 shrink-0" />
                      <span className="text-xs text-slate-700 truncate">{doc.name}</span>
                      <span className="text-[10px] text-slate-400 shrink-0">{doc.text.length.toLocaleString()} chars read</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => void handleSendDoc()}
                        disabled={running || uploadingDoc}
                        className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-40"
                      >
                        {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                        {running ? 'Running…' : 'Send to agent'}
                      </button>
                      <button onClick={() => setDoc(null)} className="text-slate-400 hover:text-red-500 shrink-0" aria-label="Remove document">
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Progress */}
              <div className="rounded-2xl border border-emerald-200 bg-white/80 p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-700">
                    {step < questions.length
                      ? `Question ${step + 1} of ${questions.length}`
                      : step === confirmStep
                        ? 'Confirm the agent\'s understanding'
                        : 'Review & run'}
                  </span>
                  <span className="text-[11px] text-slate-400">{progress}%</span>
                </div>
                <div className="h-2 rounded-full bg-emerald-100 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-300" style={{ width: `${progress}%` }} />
                </div>
              </div>

              {current ? (
                <div className="rounded-2xl border border-emerald-200 bg-white/90 p-6 shadow-sm">
                  <div className="flex items-start gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-emerald-600 mt-0.5" />
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-600">{current.label}</p>
                      <h3 className="text-base font-semibold text-slate-900">{current.question}</h3>
                    </div>
                  </div>
                  {current.required ? (
                    <span className="inline-flex mt-1 items-center gap-1 rounded-full bg-red-50 text-red-600 px-2 py-0.5 text-[10px] font-medium">required</span>
                  ) : (
                    <span className="inline-flex mt-1 items-center gap-1 rounded-full bg-slate-100 text-slate-500 px-2 py-0.5 text-[10px] font-medium">optional</span>
                  )}
                  {current.help && <p className="mt-2 text-[11px] text-slate-500 italic">{current.help}</p>}

                  <div className="mt-5">
                    <AnswerBox
                      kind={current.kind}
                      label={current.label}
                      value={answers[current.key] ?? (current.kind === 'multi' ? [] : '')}
                      onChange={(v) => setAnswers((a) => ({ ...a, [current.key]: v }))}
                      options={current.options || []}
                    />
                  </div>

                  <div className="mt-6 flex items-center justify-between">
                    <button
                      onClick={() => step > 0 ? setStep(step - 1) : router.push('/innovation-lab')}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-300 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50"
                    >
                      <ChevronLeft className="w-4 h-4" /> {step > 0 ? 'Back' : 'Agent Hub'}
                    </button>
                    <div className="flex items-center gap-2">
                      {!current.required && (
                        <button onClick={handleSkip} className="inline-flex items-center gap-1 rounded-xl px-3 py-2 text-xs text-slate-400 hover:text-slate-600">
                          Skip
                        </button>
                      )}
                      <button
                        onClick={handleContinue}
                        disabled={nextDisabled}
                        className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-40"
                      >
                        {stepsLabel()} <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ) : step === confirmStep ? (
                <div className="rounded-2xl border border-emerald-200 bg-white/90 p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-5 h-5 text-emerald-600" />
                    <h3 className="text-lg font-semibold text-slate-900">Confirm the agent&apos;s understanding</h3>
                  </div>
                  <p className="text-xs text-slate-500">Eureka-style check-in: here is how the agent understood your input. Edit the features below — {autoRun ? 'then the agent autonomously analyzes and searches against the confirmed set.' : 'the search/analysis runs against the confirmed set.'}</p>

                  {understandingLoading ? (
                    <div className="mt-6 flex items-center gap-2 text-sm text-slate-500">
                      <Loader2 className="w-4 h-4 animate-spin" /> Analyzing your input and extracting technical features…
                    </div>
                  ) : understanding ? (
                    <div className="mt-6 space-y-5">
                      <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 mb-1">Agent&apos;s understanding</p>
                        <p className="text-sm text-slate-700 leading-relaxed">{understanding.summary}</p>
                      </div>

                      {understanding.markets?.length > 0 && (
                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Jurisdictions in scope</p>
                          <div className="flex flex-wrap gap-1.5">
                            {understanding.markets.map((m) => (
                              <span key={m} className="rounded-full bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1 text-xs">{m}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Extracted technical features — confirm or edit</p>
                          <span className="text-[10px] text-slate-400">{featureItems.length} confirmed</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5 mb-2">
                          {featureItems.map((f, idx) => (
                            <span key={idx} className="inline-flex items-center gap-1.5 rounded-full bg-emerald-600 text-white px-3 py-1 text-xs">
                              <input
                                value={f.text}
                                onChange={(e) => updateFeature(idx, e.target.value)}
                                className="bg-transparent outline-none w-40 text-white placeholder-white/60"
                              />
                              <span className="text-[9px] uppercase bg-white/20 rounded-full px-1.5">{f.kind}</span>
                              <button onClick={() => removeFeature(idx)} className="text-white/70 hover:text-white">×</button>
                            </span>
                          ))}
                          {featureItems.length === 0 && (
                            <span className="text-xs text-slate-400">No features extracted — add them manually below.</span>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <input
                            value={featureDraft}
                            onChange={(e) => setFeatureDraft(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addFeature(); } }}
                            placeholder="Add a technical feature to include in the analysis"
                            className="flex-1 rounded-xl border border-emerald-200 bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300"
                          />
                          <button onClick={addFeature} className="rounded-xl border border-emerald-300 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50">Add</button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-800">
                      Could not extract features automatically. Continue to review and run with your answers as-is.
                    </div>
                  )}

                  <div className="mt-6 flex items-center justify-between">
                    <button
                      onClick={() => setStep(Math.max(0, questions.length - 1))}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-300 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50"
                    >
                      <ChevronLeft className="w-4 h-4" /> Back to questions
                    </button>
                    <button
                      onClick={handleContinue}
                      disabled={understandingLoading || understanding === null}
                      className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-40"
                    >
                      {autoRun ? 'Start search & analysis' : 'Continue'} <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl border border-emerald-200 bg-white/90 p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    <h3 className="text-lg font-semibold text-slate-900">Ready to run {agent.label}</h3>
                  </div>
                  <p className="text-xs text-slate-500 mb-5">Review your answers below, then run the agent. Every step stays visible after execution.</p>

                  <div className="space-y-2.5">
                    {questions.length === 0 && (
                      <p className="text-xs text-slate-400">No guided questions configured — running with defaults.</p>
                    )}
                    {doc && (
                      <div className="flex items-start justify-between gap-4 rounded-xl border border-teal-200 bg-teal-50/60 px-3 py-2">
                        <span className="text-xs font-medium text-teal-800">Uploaded document</span>
                        <span className="text-xs text-right text-teal-700">{doc.name} · {doc.text.length.toLocaleString()} chars read</span>
                      </div>
                    )}
                    {questions.map((q) => {
                      const v = answers[q.key];
                      const display = q.kind === 'multi' && Array.isArray(v) ? v.join(', ') : typeof v === 'string' ? v : '—';
                      return (
                        <div key={q.key} className="flex items-start justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50/60 px-3 py-2">
                          <span className="text-xs font-medium text-slate-700">{q.label}</span>
                          <span className={`text-xs text-right ${q.required && (!v || !isAnswered(q, answers)) ? 'text-red-500' : 'text-slate-600'}`}>
                            {q.required && (!v || !isAnswered(q, answers)) ? 'missing' : display}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  <div className="mt-6 flex items-center justify-between gap-2">
                    <button
                      onClick={() => setStep(Math.max(0, questions.length - 1))}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-300 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50"
                    >
                      <ChevronLeft className="w-4 h-4" /> Edit answers
                    </button>
                    <button
                      onClick={() => void handleRun()}
                      disabled={running}
                      className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                      {running ? 'Running…' : 'Run agent'}
                    </button>
                  </div>
                  {running && (
                    <p className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Agent is walking its workflow, grounding on the local corpus…
                    </p>
                  )}
                </div>
              )}
            </>
          ) : (
            /* Result view — with execution trace */
            <div className="space-y-4">
              <div className={`rounded-2xl border p-5 ${result.result.ok ? 'border-emerald-200 bg-emerald-50/60' : 'border-red-200 bg-red-50'}`}>
                <div className="flex items-start gap-3">
                  {result.result.ok
                    ? <CheckCircle2 className="w-5 h-5 text-emerald-600 mt-0.5 flex-shrink-0" />
                    : <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />}
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{result.result.summary}</p>
                    <p className="text-xs text-slate-500 mt-1">{result.result.note}</p>
                  </div>
                </div>
                {result.run_id && <p className="mt-3 text-[11px] text-slate-400">Logged to run {result.run_id.slice(0, 8)}</p>}
              </div>

              {result.result.workflow && (
                <div className="rounded-2xl border border-slate-200 bg-white p-5">
                  <p className="text-xs font-semibold text-slate-900 mb-2"><GitBranch className="w-3.5 h-3.5 inline mr-1 text-teal-500" /> Execution trace</p>
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {result.result.tools_used?.map((t) => (
                      <span key={t} className="inline-flex items-center gap-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200 px-2.5 py-0.5 text-[10px] font-medium">
                        <Wrench className="w-3 h-3" /> {t}
                      </span>
                    ))}
                  </div>
                  <div className="space-y-1">
                    {result.result.workflow.map((s, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-slate-600">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" /> {s.label}
                      </div>
                    ))}
                  </div>
                  {result.result.execution && (
                    <p className="mt-3 text-[11px] text-slate-400 italic">
                      {result.result.execution.reasoning}
                    </p>
                  )}
                </div>
              )}

              {result.result.claims.length > 0 && (
                <div className="rounded-2xl border border-rose-200 bg-white p-5">
                  <p className="text-xs font-semibold text-slate-900 mb-2"><FileText className="w-3.5 h-3.5 inline mr-1 text-rose-500" /> Draft claims</p>
                  <ul className="space-y-1.5">
                    {result.result.claims.map((c, i) => (
                      <li key={i} className="text-xs text-slate-700 bg-rose-50/60 rounded-lg px-3 py-2">{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              {result.result.sections.length > 0 && (
                <div className="space-y-4">
                  {result.result.sections.map((sec, si) => (
                    <div key={si} className="rounded-2xl border border-emerald-100 bg-white p-5">
                      <p className="text-xs font-semibold text-slate-900 mb-1">
                        <Table2 className="w-3.5 h-3.5 inline mr-1 text-emerald-600" /> {sec.title}
                      </p>
                      {sec.caption && <p className="text-[11px] text-slate-400 italic mb-3">{sec.caption}</p>}
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          {sec.columns && (
                            <thead>
                              <tr className="border-b border-slate-200 text-left text-slate-500">
                                {sec.columns.map((col, ci) => (
                                  <th key={ci} className="py-1.5 pr-3 font-medium whitespace-nowrap">{col.replace(/_/g, ' ')}</th>
                                ))}
                              </tr>
                            </thead>
                          )}
                          <tbody>
                            {sec.rows.map((row, ri) => {
                              const keys = sec.columns || Object.keys(row);
                              return (
                                <tr key={ri} className="border-b border-slate-100 last:border-0 align-top">
                                  {keys.map((k, ci) => (
                                    <td key={ci} className="py-1.5 pr-3 text-slate-700">
                                      {String(row[k] ?? '—')}
                                    </td>
                                  ))}
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {result.result.findings.length > 0 && (
                <div className="rounded-2xl border border-slate-200 bg-white p-5">
                  <p className="text-xs font-semibold text-slate-900 mb-2">Findings ({result.result.findings.length})</p>
                  <ul className="space-y-2">
                    {result.result.findings.map((f) => (
                      <li key={f.id} className={`rounded-xl border px-3 py-2 text-xs ${SEVERITY_COLORS[f.severity] || 'border-slate-200 bg-slate-50 text-slate-700'}`}>
                        <span className="font-semibold">{f.title}</span>
                        <span className="block text-slate-600 mt-0.5 whitespace-pre-line">{f.detail}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.result.citations.length > 0 && (
                <div className="rounded-2xl border border-slate-200 bg-white p-5">
                  <p className="text-xs font-semibold text-slate-900 mb-2">
                    <BookMarked className="w-3.5 h-3.5 inline mr-1 text-blue-500" />
                    Citations ({result.result.citations.length})
                  </p>
                  <ul className="space-y-2">
                    {result.result.citations.map((c, i) => (
                      <li key={i} className="text-xs rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-slate-800">{c.act_title}</span>
                          <button onClick={() => setShowFile(showFile === `${i}` ? null : `${i}`)} className="text-teal-600 hover:underline flex-shrink-0">
                            {showFile === `${i}` ? 'hide' : 'passage'}
                          </button>
                        </div>
                        <p className="text-slate-500 mt-0.5">{c.section_reference} · {c.authority} · rank {c.authority_rank}</p>
                        {showFile === `${i}` && c.exact_passage && (
                          <p className="mt-1.5 text-slate-600 bg-white rounded-lg border border-emerald-100 p-2">{c.exact_passage}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.result.suggestions.length > 0 && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-5">
                  <p className="text-xs font-semibold text-slate-900 mb-2"><Lightbulb className="w-3.5 h-3.5 inline mr-1 text-amber-500" /> Next steps</p>
                  <ul className="space-y-1.5">
                    {result.result.suggestions.map((s, i) => (
                      <li key={i} className="text-xs text-slate-700 flex gap-2">
                        <span className="text-amber-500">▸</span>{s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => void handleExport()}
                  disabled={exporting}
                  className="inline-flex items-center gap-2 rounded-xl bg-slate-800 px-4 py-2 text-xs font-medium text-white hover:bg-slate-900 disabled:opacity-50"
                >
                  {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5" />}
                  {exporting ? 'Building Word…' : 'Export Word (.docx)'}
                </button>
                <button
                  onClick={() => { setResult(null); setStep(confirmStep); }}
                  className="inline-flex items-center gap-2 rounded-xl border border-emerald-300 px-4 py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-50"
                >
                  <Undo2 className="w-3.5 h-3.5" /> Edit answers & re-run
                </button>
                <button onClick={resetFlow} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50">
                  <PauseCircle className="w-3.5 h-3.5" /> Start over
                </button>
                <button
                  onClick={() => router.push('/innovation-lab')}
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-medium text-white hover:bg-emerald-700"
                >
                  <Wand2 className="w-3.5 h-3.5" /> Back to Agent Hub
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <p className="mt-10 text-center text-xs text-slate-400">
        AI-assisted research material — must be reviewed by a qualified professional. Not legal, medical, safety, regulatory, or patentability advice.
      </p>
      </div>
    </main>
  );

  function stepsLabel() {
    return step < confirmStep ? 'Continue' : 'Proceed to review';
  }
}