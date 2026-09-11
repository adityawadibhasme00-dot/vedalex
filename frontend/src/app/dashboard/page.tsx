'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/AuthContext';
import { useLang } from '../../lib/LangContext';
import InnovationPassportView from '../../components/InnovationPassportView';
import InnovationPassportForm from '../../components/InnovationPassportForm';
import PatentAnalysis from '../../components/PatentAnalysis';
import EvidenceMatrix from '../../components/EvidenceMatrix';
import AICopilot from '../../components/AICopilot';
import ClarificationAlert from '../../components/ClarificationAlert';
import JurisdictionMatrix from '../../components/JurisdictionMatrix';
import CitationPopover from '../../components/CitationPopover';
import ProvenanceGraph from '../../components/ProvenanceGraph';
import KnowledgeGraphView from '../../components/KnowledgeGraphView';
import DocumentAnalyzer from '../../components/DocumentAnalyzer';
import DossierView from '../../components/DossierView';
import WhatIfSimulator from '../../components/WhatIfSimulator';
import SaktiAssistant from '../../components/SaktiAssistant';
import LeafRain from '../../components/PixelLeafRain';
import { ClaimSafetyIntelligence } from '../../components/ClaimSafetyIntelligence';
import { EvidenceQualityIntelligence } from '../../components/EvidenceQualityIntelligence';
import { BioResourceIntelligence } from '../../components/BioResourceIntelligence';
import { ProductClassifier } from '../../components/ProductClassifier';
import { ExportReadiness } from '../../components/ExportReadiness';
import { TerminologyMapper } from '../../components/TerminologyMapper';
import { RoadmapView } from '../../components/RoadmapView';
import { FeatureHub } from '../../components/FeatureHub';
import { GlassCard } from '../../components/ui/GlassCard';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { PageHeader } from '../../components/ui/PageHeader';
import DashboardOverview from '../../components/DashboardOverview';
import VoiceAssistant from '../../components/VoiceAssistant';

import {
  InnovationPassport, AssessmentResponse, ClarificationQuery,
  StatutoryCitation, EvidenceGapSummary, ProvenanceGraphData,
  WhatIfSimulationResponse,
} from '../../types';
import {
  createPassportFromIntake, evaluateAssessment, getClarifications,
  getProvenanceGraph, getEvidenceGaps, sanitizeDocument,
  simulateWhatIf,
} from '../../lib/api';
import { exportInnovationPassportPDF } from '../../lib/exportManager';
import { saveOfflineDraft, getOfflineDrafts } from '../../lib/offlineStorage';
import { t } from '../../lib/i18n';

import {
  LayoutDashboard, FileText, Search, ClipboardList, Bot, FileDown,
  Settings, Globe, GitBranch, Lock, LogOut, Menu, Home,
  ChevronLeft, Bell, Sparkles, Plus, Leaf, RefreshCw, ShieldCheck, FlaskConical,
  Sprout, Layers, FileBadge, BookMarked, Route,
} from 'lucide-react';

import Navbar from '../../components/Navbar';
import { HerbSprig, TulsiLeaf, TurmericRoot } from '../../components/BotanicalDecor';

const NAV_ITEMS = [
  { id: 'overview',    labelKey: 'dashboard',        icon: LayoutDashboard, color: 'text-blue-600' },
  { id: 'passport',    labelKey: 'innovation_passport', icon: FileText,     color: 'text-emerald-600' },
  { id: 'patent',      labelKey: 'patent_analysis', icon: Search,          color: 'text-blue-600' },
  { id: 'evidence',    labelKey: 'evidence_matrix',  icon: ClipboardList,   color: 'text-amber-600' },
  { id: 'claimintel',  labelKey: 'claim_safety_intelligence', icon: ShieldCheck, color: 'text-red-600' },
  { id: 'evidintel',   labelKey: 'evidence_quality_intelligence', icon: FlaskConical, color: 'text-cyan-600' },
  { id: 'biores',      labelKey: 'bio_resource_intelligence', icon: Sprout,       color: 'text-emerald-600' },
  { id: 'classify',    labelKey: 'product_classifier',     icon: Layers,         color: 'text-violet-600' },
  { id: 'market',      labelKey: 'export_readiness',       icon: FileBadge,      color: 'text-blue-600' },
  { id: 'terms',       labelKey: 'terminology_mapper',     icon: BookMarked,     color: 'text-amber-600' },
  { id: 'roadmap',     labelKey: 'regulatory_roadmap',     icon: Route,          color: 'text-violet-600' },
  { id: 'copilot',     labelKey: 'ai_copilot',       icon: Bot,             color: 'text-violet-600' },
  { id: 'dossier',     labelKey: 'dossier_export',   icon: FileDown,        color: 'text-blue-600' },
  { id: 'matrix',      labelKey: 'jurisdiction_matrix', icon: Globe,        color: 'text-blue-600' },
  { id: 'provenance',  labelKey: 'provenance_graph', icon: GitBranch,       color: 'text-violet-600' },
  { id: 'whatif',      labelKey: 'what_if',          icon: RefreshCw,       color: 'text-amber-600' },
  { id: 'doc_analyzer',labelKey: 'doc_ocr',          icon: Lock,            color: 'text-pink-600' },
  { id: 'settings',    labelKey: 'settings_title',   icon: Settings,        color: 'text-slate-500' },
] as const;

type TabId = typeof NAV_ITEMS[number]['id'];

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const { lang, setLang } = useLang();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isOnline, setIsOnline] = useState(true);
  const [offlineDraftCount, setOfflineDraftCount] = useState(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [prefs, setPrefs] = useState<Record<string, boolean>>({ emailNotifications: false, evidenceReminders: true, autoLanguage: true });
  const [prefsToast, setPrefsToast] = useState('');

  const togglePref = (key: string) => { setPrefs((p) => ({ ...p, [key]: !p[key] })); };

  useEffect(() => {
    try { const saved = JSON.parse(localStorage.getItem('ipsakti_preferences') || 'null'); if (saved) setPrefs((p) => ({ ...p, ...saved })); } catch {}
  }, []);

  useEffect(() => { localStorage.setItem('ipsakti_preferences', JSON.stringify(prefs)); }, [prefs]);

  const [passport, setPassport] = useState<InnovationPassport | null>(null);
  const [assessment, setAssessment] = useState<AssessmentResponse | null>(null);
  const [clarifications, setClarifications] = useState<ClarificationQuery[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<StatutoryCitation | null>(null);
  const [provenanceData, setProvenanceData] = useState<ProvenanceGraphData | null>(null);
  const [evidenceSummary, setEvidenceSummary] = useState<EvidenceGapSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfSimulationResponse | null>(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);

  useEffect(() => {
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    setOfflineDraftCount(getOfflineDrafts().length);
    return () => { window.removeEventListener('online', onOnline); window.removeEventListener('offline', onOffline); };
  }, []);

  useEffect(() => {
    handleIntakeSubmit(
      'अश्वगंधा + ब्राह्मी फॉर्म्युलेशन, दावा: शांत झोपेसाठी उपयुक्त, लक्ष्य बाजार: भारत, अमेरिका, कॅनडा',
      'Ashwagandha & Brahmi Restful Sleep Formulation'
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleIntakeSubmit = useCallback(async (rawText: string, title?: string) => {
    setIsLoading(true);
    try {
      const newPassport = await createPassportFromIntake(rawText, lang, title);
      setPassport(newPassport);
      saveOfflineDraft(newPassport);
      setOfflineDraftCount(getOfflineDrafts().length);
      const queries = await getClarifications(newPassport.id);
      setClarifications(queries);
      const evalRes = await evaluateAssessment(newPassport.id, ['India', 'United States', 'Canada'], lang);
      setAssessment(evalRes);
      const gaps = await getEvidenceGaps(newPassport.id);
      setEvidenceSummary(gaps);
      const prov = await getProvenanceGraph(newPassport.id, 'India');
      setProvenanceData(prov);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [lang]);

  const handleClarificationResolve = async (queryId: string, selectedOption: string) => {
    if (!passport) return;
    const updated = { ...passport, process_description: `${passport.process_description} | Solvent: ${selectedOption}`, unresolved_clarifications: [] };
    setPassport(updated);
    setClarifications([]);
    const evalRes = await evaluateAssessment(passport.id, ['India', 'United States', 'Canada'], lang);
    setAssessment(evalRes);
  };

  const handleExportPDF = () => { if (passport) exportInnovationPassportPDF(passport, assessment?.findings); };
  const handleLogout = () => { logout(); router.push('/login'); };

  const voiceFeedback = (message: string) => {
    window.dispatchEvent(new CustomEvent('ipsakti:voice-feedback', { detail: message }));
  };

  const parseVoiceCommand = (raw: string): { tab: TabId | null; query: string | null } => {
    const low = raw.toLowerCase();

    if (/\blog\s*out\b|logout|sign\s*out|bahar|baher/.test(low)) {
      handleLogout();
      voiceFeedback('Logging you out now.');
      return { tab: null, query: null };
    }

    const exportPdf = /\b(export|download)\s+(?:as\s+)?pdf\b|download\s+pdf/.test(low);
    if (exportPdf) {
      handleExportPDF();
      voiceFeedback('Exporting your passport PDF.');
      return { tab: null, query: null };
    }
    if (/\bdossier|exports?|download report/.test(low)) {
      navigate('dossier');
      voiceFeedback('Opening Dossier Export.');
      return { tab: 'dossier', query: null };
    }

    let query: string | null = null;
    const qMatch = raw.match(/(?:search|ask|query|look up|find)\s+(?:for|about|on)?\s*[:,-]?\s*(.+)/i);
    if (qMatch && qMatch[1]) {
      query = qMatch[1];
      query = query.replace(/^(copilot)\s+(and\s+)?(search|ask|query|find)\s+(for|about|on)?\s*[:,-]?\s*/i, '');
    }

    let tab: TabId | null = null;
    const tabEntries: [string, TabId, RegExp][] = [
      ['dashboard', 'overview', /dashboard|home|overview|main page|landing/i],
      ['passport', 'passport', /passport|innovation passport|create passport/i],
      ['patent', 'patent', /patent|patentability|prior art/i],
      ['evidence', 'evidence', /evidence|matrix|gaps? in evidence/i],
      ['claimintel', 'claimintel', /claim|safety|misleading|label/i],
      ['evidintel', 'evidintel', /pharmacopoeia|quality/i],
      ['biores', 'biores', /bio.?resource|plant intelligence|sourcing|abs graph|medicinal plant/i],
      ['classify', 'classify', /classify|classifier|pathway|aahara|which category|product class/i],
      ['market', 'market', /export readiness|market entry|market readiness|which market|market first|export plan/i],
      ['terms', 'terms', /terminology|mapper|canonical|rag|botanical (names?|synonyms)/i],
      ['roadmap', 'roadmap', /roadmap|regulatory roadmap|critical path|timeline|phases|filing journey/i],
      ['copilot', 'copilot', /copilot|ai|assistant|search anything/i],
      ['dossier', 'dossier', /dossier|export|download|report/i],
      ['matrix', 'matrix', /jurisdiction|country|usa|us|india|canada/i],
      ['provenance', 'provenance', /provenance|graph|sources? used|citation/i],
      ['doc_analyzer', 'doc_analyzer', /ocr|document|scan|upload|sanitize/i],
      ['settings', 'settings', /setting|profile|account|preferenc/i],
    ];
    const tabMatch = tabEntries.find(([, , re]) => re.test(low));

    if (tabMatch) tab = tabMatch[1];

    // A bare "ask/query <something>" with no tab match goes to the AI
    // Copilot so the spoken question is actually answered.
    if (query && !tab) {
      tab = 'copilot';
    }

    if (tab && tab !== activeTab) navigate(tab);

    if (tab) {
      voiceFeedback(`Opening ${tabMatch ? tabMatch[0] : tab} tab.`);
    }

    if (tab === 'copilot' && query) {
      // Give the freshly-mounted AICopilot time to attach its listener
      // before dispatching the spoken question.
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('ipsakti:copilot-question', { detail: query }));
      }, 400);
    }

    return { tab, query };
  };

  const parseVoiceCommandRef = useRef(parseVoiceCommand);
  useEffect(() => {
    parseVoiceCommandRef.current = parseVoiceCommand;
  });

  useEffect(() => {
    const onVoice = (e: Event) => {
      const raw = (e as CustomEvent<string>).detail || '';
      parseVoiceCommandRef.current(raw);
    };
    window.addEventListener('ipsakti:voice', onVoice);
    return () => window.removeEventListener('ipsakti:voice', onVoice);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const navigate = (tab: TabId) => {
    setActiveTab(tab);
    setMobileNavOpen(false);
  };

  const handleWhatIfSimulate = async (mutatedClaims: string[]) => {
    if (!passport) return;
    setWhatIfLoading(true);
    try {
      const res = await simulateWhatIf(passport.id, mutatedClaims);
      setWhatIfResult(res);
    } catch {
      setWhatIfResult(null);
    } finally {
      setWhatIfLoading(false);
    }
  };

  const handleFeatureOpen = (id: string) => {
    const map: Record<string, TabId> = {
      disclosure: 'doc_analyzer',
      fto: 'patent',
      label: 'passport',
      abs: 'provenance',
      'evidence-matrix': 'evidence',
      'claim-safety': 'claimintel',
      'evidence-quality': 'evidintel',
      'bio-resource': 'biores',
      'product-classifier': 'classify',
      'export-readiness': 'market',
      'terminology-mapper': 'terms',
      roadmap: 'roadmap',
      dossier: 'dossier',
      expert: 'overview',
      'what-if': 'whatif',
    };
    navigate(map[id] || 'overview');
  };

  const ensurePassportComputed = useCallback(async () => {
    if (!passport) return;
    if (!assessment) {
      try { setAssessment(await evaluateAssessment(passport.id, ['India', 'United States', 'Canada'], lang)); } catch {}
    }
    if (!provenanceData) {
      try { setProvenanceData(await getProvenanceGraph(passport.id, 'India')); } catch {}
    }
  }, [passport, assessment, provenanceData, lang]);

  useEffect(() => {
    if (activeTab === 'matrix' || activeTab === 'provenance') ensurePassportComputed();
  }, [activeTab, ensurePassportComputed]);

  return (
    <div className="min-h-screen flex font-sans relative text-slate-800">
      <LeafRain />
      {/* ─── Sidebar ─────────────────────────────────────────────── */}
      <aside className={`
        fixed left-0 top-0 h-full z-40 flex flex-col
        hidden lg:flex
        transition-all duration-300 ease-in-out
        ${sidebarOpen ? 'w-64' : 'w-[72px]'}
        border-r border-emerald-200 bg-white/95 backdrop-blur-xl shadow-lg shadow-emerald-900/[0.04]
      `}>
        <div className="flex items-center gap-3 px-4 py-5 h-[68px]">
          <button
            className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-600 to-emerald-700 flex items-center justify-center text-white shadow-md shadow-emerald-900/20"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <Leaf className="w-5 h-5 text-white" />
          </button>
          {sidebarOpen && (
            <div className="overflow-hidden">
              <div className="flex items-center gap-1.5 text-sm font-bold text-slate-900 font-display whitespace-nowrap">
                IP-SAKTI <TulsiLeaf className="w-3.5 h-3.5 text-emerald-600" />
              </div>
              <div className="text-[9px] font-medium text-emerald-700 whitespace-nowrap">आयुर्वेद • आईपी सुरक्षा</div>
            </div>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto py-3 space-y-1 px-2.5 no-scrollbar">
          <button
            onClick={() => router.push('/')}
            title={!sidebarOpen ? t('home_title', lang) : undefined}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all group relative text-slate-600 hover:text-emerald-700 hover:bg-emerald-50 border border-transparent"
          >
            <Home className="w-[18px] h-[18px] flex-shrink-0" />
            {sidebarOpen && (
              <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">{t('home', lang)}</span>
            )}
            {!sidebarOpen && (
              <div className="absolute left-full ml-2 px-2 py-1 bg-white border border-emerald-200 rounded-lg text-xs text-slate-700 whitespace-nowrap opacity-0 group-hover:opacity-100 transition pointer-events-none z-50 shadow-xl">
                {t('home', lang)}
              </div>
            )}
          </button>
          {NAV_ITEMS.map(item => {
            const isActive = activeTab === item.id;
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => navigate(item.id)}
                title={!sidebarOpen ? t(item.labelKey, lang) : undefined}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all group relative
                  ${isActive
                    ? 'bg-emerald-50 border border-emerald-300 text-emerald-900 font-semibold'
                    : 'text-slate-600 hover:text-emerald-800 hover:bg-emerald-50 border border-transparent'
                  }
                `}
              >
                {isActive && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-full bg-gradient-to-b from-emerald-500 to-teal-500" />}
                <Icon className={`w-[18px] h-[18px] flex-shrink-0 ${isActive ? item.color : ''}`} />
                {sidebarOpen && (
                  <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">{t(item.labelKey, lang)}</span>
                )}
                {!sidebarOpen && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-white border border-emerald-200 rounded-lg text-xs text-slate-700 whitespace-nowrap opacity-0 group-hover:opacity-100 transition pointer-events-none z-50 shadow-xl">
                    {t(item.labelKey, lang)}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        <div className="border-t border-emerald-100 p-3 space-y-2">
          {sidebarOpen && (
            <div className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs ${isOnline ? 'text-emerald-600' : 'text-amber-600'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              {isOnline ? t('online', lang) : `${t('offline', lang)} (${offlineDraftCount} drafts)`}
            </div>
          )}
          <div className="flex items-center gap-2.5 px-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-600 to-emerald-700 flex items-center justify-center flex-shrink-0 text-white font-bold text-xs">
              {user?.name?.[0] || 'U'}
            </div>
            {sidebarOpen && (
              <div className="flex-1 overflow-hidden">
                <div className="text-xs font-semibold text-slate-900 truncate">{user?.name}</div>
                <div className="text-[10px] text-slate-500 truncate">{user?.role}</div>
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-red-600 hover:bg-red-50 hover:text-red-700 transition"
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            {sidebarOpen && <span>{t('sign_out', lang)}</span>}
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-4 py-3 bg-white/95 backdrop-blur-xl border-b border-emerald-200">
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg hover:bg-emerald-50 text-slate-600">
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-600 to-emerald-700 flex items-center justify-center">
            <Leaf className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-bold text-slate-900 font-display">IP-SAKTI</span>
        </div>
        <button className="p-1.5 rounded-lg hover:bg-emerald-50 text-slate-600">
          <Bell className="w-5 h-5" />
        </button>
      </div>

      {/* Mobile nav drawer */}
      {!sidebarOpen && mobileNavOpen && (
        <div className="lg:hidden fixed inset-0 z-40" onClick={() => setMobileNavOpen(false)}>
          <div className="absolute inset-0 bg-emerald-900/40" />
          <div className="absolute left-0 top-0 h-full w-64 bg-white border-r border-emerald-200 p-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-bold text-slate-900 font-display">IP-SAKTI</span>
              <button onClick={() => setMobileNavOpen(false)} className="text-slate-500"><ChevronLeft className="w-5 h-5" /></button>
            </div>
            <nav className="space-y-1">
              <button onClick={() => router.push('/')} className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left text-sm text-slate-600 hover:bg-emerald-50`}>
                <Home className="w-[18px] h-[18px]" /> {t('home', lang)}
              </button>
              {NAV_ITEMS.map(item => {
                const isActive = activeTab === item.id;
                const Icon = item.icon;
                return (
                  <button key={item.id} onClick={() => navigate(item.id)} className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left text-sm ${isActive ? 'bg-emerald-50 text-emerald-900 font-semibold' : 'text-slate-600 hover:bg-emerald-50'}`}>
                    <Icon className="w-[18px] h-[18px]" /> {t(item.labelKey, lang)}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      )}

      {/* ─── Main ─────────────────────────────────────────────── */}
      <div className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ${sidebarOpen ? 'lg:ml-64' : 'lg:ml-[72px]'} pt-[60px] lg:pt-0`}>
        <Navbar
          isOnline={isOnline}
          offlineDraftCount={offlineDraftCount}
        />

        {isLoading && (
          <div className="h-0.5 bg-emerald-100 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-500 animate-shimmer" />
          </div>
        )}

        <main className="flex-1 p-4 md:p-6 space-y-6 relative z-10 overflow-auto">
          {clarifications.length > 0 && (
            <ClarificationAlert clarifications={clarifications} currentLang={lang} onResolve={handleClarificationResolve} />
          )}

          {activeTab === 'overview' && (
            <>
              <DashboardOverview passport={passport} onNavigateTab={navigate} />
              <div className="pt-2">
                <GlassCard padding="md" className="mb-6 relative overflow-hidden">
                  <HerbSprig className="w-16 h-16 text-emerald-500/15 absolute -right-2 -bottom-3 rotate-[25deg] pointer-events-none" />
                  <TurmericRoot className="w-10 h-10 text-amber-500/15 absolute right-16 bottom-1 pointer-events-none" />
                  <PageHeader
                    title="Create a New Innovation Passport"
                    subtitle="Import a formulation to start your Idea → Patent → Compliance journey"
                    icon={<Sparkles className="w-5 h-5" />}
                  />
                  <InnovationPassportForm
                    onSubmit={(data: any) => {
                      handleIntakeSubmit(data.raw_text || data.case_title, data.case_title || 'New Innovation');
                    }}
                    isLoading={isLoading}
                  />
                </GlassCard>
              </div>
              <FeatureHub onOpen={handleFeatureOpen} />
            </>
          )}

          {activeTab === 'passport' && (
            <div className="space-y-4">
              <PageHeader title={t('innovation_passport', lang)} subtitle="5-step guided intake to build your patent-ready profile" icon={<FileText className="w-5 h-5" />} />
              {passport ? (
                <InnovationPassportView
                  passport={passport}
                  onUpdatePassport={setPassport}
                  onIntakeSubmit={handleIntakeSubmit}
                  onSanitizeTest={(t) => sanitizeDocument(t, 'label.pdf')}
                  isLoading={isLoading}
                  currentLang={lang}
                />
              ) : (
                <GlassCard padding="lg"><Skeleton lines={6} /></GlassCard>
              )}
            </div>
          )}

          {activeTab === 'patent' && (
            <div className="space-y-4">
              <PageHeader title={t('patent_analysis', lang)} subtitle="Novelty · Inventive Step · Overall Readiness" icon={<Search className="w-5 h-5" />} />
              <PatentAnalysis passportId={passport?.id || ''} />
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-4">
              <PageHeader title={t('evidence_matrix', lang)} subtitle="Link claims to evidence with color-coded status" icon={<ClipboardList className="w-5 h-5" />} />
              <EvidenceMatrix
                initialRows={undefined}
                passportId={passport?.id}
                passport={passport}
                onStatusUpdate={(itemId, status) => {
                  if (passport) getEvidenceGaps(passport.id).then(setEvidenceSummary).catch(() => {});
                }}
              />
            </div>
          )}

          {activeTab === 'copilot' && (
            <div className="space-y-4">
              <PageHeader title={t('ai_copilot', lang)} subtitle="RAG-powered answers with cited sources & confidence" icon={<Bot className="w-5 h-5" />} />
              <AICopilot passportId={passport?.id} lang={lang} />
            </div>
          )}

          {activeTab === 'claimintel' && (
            <div className="space-y-4">
              <PageHeader title={t('claim_safety_intelligence', lang)} subtitle="Test claims against evidence & pharmacovigilance signals (Ayush Suraksha aware)" icon={<ShieldCheck className="w-5 h-5" />} />
              <ClaimSafetyIntelligence passportId={passport?.id} initialClaims={passport?.proposed_claims} />
            </div>
          )}

          {activeTab === 'evidintel' && (
            <div className="space-y-4">
              <PageHeader title={t('evidence_quality_intelligence', lang)} subtitle="Research evidence ladder + pharmacopoeia quality readiness" icon={<FlaskConical className="w-5 h-5" />} />
              <EvidenceQualityIntelligence passportId={passport?.id} />
            </div>
          )}

          {activeTab === 'biores' && (
            <div className="space-y-4">
              <PageHeader title={t('bio_resource_intelligence', lang)} subtitle="Provenance · conservation · ABS · TK · IP per plant" icon={<Sprout className="w-5 h-5" />} />
              <BioResourceIntelligence passportId={passport?.id} />
            </div>
          )}

          {activeTab === 'classify' && (
            <div className="space-y-4">
              <PageHeader title={t('product_classifier', lang)} subtitle="Likely regulatory class: ASU drug · Ayurveda Aahara · supplement · cosmetic" icon={<Layers className="w-5 h-5" />} />
              <ProductClassifier passportId={passport?.id} passport={passport} />
            </div>
          )}

          {activeTab === 'market' && (
            <div className="space-y-4">
              <PageHeader title={t('export_readiness', lang)} subtitle="India · United States · European Union · Canada gap comparison" icon={<FileBadge className="w-5 h-5" />} />
              <ExportReadiness passportId={passport?.id} />
            </div>
          )}

          {activeTab === 'terms' && (
            <div className="space-y-4">
              <PageHeader title={t('terminology_mapper', lang)} subtitle="Resolve all names of a botanical to one canonical RAG entity" icon={<BookMarked className="w-5 h-5" />} />
              <TerminologyMapper passportIngredients={passport?.ingredients?.map((i) => i.raw_name) || []} />
            </div>
          )}

          {activeTab === 'roadmap' && (
            <div className="space-y-4">
              <PageHeader title={t('regulatory_roadmap', lang)} subtitle="Prior art → ABS → Patent → Evidence → Compliance → Launch" icon={<Route className="w-5 h-5" />} />
              <RoadmapView passportId={passport?.id} />
            </div>
          )}

          {activeTab === 'dossier' && (
            <div className="space-y-4">
              <PageHeader title={t('dossier_export', lang)} subtitle="Generate filing-ready documents" icon={<FileDown className="w-5 h-5" />} />
              <DossierView passportId={passport?.id || ''} />
            </div>
          )}

          {activeTab === 'matrix' && (
            <div className="space-y-4">
              <PageHeader title={t('jurisdiction_matrix', lang)} subtitle="India · United States · Canada evaluation" icon={<Globe className="w-5 h-5" />} />
              <JurisdictionMatrix
                findings={assessment?.findings || []}
                onSelectCitation={setSelectedCitation}
                coverageMeterScore={assessment?.coverage_meter_score || 82}
              />
            </div>
          )}

          {activeTab === 'provenance' && (
            <div className="space-y-4">
              <PageHeader title={t('provenance_graph', lang)} subtitle="Trace regulatory reasoning with citations" icon={<GitBranch className="w-5 h-5" />} />
              <ProvenanceGraph graphData={provenanceData} onSelectCitation={setSelectedCitation} />
            </div>
          )}

          {activeTab === 'doc_analyzer' && (
            <div className="space-y-4">
              <PageHeader title={t('doc_ocr', lang)} subtitle="Upload, scan, and sanitize documents safely" icon={<Lock className="w-5 h-5" />} />
              <DocumentAnalyzer onApplyToPassport={handleIntakeSubmit} passportId={passport?.id} />
            </div>
          )}

          {activeTab === 'whatif' && (
            <div className="space-y-4">
              <PageHeader title={t('what_if', lang)} subtitle="Live reactive what-if compliance simulation" icon={<RefreshCw className="w-5 h-5" />} />
              <WhatIfSimulator
                passportId={passport?.id || ''}
                onSimulate={handleWhatIfSimulate}
                simulationResult={whatIfResult}
                isLoading={whatIfLoading}
              />
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="space-y-4">
              <PageHeader title={t('settings_title', lang)} subtitle="Profile, preferences, and workspace configuration" icon={<Settings className="w-5 h-5" />} />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <GlassCard padding="lg">
                  <h3 className="text-sm font-bold text-slate-900 mb-4">{t('profile', lang)}</h3>
                  {user && (
                    <div className="space-y-3">
                      {[
                        { lbl: t('name', lang), val: user.name, disabled: false },
                        { lbl: t('email', lang), val: user.email, disabled: true },
                        { lbl: t('role', lang), val: user.role, disabled: true },
                      ].map((f) => (
                        <div key={f.lbl}>
                          <label className="text-xs text-slate-500 mb-1.5 block">{f.lbl}</label>
                          <input
                            defaultValue={f.val}
                            disabled={f.disabled}
                            className="w-full px-4 py-2.5 bg-emerald-50/50 border border-emerald-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:border-emerald-500 disabled:text-slate-500"
                          />
                        </div>
                      ))}
                      <Button variant="primary" className="w-full" onClick={() => { setPrefsToast('Profile saved'); setTimeout(() => setPrefsToast(''), 2000); }}>{t('save_changes', lang)}</Button>
                      {prefsToast && <div className="text-xs text-emerald-600 text-center">{prefsToast}</div>}
                    </div>
                  )}
                </GlassCard>
                <GlassCard padding="lg">
                  <h3 className="text-sm font-bold text-slate-900 mb-4">{t('preferences', lang)}</h3>
                  <div className="space-y-3">
                    {[['emailNotifications', 'Email Notifications'], ['evidenceReminders', 'Evidence Reminders'], ['autoLanguage', 'Auto Language-Detection']].map(([key, label]) => {
                      const on = !!prefs[key];
                      return (
                        <div key={key} className="flex items-center justify-between px-4 py-3 rounded-xl bg-emerald-50/50 border border-emerald-200">
                          <span className="text-xs text-slate-700">{label}</span>
                          <button
                            role="switch"
                            aria-checked={on}
                            onClick={() => togglePref(key)}
                            className={`w-10 h-5 rounded-full relative transition cursor-pointer ${on ? 'bg-emerald-500' : 'bg-emerald-100'}`}
                          >
                            <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${on ? 'right-0.5' : 'left-0.5'}`} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
                    <Badge variant="success" dot>Secure</Badge>
                    <span>DPDP Act 2023 compliant · ap-south-1</span>
                  </div>
                </GlassCard>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Sticky mobile action button */}
      <div className="lg:hidden fixed bottom-5 right-5 z-40">
        <Button variant="primary" size="lg" className="rounded-full h-14 w-14 p-0 shadow-glow-blue">
          <Plus className="w-6 h-6" />
        </Button>
      </div>

      {/* Bottom navigation - mobile */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-xl border-t border-emerald-200 flex items-center justify-around px-2 py-2 shadow-[0_-4px_20px_rgba(2,44,34,0.06)]">
        {NAV_ITEMS.slice(0, 5).map(item => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;
          return (
            <button key={item.id} onClick={() => navigate(item.id)} className={`flex flex-col items-center gap-1 px-3 py-1 rounded-xl ${isActive ? 'text-emerald-600' : 'text-slate-500'}`}>
              <Icon className="w-5 h-5" />
              <span className="text-[9px] font-medium">{t(item.labelKey, lang).split(' ')[0]}</span>
            </button>
          );
        })}
      </nav>

      <SaktiAssistant
        lang={lang}
        passportId={passport?.id}
        passportTitle={passport?.case_title}
        readiness={assessment?.coverage_meter_score ?? null}
        onNavigate={(tab) => navigate(tab as TabId)}
        onQuickAction={(action) => {
          if (action === 'evaluate' && passport) handleIntakeSubmit(passport.case_title);
          else if (action === 'export') handleExportPDF();
          else if (action === 'whatif') navigate('whatif');
          else if (action === 'copilot') navigate('copilot');
        }}
      />

      <CitationPopover citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
      <GapPaddingBottom />
      <VoiceAssistant />
    </div>
  );
}

function GapPaddingBottom() {
  return <div className="lg:hidden h-16" />;
}
