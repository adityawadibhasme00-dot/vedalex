'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/AuthContext';
import { useLang } from '../../lib/LangContext';
import InnovationPassportView from '../../components/InnovationPassportView';
import InnovationPassportForm from '../../components/InnovationPassportForm';
import EvidenceMatrix from '../../components/EvidenceMatrix';
import AICopilot from '../../components/AICopilot';
import ClarificationAlert from '../../components/ClarificationAlert';
import CitationPopover from '../../components/CitationPopover';
import DossierView from '../../components/DossierView';
import WhatIfSimulator from '../../components/WhatIfSimulator';
import SaktiAssistant from '../../components/SaktiAssistant';
import { ProductClassifier } from '../../components/ProductClassifier';
import { ExportReadiness } from '../../components/ExportReadiness';
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
  simulateWhatIf, PassportIntakeExtras,
} from '../../lib/api';
import { exportInnovationPassportPDF } from '../../lib/exportManager';
import { saveOfflineDraft, getOfflineDrafts } from '../../lib/offlineStorage';
import { t } from '../../lib/i18n';
import { innolabApi, InnolabAgent } from '../../lib/innolabApi';

import {
  LayoutDashboard, FileText, Search, ClipboardList, Bot, FileDown,
  Settings, Sparkles, Plus, RefreshCw,
  Sprout, Layers, FileBadge, FlaskConical,
} from 'lucide-react';

import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { HerbSprig, TurmericRoot } from '../../components/BotanicalDecor';
import {
  IPRegulatoryPanel, EvidenceCompliancePanel, BioResourcePanel,
  LanguageSettingsPanel, IPRouteAdvisor,
} from '../../components/DashboardPanels';

const NAV_ITEMS = [
  { id: 'overview', labelKey: 'dashboard',               icon: LayoutDashboard, color: 'text-blue-600' },
  { id: 'innolab',  labelKey: 'innovation_lab',          icon: FlaskConical,    color: 'text-teal-600' },
  { id: 'passport', labelKey: 'innovation_passport',     icon: FileText,        color: 'text-emerald-600' },
  { id: 'biores',   labelKey: 'bio_resource_intelligence', icon: Sprout,        color: 'text-emerald-600' },
  { id: 'ipreg',    labelKey: 'ip_regulatory_analysis',  icon: Search,          color: 'text-blue-600' },
  { id: 'evidence', labelKey: 'evidence_compliance',     icon: ClipboardList,   color: 'text-amber-600' },
  { id: 'classify', labelKey: 'product_classifier',      icon: Layers,          color: 'text-violet-600' },
  { id: 'market',   labelKey: 'market_readiness',        icon: FileBadge,       color: 'text-blue-600' },
  { id: 'copilot',  labelKey: 'ai_copilot',              icon: Bot,             color: 'text-violet-600' },
  { id: 'whatif',   labelKey: 'what_if',                 icon: RefreshCw,       color: 'text-amber-600' },
  { id: 'dossier',  labelKey: 'dossier_export',          icon: FileDown,        color: 'text-blue-600' },
  { id: 'settings', labelKey: 'language_settings',       icon: Settings,        color: 'text-slate-500' },
] as const;

type TabId = typeof NAV_ITEMS[number]['id'];

import { InnovationLabWorkspace } from '../../components/InnovationLabWorkspace';

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const { lang } = useLang();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [isOnline, setIsOnline] = useState(true);
  const [offlineDraftCount, setOfflineDraftCount] = useState(0);
  const [ipregInitialTab, setIpregInitialTab] = useState('ip');
  const [labAgents, setLabAgents] = useState<InnolabAgent[]>([]);
  const [labAgentsLoaded, setLabAgentsLoaded] = useState(false);

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
    const h = window.location.hash.replace('#', '') as TabId;
    if (NAV_ITEMS.some((n) => n.id === h)) setActiveTab(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    innolabApi.agents()
      .then((r) => { setLabAgents(r.agents); setLabAgentsLoaded(true); })
      .catch(() => setLabAgentsLoaded(true));
  }, []);

  useEffect(() => {
    handleIntakeSubmit(
      'अश्वगंधा + ब्राह्मी फॉर्म्युलेशन, दावा: शांत झोपेसाठी उपयुक्त, लक्ष्य बाजार: भारत, अमेरिका, कॅनडा',
      'Ashwagandha & Brahmi Restful Sleep Formulation'
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleIntakeSubmit = useCallback(async (rawText: string, title?: string, extras?: Partial<PassportIntakeExtras>) => {
    setIsLoading(true);
    try {
      const newPassport = await createPassportFromIntake(rawText, lang, title, extras);
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

  const handleSearch = (query: string) => {
    setActiveTab('copilot');
    setIpregInitialTab('ip');
    if (typeof window !== 'undefined') window.history.replaceState(null, '', '#copilot');
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('ipsakti:copilot-question', { detail: query }));
    }, 400);
  };

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
    const tabEntries: [TabId, RegExp][] = [
      ['overview', /dashboard|home|overview|main page|landing/i],
      ['innolab', /innovation lab|innovation ai lab|r&d|research lab|ai lab/i],
      ['passport', /passport|innovation passport|create passport/i],
      ['ipreg', /patent|patentability|prior art|jurisdiction|country|roadmap|regulatory roadmap|timeline|filing journey|IP analysis/i],
      ['biores', /bio.?resource|plant intelligence|sourcing|abs graph|medicinal plant|provenance|graph|citation/i],
      ['evidence', /evidence|matrix|gaps? in evidence|claim|safety|misleading|label|pharmacopoeia|quality|ocr|document|scan|sanitize/i],
      ['classify', /classify|classifier|pathway|aahara|which category|product class|wizard/i],
      ['market', /export readiness|market entry|market readiness|which market|market first|export plan/i],
      ['copilot', /copilot|ai|assistant|search anything/i],
      ['whatif', /what.?if|simulat/i],
      ['dossier', /dossier|export|download|report/i],
      ['settings', /settings?|language|terminology|mapper|botanical (names?|synonyms)|profile|account|preferenc/i],
    ];
    const tabMatch = tabEntries.find(([, re]) => re.test(low));

    if (tabMatch) tab = tabMatch[0];

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
    if (typeof window !== 'undefined') window.history.replaceState(null, '', `#${tab}`);
    if (tab !== 'ipreg') setIpregInitialTab('ip');
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
      disclosure: 'evidence',
      fto: 'ipreg',
      label: 'passport',
      abs: 'biores',
      'evidence-matrix': 'evidence',
      'claim-safety': 'evidence',
      'evidence-quality': 'evidence',
      'bio-resource': 'biores',
      'provenance': 'biores',
      'product-classifier': 'classify',
      'export-readiness': 'market',
      'terminology-mapper': 'settings',
      roadmap: 'ipreg',
      whitespace: 'ipreg',
      dossier: 'dossier',
      expert: 'overview',
      'what-if': 'whatif',
    };
    if (id === 'whitespace') setIpregInitialTab('whitespace');
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
    if (activeTab === 'ipreg' || activeTab === 'biores') ensurePassportComputed();
  }, [activeTab, ensurePassportComputed]);

  return (
    <>
      <DashboardLayout
        activeTab={activeTab}
        onNavigate={(tab) => navigate(tab as TabId)}
        onSearch={handleSearch}
        userName={user?.name}
        userRole={user?.role}
        labAgents={labAgents}
        labAgentsLoaded={labAgentsLoaded}
        isOnline={isOnline}
        offlineDraftCount={offlineDraftCount}
      >

        {isLoading && (
          <div className="h-0.5 bg-gov-wash relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-amber-500 via-gov-blue to-amber-500 animate-shimmer" />
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
                    title={t('dash_passport_header_title', lang)}
                    subtitle={t('dash_passport_header_sub', lang)}
                    icon={<Sparkles className="w-5 h-5" />}
                  />
                  <InnovationPassportForm
                    onSubmit={(data: any) => {
                      handleIntakeSubmit(data.raw_text || data.case_title, data.case_title || 'New Innovation', {
                        product_type: data.product_type,
                        category: data.category,
                        target_markets: data.target_markets,
                        extraction_method: data.extraction_method,
                        solvent: data.solvent,
                        temperature: data.temperature,
                        time: data.time,
                        processing_steps: data.processing_steps,
                        proposed_claims: data.proposed_claims,
                      });
                    }}
                    isLoading={isLoading}
                  />
                </GlassCard>
              </div>
            </>
          )}

          {activeTab === 'innolab' && (
            <div className="space-y-4">
              <PageHeader title={t('innovation_lab', lang)} subtitle={t('dash_innolab_sub', lang)} icon={<FlaskConical className="w-5 h-5" />} />
              <InnovationLabWorkspace />
            </div>
          )}

          {activeTab === 'passport' && (
            <div className="space-y-4">
              <PageHeader title={t('innovation_passport', lang)} subtitle={t('dash_passport_sub', lang)} icon={<FileText className="w-5 h-5" />} />
              {passport ? (
                <>
                  <IPRouteAdvisor passport={passport} />
                  <InnovationPassportView
                    passport={passport}
                    onUpdatePassport={setPassport}
                    onIntakeSubmit={handleIntakeSubmit}
                    onSanitizeTest={(txt) => sanitizeDocument(txt, 'label.pdf')}
                    isLoading={isLoading}
                    currentLang={lang}
                  />
                </>
              ) : (
                <GlassCard padding="lg"><Skeleton lines={6} /></GlassCard>
              )}
            </div>
          )}

          {activeTab === 'ipreg' && (
            <div className="space-y-4">
              <PageHeader title={t('ip_regulatory_analysis', lang)} subtitle={t('dash_ipreg_sub', lang)} icon={<Search className="w-5 h-5" />} />
              <IPRegulatoryPanel
                passportId={passport?.id}
                findings={assessment?.findings || []}
                onSelectCitation={setSelectedCitation}
                coverageMeterScore={assessment?.coverage_meter_score || 82}
                initialTab={ipregInitialTab}
              />
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-4">
              <PageHeader title={t('evidence_compliance', lang)} subtitle={t('dash_evidence_sub', lang)} icon={<ClipboardList className="w-5 h-5" />} />
              <EvidenceCompliancePanel
                passport={passport}
                passportId={passport?.id}
                onStatusUpdate={(itemId, status) => {
                  if (passport) getEvidenceGaps(passport.id).then(setEvidenceSummary).catch(() => {});
                }}
                onApplyToPassport={(raw, title) => handleIntakeSubmit(raw, title)}
              />
            </div>
          )}

          {activeTab === 'copilot' && (
            <div className="space-y-4">
              <PageHeader title={t('dash_copilot_title', lang)} subtitle={t('dash_copilot_sub', lang)} icon={<Bot className="w-5 h-5" />} />
              <AICopilot passportId={passport?.id} lang={lang} />
            </div>
          )}

          {activeTab === 'biores' && (
            <div className="space-y-4">
              <PageHeader title={t('bio_resource_intelligence', lang)} subtitle={t('dash_biores_sub', lang)} icon={<Sprout className="w-5 h-5" />} />
              <BioResourcePanel passportId={passport?.id} />
            </div>
          )}

          {activeTab === 'classify' && (
            <div className="space-y-4">
              <PageHeader title={t('product_classifier', lang)} subtitle={t('dash_classify_sub', lang)} icon={<Layers className="w-5 h-5" />} />
              <ProductClassifier passportId={passport?.id} passport={passport} />
            </div>
          )}

          {activeTab === 'market' && (
            <div className="space-y-4">
              <PageHeader title={t('market_readiness', lang)} subtitle={t('dash_market_sub', lang)} icon={<FileBadge className="w-5 h-5" />} />
              <ExportReadiness passportId={passport?.id} />
            </div>
          )}

          {activeTab === 'dossier' && (
            <div className="space-y-4">
              <PageHeader title={t('dossier_export', lang)} subtitle={t('dash_dossier_sub', lang)} icon={<FileDown className="w-5 h-5" />} />
              <DossierView passportId={passport?.id || ''} />
            </div>
          )}

          {activeTab === 'whatif' && (
            <div className="space-y-4">
              <PageHeader title={t('what_if', lang)} subtitle={t('dash_whatif_sub', lang)} icon={<RefreshCw className="w-5 h-5" />} />
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
              <PageHeader title={t('language_settings', lang)} subtitle={t('dash_settings_sub', lang)} icon={<Settings className="w-5 h-5" />} />
              <LanguageSettingsPanel
                user={user}
                passportIngredients={passport?.ingredients?.map((i) => i.raw_name) || []}
              />
            </div>
          )}
        </main>
      </DashboardLayout>

      {/* Sticky mobile action button */}
      <div className="lg:hidden fixed bottom-5 right-5 z-40">
        <Button variant="primary" size="lg" className="rounded-full h-14 w-14 p-0 shadow-glow-blue">
          <Plus className="w-6 h-6" />
        </Button>
      </div>

      {/* Bottom navigation - mobile */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gov-rule flex items-center justify-around px-2 py-2 shadow-[0_-4px_20px_rgba(26,42,78,0.08)]">
        {NAV_ITEMS.slice(0, 5).map(item => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;
          return (
            <button key={item.id} onClick={() => navigate(item.id)} className={`flex flex-col items-center gap-1 px-3 py-1 rounded-md ${isActive ? 'text-gov-blue' : 'text-slate-500'}`}>
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
    </>
  );
}

function GapPaddingBottom() {
  return <div className="lg:hidden h-16" />;
}
