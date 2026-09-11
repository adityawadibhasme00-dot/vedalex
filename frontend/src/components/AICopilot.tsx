'use client';
import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Loader2, ChevronDown, Copy, Check, Library, Mic, Volume2, VolumeX, AudioLines, Lightbulb, ShieldCheck, ShieldAlert, AlertTriangle, ListChecks, Target, BarChart3, PieChart as PieChartIcon, Radar as RadarIcon, Gauge, GitBranch, MapPin, ShieldQuestion, Table2 } from 'lucide-react';
import { askCopilot, getSuggestedQuestions } from '../lib/api';
import { CopilotResponse, CopilotChart } from '../types';
import { HerbSprig, TulsiLeaf, TurmericRoot, MortarPestle } from './BotanicalDecor';
import { BarChart as RCBarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, RadarChart, Radar, PolarGrid, PolarAngleAxis } from 'recharts';
import { GlassCard } from './ui/GlassCard';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { ReadinessGauge } from './ReadinessGauge';
import { useVoiceAssistant } from '../hooks/useVoiceAssistant';

interface AICopilotProps {
  passportId?: string;
  lang?: string;
}

const DEFAULT_SUGGESTIONS = [
  'Can I patent this?',
  'Is Neem already patented?',
  'Check my label',
  'What evidence is missing?',
];

const RAG_SOURCES = [
  { name: 'Ayurvedic Pharmacopoeia of India', category: 'Verified', color: 'emerald' },
  { name: 'Charaka Samhita', category: 'Classical Text', color: 'blue' },
  { name: 'PubMed', category: 'Peer-Reviewed', color: 'violet' },
  { name: 'WIPO Metadata', category: 'Patent Data', color: 'amber' },
];

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: CopilotResponse['sources'];
  confidence?: number;
  charts?: CopilotChart[];
  images?: string[];
  analysisCard?: CopilotResponse['analysis_card'];
  evidenceUsed?: CopilotResponse['evidence_used'];
  nextActions?: CopilotResponse['next_actions'];
  intent?: CopilotResponse['intent'];
  timestamp: number;
}

function confidenceTone(c?: number): 'success' | 'warning' | 'danger' {
  const v = Math.round((c || 0) * 100);
  if (v >= 70) return 'success';
  if (v >= 40) return 'warning';
  return 'danger';
}

const CHART_COLORS = ['#6366f1', '#22d3ee', '#34d399', '#fbbf24', '#f472b6', '#a78bfa'];

const STATUS_META: Record<string, { dot: string; text: string; ring: string; label: string }> = {
  completed: { dot: '#10B981', text: 'text-emerald-700', ring: 'border-emerald-400', label: 'Completed' },
  current: { dot: '#F59E0B', text: 'text-amber-700', ring: 'border-amber-400', label: 'Current blocker' },
  pending: { dot: '#cbd5e1', text: 'text-slate-500', ring: 'border-slate-200', label: 'Pending' },
};

function TimelineChart({ chart }: { chart: CopilotChart }) {
  const phases = chart.phases ?? [];
  return (
    <div className="flex overflow-x-auto py-2 gap-1.5">
      {phases.map((p, i) => {
        const meta = STATUS_META[p.status] ?? STATUS_META.pending;
        return (
          <div key={p.label} className="flex items-start gap-1.5 flex-shrink-0">
            <div className={`w-9 min-w-[9rem] rounded-xl border bg-white/70 p-2 ${meta.ring} ${meta.text}`}>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ background: meta.dot }} />
                <span className="text-[10px] font-bold">{p.label}</span>
              </div>
              <div className="text-[9px] text-slate-500 mt-1 leading-snug">{p.desc}</div>
              <div className="text-[9px] text-slate-400 mt-0.5">{p.duration}</div>
              {p.status === 'current' && (
                <span className="mt-1 inline-block text-[9px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded-full">{meta.label}</span>
              )}
            </div>
            {i < phases.length - 1 && <span className="mt-4 text-slate-300">→</span>}
          </div>
        );
      })}
    </div>
  );
}

function IndiaHeatmapChart({ chart }: { chart: CopilotChart }) {
  const states = chart.states ?? [];
  return (
    <div>
      <svg viewBox="0 0 100 100" className="w-full h-40 rounded-lg bg-gradient-to-br from-emerald-50 to-teal-50 [&>*]:cursor-pointer">
        {states.map((s) => (
          <g key={s.code}>
            <title>{`${s.ingredient} (${s.state}) — ${s.status}`}</title>
            <circle cx={s.x_norm * 100} cy={s.y_norm * 100} r={3.4} fill={s.status === 'verified' ? '#10B981' : '#0EA5E9'} opacity={0.9} stroke="#fff" strokeWidth={0.8} />
          </g>
        ))}
      </svg>
      <div className="flex items-center justify-center gap-4 mt-1.5 text-[9px] text-slate-500">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> Verified</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-sky-500" /> Supplier confirmed</span>
        <span className="flex items-center gap-1"><ListChecks className="w-3 h-3" /> {states.length} states traced</span>
      </div>
    </div>
  );
}

function RiskMatrixChart({ chart }: { chart: CopilotChart }) {
  const cols = [
    { key: 'Safe', color: '#10B981', bg: 'bg-emerald-500/10', border: 'border-emerald-400', note: 'Structure/function safe' },
    { key: 'Review', color: '#F59E0B', bg: 'bg-amber-500/10', border: 'border-amber-400', note: 'Needs review' },
    { key: 'High Risk', color: '#EF4444', bg: 'bg-red-500/10', border: 'border-red-400', note: 'Drug classification risk' },
  ];
  const current = chart.current ?? 0;
  return (
    <div className="grid grid-cols-3 gap-1.5 py-1">
      {cols.map((c, ci) => {
        const count = chart.values[ci] ?? 0;
        const active = ci === current;
        return (
          <div key={c.key} className={`rounded-xl border p-2 text-center ${active ? `${c.border} bg-white shadow-sm` : 'border-slate-150 bg-white/60'}`}>
            <div className="text-lg font-black" style={{ color: c.color }}>{count}</div>
            <div className="text-[10px] font-bold text-slate-700">{c.key}</div>
            <div className="text-[9px] text-slate-400">{c.note}</div>
            {active && <div className="mt-1 text-[9px] font-bold text-slate-600">◄ {chart.current_label ?? 'current'}</div>}
          </div>
        );
      })}
    </div>
  );
}

function OpportunityHeatmapChart({ chart }: { chart: CopilotChart }) {
  const herbs = chart.herbs ?? [];
  const forms = chart.forms ?? [];
  const cells = chart.cells ?? [];
  const colors = chart.colors ?? {};
  const cellFor = (herb: string, form: string) => cells.find((c) => c.herb === herb && c.form === form);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[10px] border-separate border-spacing-1">
        <thead>
          <tr>
            <th className="text-left text-slate-500 font-semibold px-1">Ingredient</th>
            {forms.map((f) => <th key={f} className="text-center text-slate-500 font-semibold">{f}</th>)}
          </tr>
        </thead>
        <tbody>
          {herbs.map((herb) => {
            const rowColor = cellFor(herb, forms[0])?.color;
            return (
              <tr key={herb}>
                <td className="font-bold text-slate-700 px-1 whitespace-nowrap" style={{ color: rowColor }}>{herb}</td>
                {forms.map((form) => {
                  const cell = cellFor(herb, form);
                  const fill = cell?.color ?? colors[cell?.value ?? ''] ?? '#e2e8f0';
                  return (
                    <td key={form} className="text-center">
                      <div
                        className="rounded-lg px-1.5 py-2 min-w-[4.2rem] font-bold text-white"
                        style={{ background: fill }}
                        title={cell?.rationale}
                      >
                        {cell?.value ?? '—'}
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="flex items-center justify-center gap-3 mt-1 text-[9px] text-slate-500">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> Crowded</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> Medium</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> Opportunity</span>
      </div>
    </div>
  );
}

const CHART_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pie: { label: 'Pie Chart', color: 'bg-blue-100 text-blue-700 border-blue-300', icon: <PieChartIcon className="w-3.5 h-3.5" /> },
  doughnut: { label: 'Doughnut Chart', color: 'bg-blue-100 text-blue-700 border-blue-300', icon: <PieChartIcon className="w-3.5 h-3.5" /> },
  radar: { label: 'Radar Chart', color: 'bg-violet-100 text-violet-700 border-violet-300', icon: <RadarIcon className="w-3.5 h-3.5" /> },
  bar_h: { label: 'Horizontal Bar Chart', color: 'bg-emerald-100 text-emerald-700 border-emerald-300', icon: <BarChart3 className="w-3.5 h-3.5" /> },
  bar: { label: 'Bar Chart', color: 'bg-emerald-100 text-emerald-700 border-emerald-300', icon: <BarChart3 className="w-3.5 h-3.5" /> },
  gauge: { label: 'Readiness Gauge', color: 'bg-amber-100 text-amber-700 border-amber-300', icon: <Gauge className="w-3.5 h-3.5" /> },
  timeline: { label: 'Timeline', color: 'bg-sky-100 text-sky-700 border-sky-300', icon: <GitBranch className="w-3.5 h-3.5" /> },
  india_heatmap: { label: 'India Sourcing Heatmap', color: 'bg-teal-100 text-teal-700 border-teal-300', icon: <MapPin className="w-3.5 h-3.5" /> },
  risk_matrix: { label: 'Risk Matrix', color: 'bg-red-100 text-red-700 border-red-300', icon: <ShieldQuestion className="w-3.5 h-3.5" /> },
  opportunity_heatmap: { label: 'Opportunity Heatmap', color: 'bg-lime-100 text-lime-700 border-lime-300', icon: <Table2 className="w-3.5 h-3.5" /> },
};

function ChartRenderer({ chart }: { chart: CopilotChart }) {
  const [open, setOpen] = useState(false);

  // Only render charts that actually contain data
  if (!chart || !chart.labels || chart.labels.length === 0 || !chart.values || chart.values.length === 0) {
    return null;
  }
  const data = chart.labels.map((label, i) => ({ name: label, value: chart.values[i] || 0 }));
  const meta = CHART_META[chart.type] ?? CHART_META.bar;
  const hasInsights = (chart.description && chart.description.length > 0) || (chart.insights && chart.insights.length > 0);

  let body: React.ReactNode = null;
  switch (chart.type) {
    case 'doughnut':
    case 'pie':
      body = (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={chart.type === 'doughnut' ? 40 : 0} outerRadius={62} paddingAngle={2}>
                {data.map((entry, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 12, fontSize: 11, boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}
                itemStyle={{ color: '#0f172a' }}
                labelStyle={{ color: '#334155' }}
              />
              <Legend wrapperStyle={{ fontSize: 10 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      );
      break;
    case 'radar':
      body = (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={data} outerRadius="70%">
              <PolarGrid stroke="#cbd5e1" />
              <PolarAngleAxis dataKey="name" tick={{ fill: '#475569', fontSize: 9 }} />
              <Radar dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.32} strokeWidth={1.5} />
              <Tooltip
                contentStyle={{ background: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 12, fontSize: 11, boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}
                itemStyle={{ color: '#0f172a' }}
                labelStyle={{ color: '#334155' }}
              />
            </RadarChart>
          </ResponsiveContainer>
          <div className="text-center text-[9px] text-slate-400 mt-1">{chart.title} — dimensions scored</div>
        </div>
      );
      break;
    case 'bar_h':
      body = (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <RCBarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 9 }} axisLine={false} tickLine={false} label={{ value: 'Score (0–100)', position: 'insideBottom', fontSize: 9, fill: '#94a3b8' }} />
              <YAxis type="category" dataKey="name" width={92} tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 12, fontSize: 11, boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}
                itemStyle={{ color: '#0f172a' }}
                cursor={{ fill: 'rgba(16,185,129,0.08)' }}
              />
              <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                {data.map((entry, i) => <Cell key={i} fill={(entry.value as number) >= 50 ? '#ef4444' : ((entry.value as number) >= 25 ? '#f59e0b' : '#34d399')} />)}
              </Bar>
            </RCBarChart>
          </ResponsiveContainer>
        </div>
      );
      break;
    case 'gauge':
      body = (
        <div className="flex flex-col items-center justify-center py-1 gap-1">
          <ReadinessGauge value={chart.values[0] || 0} label={chart.title} size={180} />
        </div>
      );
      break;
    case 'timeline':
      body = <TimelineChart chart={chart} />;
      break;
    case 'india_heatmap':
      body = <IndiaHeatmapChart chart={chart} />;
      break;
    case 'risk_matrix':
      body = <RiskMatrixChart chart={chart} />;
      break;
    case 'opportunity_heatmap':
      body = <OpportunityHeatmapChart chart={chart} />;
      break;
    default:
      body = (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <RCBarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} label={{ value: chart.title, position: 'insideBottom', offset: -2, fontSize: 9, fill: '#94a3b8' }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} allowDecimals={false} axisLine={false} tickLine={false} label={{ value: 'Value', angle: -90, position: 'insideLeft', fontSize: 9, fill: '#94a3b8' }} />
              <Tooltip
                contentStyle={{ background: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 12, fontSize: 11, boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}
                itemStyle={{ color: '#0f172a' }}
                labelStyle={{ color: '#334155' }}
                cursor={{ fill: 'rgba(16,185,129,0.08)' }}
              />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {data.map((entry, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
              </Bar>
            </RCBarChart>
          </ResponsiveContainer>
        </div>
      );
  }
  return (
    <div className={`overflow-hidden rounded-xl border border-slate-200 bg-white transition-colors ${open ? 'border-blue-400/60' : ''}`}>
      {/* Graph header — type badge + title */}
      <div className="px-3 pt-2.5 pb-1.5 border-b border-slate-100">
        <div className="flex items-center gap-1.5 mb-1.5">
          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border text-[9px] font-black uppercase tracking-wider ${meta.color}`}>
            {meta.icon} {meta.label}
          </span>
          {hasInsights && (
            <button
              type="button"
              onClick={() => setOpen((o) => !o)}
              className="ml-auto inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-slate-400 hover:text-blue-600 transition"
              aria-expanded={open}
            >
              {open ? 'Hide insight' : 'Insight'}
              <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>
          )}
        </div>
        <h4 className="text-xs font-black text-slate-900 leading-tight">{chart.title}</h4>
      </div>

      <div className="px-3 py-2">{body}</div>

      {open && hasInsights && (
        <div className="mx-3 mb-3 rounded-lg border border-blue-500/30 bg-[#0D1425] px-3 py-2.5 space-y-2">
          {chart.description && <p className="text-[10px] text-slate-300 leading-relaxed">{chart.description}</p>}
          {chart.insights && chart.insights.length > 0 && (
            <ul className="space-y-1">
              {chart.insights.map((ins, i) => (
                <li key={i} className="flex items-start gap-1.5 text-[10px] text-blue-200">
                  <Lightbulb className="w-3 h-3 text-amber-300 mt-0.5 flex-shrink-0" />
                  <span>{ins}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

const SPEECH_LOCALES: Record<string, string> = {
  en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN', ta: 'ta-IN', te: 'te-IN',
  kn: 'kn-IN', bn: 'bn-IN', gu: 'gu-IN', ml: 'ml-IN', sa: 'sa-IN',
};

function voiceLocale(code: string): string {
  return SPEECH_LOCALES[code] || code;
}

export default function AICopilot({ passportId, lang = 'en' }: AICopilotProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS);
  const [showSources, setShowSources] = useState<Record<number, boolean>>({});
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [voiceOutput, setVoiceOutput] = useState(false);
  const [speakingMsgId, setSpeakingMsgId] = useState<number | null>(null);
  const pendingTranscript = useRef('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const voice = useVoiceAssistant({ lang: voiceLocale(lang) });

  useEffect(() => {
    getSuggestedQuestions().then((res) => {
      if (res?.questions?.length) setSuggestions(res.questions);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (voice.interim) {
      setInput(voice.interim);
    } else if (pendingTranscript.current) {
      setInput(pendingTranscript.current);
    }
  }, [voice.interim]);

  useEffect(() => {
    const onExternalQuestion = (e: Event) => {
      const q = (e as CustomEvent<string>).detail;
      if (q) handleSend(q);
    };
    window.addEventListener('ipsakti:copilot-question', onExternalQuestion);
    return () => window.removeEventListener('ipsakti:copilot-question', onExternalQuestion);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSend = async (text?: string) => {
    let question = text?.trim() ?? '';
    if (!question) {
      question = pendingTranscript.current.trim() || input.trim();
    }
    if (!question || isLoading) return;
    pendingTranscript.current = '';

    setMessages((prev) => [...prev, { role: 'user', content: question, timestamp: Date.now() }]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await askCopilot(question, passportId);
      const msg: Message = { role: 'assistant', content: res.answer, sources: res.sources, confidence: res.confidence, charts: res.charts, images: res.images, analysisCard: res.analysis_card, evidenceUsed: res.evidence_used, nextActions: res.next_actions, intent: res.intent, timestamp: Date.now() };
      setMessages((prev) => [...prev, msg]);
      if (voiceOutput && voice.synthSupported) {
        setSpeakingMsgId(messages.length + 1);
        voice.speak(res.answer, () => setSpeakingMsgId(null));
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please ensure the backend is running and try again.', timestamp: Date.now() },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceTranscript = (transcript: string) => {
    pendingTranscript.current = transcript;
    setInput(transcript);
    handleSend(transcript);
  };

  const handleMicToggle = () => {
    if (voice.isListening) {
      voice.stopListening();
      if (pendingTranscript.current) {
        handleVoiceTranscript(pendingTranscript.current);
        pendingTranscript.current = '';
      }
      return;
    }
    voice.clearError();
    voice.startListening(handleVoiceTranscript);
  };

  const readAloud = (msg: Message, index: number) => {
    if (speakingMsgId === index) {
      voice.cancelSpeech();
      setSpeakingMsgId(null);
      return;
    }
    voice.speak(msg.content, () => setSpeakingMsgId(null));
    setSpeakingMsgId(index);
  };

  const copyText = async (index: number, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(index);
      setTimeout(() => setCopiedId(null), 1500);
    } catch {}
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-5 animate-slide-up">
      {/* Chat panel */}
      <GlassCard className="flex flex-col overflow-hidden !p-0 h-[calc(100vh-240px)] min-h-[520px]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-emerald-200 bg-emerald-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 flex items-center gap-2">
                AI Copilot <Badge variant="info" dot><Sparkles className="w-3 h-3" /> RAG-Powered</Badge>
              </div>
              <div className="text-[10px] text-slate-500">Retrieval-grounded · rule-verified · never answers from memory</div>
            </div>
          </div>
          {voice.synthSupported && (
            <button
              onClick={() => setVoiceOutput((v) => !v)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[11px] font-semibold transition ${
                voiceOutput
                  ? 'bg-blue-100 border-blue-400 text-blue-600'
                  : 'bg-emerald-50 border-emerald-200 text-slate-500 hover:text-slate-700'
              }`}
              title={voiceOutput ? 'Mute voice replies' : 'Hear replies read aloud'}
            >
              {voiceOutput ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
              Voice {voiceOutput ? 'On' : 'Off'}
            </button>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-transparent">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center gap-6 py-10">
              <div className="text-center">
                <div className="relative inline-block mb-4">
                  <HerbSprig className="w-9 h-9 text-emerald-500 absolute -top-4 -left-7 opacity-80" />
                  <TulsiLeaf className="w-6 h-6 text-amber-500 absolute -bottom-3 -right-7 opacity-90" />
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-700 border-4 border-emerald-100 shadow-lg shadow-emerald-900/20 flex items-center justify-center">
                    <Bot className="w-8 h-8 text-white" />
                  </div>
                </div>
                <h3 className="text-lg font-bold text-slate-900 font-display mb-2">Ask IP-SAKTI Anything</h3>
                <div className="flex items-center justify-center gap-2.5 mb-1.5">
                  <TulsiLeaf className="w-4 h-4 text-emerald-600" />
                  <TurmericRoot className="w-4 h-4 text-amber-600" />
                  <MortarPestle className="w-4 h-4 text-emerald-700" />
                  <TurmericRoot className="w-4 h-4 text-amber-600" />
                  <TulsiLeaf className="w-4 h-4 text-emerald-600" />
                </div>
                <p className="text-sm text-slate-500 max-w-md">
                  Patentability, regulatory compliance, evidence requirements — grounded in retrieved sources.
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2 max-w-xl">
                {suggestions.map((sug) => (
                  <button key={sug} onClick={() => handleSend(sug)} className="px-3 py-2 text-xs bg-emerald-50 hover:bg-blue-100 border border-emerald-200 hover:border-blue-400 rounded-xl text-slate-600 hover:text-blue-600 transition">
                    {sug}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-white" />
                </div>
              )}
              <div className={`max-w-[78%] ${msg.role === 'user' ? 'order-first items-end' : ''}`}>
                {msg.role === 'assistant' && msg.analysisCard && (
                  <div className="mb-2 rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white p-3.5 shadow-sm">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-1.5">
                        {msg.analysisCard.verification_badge === 'Insufficient Evidence' ? (
                          <AlertTriangle className="w-4 h-4 text-amber-600" />
                        ) : (
                          <ShieldCheck className="w-4 h-4 text-emerald-600" />
                        )}
                        <span className={`text-[11px] font-bold ${msg.analysisCard.verification_badge === 'Insufficient Evidence' ? 'text-amber-700' : 'text-emerald-700'}`}>
                          {msg.analysisCard.verification_badge}
                        </span>
                      </div>
                      {msg.intent && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">
                          <Target className="w-3 h-3" /> {msg.intent.label}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 mt-2.5">
                      <div className="flex-1">
                        <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                          <span>Confidence</span>
                          <span className="font-bold text-slate-700">{msg.analysisCard.confidence_pct}%</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{ width: `${Math.min(100, msg.analysisCard.confidence_pct)}%`, background: msg.analysisCard.confidence_pct >= 70 ? '#10B981' : msg.analysisCard.confidence_pct >= 40 ? '#F59E0B' : '#EF4444' }}
                          />
                        </div>
                      </div>
                      {msg.analysisCard.patent_readiness !== null && msg.analysisCard.patent_readiness !== undefined && (
                        <div className="text-center px-3">
                          <div className={`text-2xl font-black leading-none ${msg.analysisCard.patent_readiness >= 70 ? 'text-emerald-600' : msg.analysisCard.patent_readiness >= 40 ? 'text-amber-600' : 'text-red-500'}`}>
                            {msg.analysisCard.patent_readiness}
                          </div>
                          <div className="text-[9px] text-slate-500 font-semibold mt-0.5">Readiness</div>
                        </div>
                      )}
                      <div className="text-center px-3 border-l border-slate-200">
                        <div className="text-[10px] text-slate-500 font-semibold mb-0.5">Risk</div>
                        <span className={`inline-block text-[11px] font-bold px-2 py-0.5 rounded-full ${msg.analysisCard.risk_level === 'High' ? 'bg-red-100 text-red-700' : msg.analysisCard.risk_level === 'Moderate' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                          {msg.analysisCard.risk_level}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                <div className={`px-4 py-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-blue-100 border border-blue-200 text-blue-800' : 'bg-emerald-50 border border-emerald-200 text-slate-700'}`}>
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>

                {msg.role === 'assistant' && msg.evidenceUsed && msg.evidenceUsed.length > 0 && (
                  <div className="mt-2">
                    <div className="flex items-center gap-1 text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                      <Library className="w-3 h-3 text-violet-600" /> Evidence used
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.evidenceUsed.map((ev, k) => (
                        <span key={k} className="inline-flex items-center gap-1 text-[10px] bg-white border border-violet-200 text-violet-700 px-2 py-1 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-violet-500" />
                          {ev.name}
                          <span className="text-violet-400 font-semibold">· {ev.type}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {msg.role === 'assistant' && msg.nextActions && msg.nextActions.length > 0 && (
                  <div className="mt-2 rounded-xl border border-slate-200 bg-white/80 p-3">
                    <div className="flex items-center gap-1 text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                      <ListChecks className="w-3 h-3 text-blue-600" /> Recommended next actions
                    </div>
                    <ol className="space-y-1">
                      {msg.nextActions.map((act, k) => (
                        <li key={k} className="flex items-start gap-1.5 text-[10px] text-slate-600">
                          <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 text-[9px] font-bold flex items-center justify-center flex-shrink-0 mt-px">{k + 1}</span>
                          <span className="leading-relaxed">{act}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {msg.role === 'assistant' && msg.images && msg.images.length > 0 && (
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    {msg.images.map((src, j) => (
                      <div key={j} className="rounded-xl overflow-hidden border border-emerald-200 bg-emerald-50">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={src} alt={`Reference ${j + 1}`} className="w-full h-20 object-cover" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                      </div>
                    ))}
                  </div>
                )}

                {msg.role === 'assistant' && msg.charts && msg.charts.length > 0 && (
                  <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {msg.charts.filter((c) => c && c.labels && c.labels.length > 0 && c.values && c.values.length > 0).map((chart, j) => (
                      <div key={j} className="px-2 py-2 rounded-xl bg-emerald-50 border border-emerald-200">
                        <ChartRenderer chart={chart} />
                      </div>
                    ))}
                  </div>
                )}

                {msg.role === 'assistant' && (
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    {msg.confidence !== undefined && (
                      <Badge variant={confidenceTone(msg.confidence)} dot>Confidence {Math.round(msg.confidence * 100)}%</Badge>
                    )}
                    <button onClick={() => copyText(i, msg.content)} className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-blue-600 transition">
                      {copiedId === i ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      {copiedId === i ? 'Copied' : 'Copy'}
                    </button>
                    {voice.synthSupported && (
                      <button onClick={() => readAloud(msg, i)} className={`flex items-center gap-1 text-[10px] transition ${speakingMsgId === i ? 'text-blue-600' : 'text-slate-500 hover:text-blue-600'}`} title="Read aloud">
                        {speakingMsgId === i ? <AudioLines className="w-3.5 h-3.5 animate-pulse" /> : <Volume2 className="w-3.5 h-3.5" />}
                        {speakingMsgId === i ? 'Speaking' : 'Listen'}
                      </button>
                    )}
                    {msg.sources && msg.sources.length > 0 && (
                      <button onClick={() => setShowSources((p) => ({ ...p, [i]: !p[i] }))} className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-blue-600 transition">
                        <ChevronDown className={`w-3 h-3 transition-transform ${showSources[i] ? 'rotate-180' : ''}`} />
                        {msg.sources.length} sources used
                      </button>
                    )}
                  </div>
                )}

                {msg.role === 'assistant' && showSources[i] && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 space-y-2 animate-slide-up">
                    {msg.sources.map((src, j) => (
                      <button key={j} className="w-full text-left px-3 py-2 rounded-xl bg-emerald-50 border border-emerald-200 hover:border-blue-400 transition">
                        <div className="text-[10px] text-blue-600 font-semibold">{src.category}</div>
                        <div className="text-[10px] text-slate-500 truncate mt-0.5">{src.source}</div>
                        <div className="text-[10px] text-slate-500 mt-1 line-clamp-2">{src.content}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center flex-shrink-0 mt-1">
                  <User className="w-4 h-4 text-slate-500" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="px-4 py-3 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" /> Retrieving sources & reasoning...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-emerald-200">
          {voice.isListening && (
            <div className="mb-3 px-4 py-2.5 rounded-xl bg-red-500/[0.08] border border-red-500/30 flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-red-600 font-semibold">
                <Mic className="w-3.5 h-3.5 animate-pulse" /> Listening
                {voice.interim && <span className="text-red-700/80 font-normal max-w-[240px] truncate">— {voice.interim}</span>}
              </span>
              <span className="flex gap-1 ml-auto">
                {[0, 1, 2, 3].map((b) => (
                  <span key={b} className="w-0.5 h-4 rounded-full bg-red-400 animate-pulse" style={{ animationDelay: `${b * 0.15}s` }} />
                ))}
              </span>
              <button onClick={voice.stopListening} className="text-[10px] px-2 py-1 rounded-md bg-red-100 hover:bg-red-200 text-red-700 transition">Stop</button>
            </div>
          )}
          {voice.error && !voice.isListening && (
            <div className="mb-3 px-4 py-2.5 rounded-xl bg-amber-500/[0.08] border border-amber-500/40 text-[11px] text-amber-700 flex items-center justify-between gap-2">
              <span>{voice.error}</span>
              <button onClick={voice.clearError} className="text-amber-600 hover:text-slate-900">✕</button>
            </div>
          )}
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
            <button
              type="button"
              onClick={handleMicToggle}
              disabled={!voice.supported}
              title={voice.supported ? (voice.isListening ? 'Stop listening' : 'Ask with your voice') : 'Voice input not supported in this browser'}
              className={`w-11 h-11 rounded-xl flex items-center justify-center border shrink-0 transition ${
                voice.isListening
                  ? 'bg-red-100 border-red-300 text-red-600 animate-pulse'
                  : voice.supported
                    ? 'bg-emerald-50 border-emerald-200 text-slate-600 hover:border-blue-400 hover:text-blue-600'
                    : 'bg-emerald-50/50 border-emerald-200/50 text-slate-500 cursor-not-allowed'
              }`}
            >
              {voice.isListening ? <AudioLines className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type or speak — ask about patentability, compliance, evidence..."
              className="flex-1 px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-slate-900 placeholder-slate-500 focus:outline-none focus:border-blue-400"
            />
            <Button type="submit" variant="primary" disabled={isLoading || !input.trim()} className="!px-4">
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </GlassCard>

      {/* RAG Source Panel */}
      <div className="space-y-4">
        <GlassCard padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Library className="w-4 h-4 text-violet-600" />
            <h3 className="text-sm font-bold text-slate-900">Sources Used</h3>
          </div>
          <p className="text-[11px] text-slate-500 mb-3">Every answer cites verified authoritative sources.</p>
          <div className="space-y-2">
            {RAG_SOURCES.map((src) => (
              <button key={src.name} className="w-full text-left px-3.5 py-3 rounded-xl bg-emerald-50 border border-emerald-200 hover:border-violet-400 transition group">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-700 flex items-center gap-2">
                    <Library className="w-3.5 h-3.5 text-violet-600" /> {src.name}
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 mt-1">{src.category}</div>
              </button>
            ))}
          </div>
        </GlassCard>

        <GlassCard padding="md" className="border-blue-500/20">
          <div className="flex items-start gap-2 text-[11px] text-slate-500">
            <Sparkles className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
            <p>AI Copilot provides informational guidance. Always consult a qualified patent agent for final decisions.</p>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}