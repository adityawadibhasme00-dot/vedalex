'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  Search, Globe, Route, ClipboardList, ShieldCheck, FlaskConical, Lock,
  Sprout, GitBranch, BookMarked, Languages, Settings, Compass, Landmark,
  EyeOff, Lightbulb, ArrowRight, Database, RefreshCw, CheckCircle2, TrendingUp,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Skeleton } from './ui/Skeleton';
import PatentAnalysis from './PatentAnalysis';
import JurisdictionMatrix from './JurisdictionMatrix';
import { RoadmapView } from './RoadmapView';
import EvidenceMatrix from './EvidenceMatrix';
import { ClaimSafetyIntelligence } from './ClaimSafetyIntelligence';
import { EvidenceQualityIntelligence } from './EvidenceQualityIntelligence';
import DocumentAnalyzer from './DocumentAnalyzer';
import { BioResourceIntelligence } from './BioResourceIntelligence';
import KnowledgeGraphView from './KnowledgeGraphView';
import ProvenanceGraph from './ProvenanceGraph';
import { TerminologyMapper } from './TerminologyMapper';
import { WhiteSpaceNavigator } from './WhiteSpaceNavigator';
import { getProvenanceGraph } from '../lib/api';
import { useLang, LangCode } from '../lib/LangContext';
import { SUPPORTED_LANGUAGES } from '../lib/i18n';
import { t } from '../lib/i18n';
import {
  InnovationPassport, ProvenanceGraphData, StatutoryCitation,
  RegulatoryFinding, AssessmentResponse,
} from '../types';

function PanelTabs({
  tabs, active, onChange,
}: {
  tabs: { id: string; label: string; icon: React.ReactNode }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap px-1 py-1.5 rounded-2xl bg-white/70 border border-emerald-200 mb-4">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-semibold transition ${
            active === tab.id
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-500 hover:text-slate-800 hover:bg-emerald-50'
          }`}
        >
          {tab.icon} {tab.label}
        </button>
      ))}
    </div>
  );
}

// ─── IP & Regulatory Analysis (Patent Analysis + Jurisdiction Matrix + Regulatory Roadmap + White Space) ───
export function IPRegulatoryPanel({
  passportId,
  findings = [],
  onSelectCitation,
  coverageMeterScore = 82,
  initialTab = 'ip',
}: {
  passportId?: string;
  findings?: RegulatoryFinding[];
  onSelectCitation: (citation: StatutoryCitation) => void;
  coverageMeterScore?: number;
  initialTab?: string;
}) {
  const [tab, setTab] = useState(initialTab);
  const tabs = [
    { id: 'ip', label: 'IP Analysis', icon: <Search className="w-3.5 h-3.5" /> },
    { id: 'matrix', label: 'India / International Matrix', icon: <Globe className="w-3.5 h-3.5" /> },
    { id: 'roadmap', label: 'Regulatory Roadmap', icon: <Route className="w-3.5 h-3.5" /> },
    { id: 'whitespace', label: 'White Space', icon: <Compass className="w-3.5 h-3.5" /> },
  ];
  return (
    <div className="space-y-4">
      <PanelTabs tabs={tabs} active={tab} onChange={setTab} />
      {tab === 'ip' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white/70 px-4 py-3 flex items-center gap-3">
            <Compass className="w-4 h-4 text-blue-600 flex-shrink-0" />
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Cross-referenced against India (Patent Act, 1970 & Section 3(p)) and international routes (PCT, WIPO). Switch the AI Copilot to International scope for cross-border answers.
            </p>
          </div>
          <PatentAnalysis passportId={passportId || ''} />
        </div>
      )}
      {tab === 'matrix' && (
        <JurisdictionMatrix
          findings={findings}
          onSelectCitation={onSelectCitation}
          coverageMeterScore={coverageMeterScore}
        />
      )}
      {tab === 'roadmap' && <RoadmapView passportId={passportId} />}
      {tab === 'whitespace' && <WhiteSpaceNavigator passportId={passportId} />}
    </div>
  );
}

// ─── Evidence & Compliance (Evidence Matrix + Claim & Safety + Evidence & Quality + Document OCR) ───
export function EvidenceCompliancePanel({
  passport,
  passportId,
  onStatusUpdate,
  onApplyToPassport,
}: {
  passport: InnovationPassport | null;
  passportId?: string;
  onStatusUpdate: (itemId: string, status: string) => void;
  onApplyToPassport: (rawText: string, title?: string) => void;
}) {
  const [tab, setTab] = useState('matrix');
  const tabs = [
    { id: 'matrix', label: 'Evidence Matrix', icon: <ClipboardList className="w-3.5 h-3.5" /> },
    { id: 'claim', label: 'Claim & Safety', icon: <ShieldCheck className="w-3.5 h-3.5" /> },
    { id: 'quality', label: 'Evidence & Quality', icon: <FlaskConical className="w-3.5 h-3.5" /> },
    { id: 'ocr', label: 'Document OCR & Safety', icon: <Lock className="w-3.5 h-3.5" /> },
  ];
  return (
    <div className="space-y-4">
      <PanelTabs tabs={tabs} active={tab} onChange={setTab} />
      {tab === 'matrix' && (
        <EvidenceMatrix
          initialRows={undefined}
          passportId={passportId}
          passport={passport}
          onStatusUpdate={onStatusUpdate}
        />
      )}
      {tab === 'claim' && (
        <ClaimSafetyIntelligence passportId={passportId} initialClaims={passport?.proposed_claims} />
      )}
      {tab === 'quality' && <EvidenceQualityIntelligence passportId={passportId} />}
      {tab === 'ocr' && <DocumentAnalyzer onApplyToPassport={onApplyToPassport} passportId={passportId} />}
    </div>
  );
}

// ─── Bio-Resource Intelligence Graph (Bio-Resource Graph + Provenance Graph) ───
export function BioResourcePanel({ passportId }: { passportId?: string }) {
  const [jurisdiction, setJurisdiction] = useState<'India' | 'International'>('India');
  const [provenanceData, setProvenanceData] = useState<ProvenanceGraphData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchProvenance = useCallback(async () => {
    if (!passportId) return;
    setLoading(true);
    try {
      const data = await getProvenanceGraph(passportId, jurisdiction);
      setProvenanceData(data);
    } catch {
      setProvenanceData(null);
    } finally {
      setLoading(false);
    }
  }, [passportId, jurisdiction]);

  useEffect(() => {
    fetchProvenance();
  }, [fetchProvenance]);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-200 bg-white/70 px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <Database className="w-4 h-4 text-emerald-700 flex-shrink-0" />
          <div>
            <div className="text-xs font-bold text-slate-800">Provenance & Decision Trace</div>
            <div className="text-[10px] text-slate-500">Trace regulatory reasoning with citations</div>
          </div>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 p-1">
          {(['India', 'International'] as const).map((j) => (
            <button
              key={j}
              type="button"
              onClick={() => setJurisdiction(j)}
              className={`px-3 py-1 rounded-full text-[11px] font-semibold transition ${
                jurisdiction === j ? 'bg-emerald-600 text-white shadow' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              {j}
            </button>
          ))}
        </div>
      </div>

      <BioResourceIntelligence passportId={passportId} />

      <KnowledgeGraphView passportId={passportId} />

      {loading ? (
        <GlassCard padding="lg"><Skeleton lines={4} /></GlassCard>
      ) : (
        <ProvenanceGraph graphData={provenanceData} onSelectCitation={() => {}} />
      )}
    </div>
  );
}

// ─── Language & Settings (Terminology Mapper + Language Selector + Preferences) ───
export function LanguageSettingsPanel({
  user,
  passportIngredients = [],
}: {
  user?: { name?: string; email?: string; role?: string } | null;
  passportIngredients?: string[];
}) {
  const { lang, setLang } = useLang();
  const initialPrefs = { emailNotifications: false, evidenceReminders: true, autoLanguage: true };
  const [prefs, setPrefs] = useState<Record<string, boolean>>(initialPrefs);
  const [toast, setToast] = useState('');
  const [termTab, setTermTab] = useState(false);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('ipsakti_preferences') || 'null');
      if (saved) setPrefs((p) => ({ ...p, ...saved }));
    } catch {}
  }, []);

  useEffect(() => {
    localStorage.setItem('ipsakti_preferences', JSON.stringify(prefs));
  }, [prefs]);

  const togglePref = (key: string) => setPrefs((p) => ({ ...p, [key]: !p[key] }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        <GlassCard padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Languages className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">{t('language_settings', lang)}</h3>
          </div>
          <p className="text-[11px] text-slate-500 mb-3">Choose the working language for the entire platform — answers render with the same source evidence in every language.</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {SUPPORTED_LANGUAGES.map((opt) => (
              <button
                key={opt.code}
                type="button"
                onClick={() => setLang(opt.code as LangCode)}
                className={`px-3 py-2.5 rounded-xl border text-left transition ${
                  lang === opt.code
                    ? 'bg-emerald-600 border-emerald-600 text-white shadow-sm'
                    : 'bg-emerald-50/50 border-emerald-200 text-slate-600 hover:border-emerald-400'
                }`}
              >
                <div className="text-[11px] font-bold">{opt.nativeName}</div>
                <div className={`text-[9px] ${lang === opt.code ? 'text-white/70' : 'text-slate-400'}`}>{opt.name}</div>
              </button>
            ))}
          </div>
        </GlassCard>

        <GlassCard padding="lg">
          <h3 className="text-sm font-bold text-slate-900 mb-4">{t('profile', lang)}</h3>
          {user && (
            <div className="space-y-3">
              {[
                { lbl: t('name', lang), val: user.name || '', disabled: false },
                { lbl: t('email', lang), val: user.email || '', disabled: true },
                { lbl: t('role', lang), val: user.role || '', disabled: true },
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
              <Button variant="primary" className="w-full" onClick={() => { setToast('Profile saved'); setTimeout(() => setToast(''), 2000); }}>{t('save_changes', lang)}</Button>
              {toast && <div className="text-xs text-emerald-600 text-center">{toast}</div>}
            </div>
          )}
        </GlassCard>
      </div>

      <GlassCard padding="lg">
        <div className="flex items-center gap-2 mb-2">
          <BookMarked className="w-4 h-4 text-amber-600" />
          <h3 className="text-sm font-bold text-slate-900">Ayurvedic Terminology Mapper</h3>
          <button
            type="button"
            onClick={() => setTermTab((v) => !v)}
            className="ml-auto text-[10px] font-bold text-blue-600 hover:text-blue-800 transition inline-flex items-center gap-1"
          >
            {termTab ? <RefreshCw className="w-3 h-3" /> : <Search className="w-3 h-3" />}
            {termTab ? 'Show preferences' : 'Resolve botanical names'}
          </button>
        </div>
        <p className="text-[11px] text-slate-500 mb-3">Resolve all names of a botanical to one canonical RAG entity.</p>
        {termTab ? (
          <TerminologyMapper passportIngredients={passportIngredients} />
        ) : (
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
        )}
      </GlassCard>
    </div>
  );
}

// ─── IP Route Advisor (Innovation Passport → recommended IP route) ───
const ROUTE_META: Record<string, { icon: React.ReactNode; title: string; desc: string; authority: string; note: string }> = {
  trademark: {
    icon: <Landmark className="w-4 h-4" />,
    title: 'Trademark',
    desc: 'Protect your brand name, word-mark or product label identity.',
    authority: 'Controller General of Patents, Designs & Trademarks (CGPDTM)',
    note: 'Multi-class filing; Madrid Protocol allows international extension from India.',
  },
  gi: {
    icon: <Globe className="w-4 h-4" />,
    title: 'Geographical Indication (GI)',
    desc: 'Protect formulation identity tied to a geographic origin or community practice.',
    authority: 'Geographical Indications Registry, Chennai',
    note: 'Requires the product’s qualities to be attributable to its place of origin.',
  },
  trade_secret: {
    icon: <EyeOff className="w-4 h-4" />,
    title: 'Trade Secret',
    desc: 'Keep the process, ratios or sourcing data confidential — no public disclosure.',
    authority: 'No registration — protected by confidentiality agreements',
    note: 'Section 3(p) risk avoided, but reverse-engineering is a real threat.',
  },
  patent: {
    icon: <Search className="w-4 h-4" />,
    title: 'Patent',
    desc: 'Protect the novel process, composition or method of manufacture.',
    authority: 'IP India (Patent Office) / PCT via WIPO',
    note: 'Filing = full disclosure. Run a prior-art search + Section 3(p) check first.',
  },
};

export function IPRouteAdvisor({ passport }: { passport: InnovationPassport | null }) {
  const [intent, setIntent] = useState<Record<string, boolean>>({ brand: true, region: false, secret: false, process: true });

  if (!passport) {
    return (
      <GlassCard padding="lg" className="border-blue-500/20">
        <div className="flex items-center gap-2 mb-2">
          <Lightbulb className="w-4 h-4 text-amber-500" />
          <h3 className="text-sm font-bold text-slate-900">IP Route Advisor</h3>
        </div>
        <p className="text-[11px] text-slate-500">Create an Innovation Passport to see which IP route best protects your asset.</p>
      </GlassCard>
    );
  }

  const brandName = passport.case_title || '';
  const hasProcessInnovation =
    /novel|innovative|new|unique|synergistic|proprietary|process patent/i.test(
      `${passport.claimed_innovation} ${passport.process_description} ${passport.existing_ip_status}`
    );

  const routes: string[] = [];
  if (intent.brand && brandName) routes.push('trademark');
  if (intent.region && passport.target_markets?.some((m) => /india/i.test(m))) routes.push('gi');
  if (intent.secret) routes.push('trade_secret');
  if (intent.process && hasProcessInnovation) routes.push('patent');

  const topPick = intent.process && hasProcessInnovation ? 'patent' : routes[0];
  const toggle = (key: string) => setIntent((p) => ({ ...p, [key]: !p[key] }));

  const intentOptions = [
    { key: 'brand', label: 'Brand / product name', hint: '→ Trademark' },
    { key: 'region', label: 'Region-linked origin / community practice', hint: '→ GI' },
    { key: 'secret', label: 'Keep formulation or process confidential', hint: '→ Trade Secret' },
    { key: 'process', label: 'Novel process / synergy in formulation', hint: '→ Patent' },
  ];

  return (
    <div className="space-y-4">
      <GlassCard padding="lg" className="border-blue-500/20">
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb className="w-4 h-4 text-amber-500" />
          <h3 className="text-sm font-bold text-slate-900">IP Route Advisor</h3>
          <Badge variant="info" dot>Recommendation Engine</Badge>
        </div>
        <p className="text-[11px] text-slate-500 mb-4">Declare what you want to protect, and the advisor routes it to the right IP protection for {brandName}:</p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4">
          {intentOptions.map((opt) => (
            <button
              key={opt.key}
              type="button"
              onClick={() => toggle(opt.key)}
              className={`px-4 py-3 rounded-xl border text-left transition ${
                intent[opt.key]
                  ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                  : 'bg-white/70 border-slate-200 text-slate-600 hover:border-blue-400'
              }`}
            >
              <div className="text-[11px] font-bold">{opt.label}</div>
              <div className={`text-[10px] mt-0.5 ${intent[opt.key] ? 'text-white/80' : 'text-slate-400'}`}>{opt.hint}</div>
            </button>
          ))}
        </div>

        {routes.length > 0 ? (
          <div className="space-y-2.5">
            {routes.map((r) => {
              const meta = ROUTE_META[r];
              const isTop = r === topPick;
              return (
                <div key={r} className={`flex items-start gap-3 px-4 py-3 rounded-xl border ${isTop ? 'border-emerald-400 bg-emerald-50/80' : 'border-slate-200 bg-white/70'}`}>
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${isTop ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                    {meta.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900">{meta.title}</span>
                      {isTop && <Badge variant="success" dot>Recommended</Badge>}
                    </div>
                    <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed">{meta.desc}</p>
                    <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-slate-400">
                      <ArrowRight className="w-3 h-3" /> {meta.authority}
                    </div>
                  </div>
                </div>
              );
            })}
            <div className="rounded-xl bg-[#0D1425] px-4 py-3 flex items-start gap-2.5">
              <TrendingUp className="w-4 h-4 text-emerald-300 mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-slate-300 leading-relaxed">
                {topPick === 'patent' && 'A novel process with a synergistic composition is your strongest protectable asset — but filing means full disclosure, so pair it with a Section 3(p) + prior-art run before filing.'}
                {topPick === 'trademark' && 'Brand identity can be secured quickly and inexpensively — file the trademark first to lock the name, then decide on deeper process protection later.'}
                {topPick === 'gi' && `Origin-linked identity (${passport.manufacturing_location || 'your region'}) can be claimed as a GI — community coordination is required.`}
                {topPick === 'trade_secret' && 'Keeping the process confidential avoids Section 3(p) disclosure risk entirely, but you must document trade-secret controls (NDAs, access logs).'}
              </p>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white/60 px-4 py-6 text-center text-[11px] text-slate-500">
            Select at least one protection intent above to see your route options.
          </div>
        )}
      </GlassCard>
    </div>
  );
}