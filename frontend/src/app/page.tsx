'use client';
import React from 'react';
import { useRouter } from 'next/navigation';
import {
  Leaf, ShieldCheck, Globe2, BookOpenCheck,
  ArrowRight, Scale, BadgeCheck, Lock, Languages,
  Landmark, Database, Newspaper, QrCode, ClipboardList,
  Award, ChevronRight, Lightbulb, Search, FileText, FileDown,
  CheckCircle2,
} from 'lucide-react';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

const NAV_LINKS = [
  { id: 'hero', labelKey: 'home' },
  { id: 'about', labelKey: 'landing_nav_about' },
  { id: 'features', labelKey: 'landing_nav_features' },
  { id: 'process', labelKey: 'landing_nav_how' },
  { id: 'sources', labelKey: 'landing_nav_sources' },
  { id: 'contact', labelKey: 'landing_nav_contact' },
];

const FEATURES = [
  {
    id: 'disclosure',
    tagKey: 'feature_disclosure_tag',
    titleKey: 'feature_disclosure_title',
    descKey: 'feature_disclosure_desc',
    pointKeys: ['feature_disclosure_p1', 'feature_disclosure_p2', 'feature_disclosure_p3'],
    icon: ClipboardList,
  },
  {
    id: 'section3p',
    tagKey: 'feature_section3p_tag',
    titleKey: 'feature_section3p_title',
    descKey: 'feature_section3p_desc',
    pointKeys: ['feature_section3p_p1', 'feature_section3p_p2', 'feature_section3p_p3'],
    icon: Scale,
  },
  {
    id: 'passport',
    tagKey: 'feature_passport_tag',
    titleKey: 'innovation_passport',
    descKey: 'feature_passport_desc',
    pointKeys: ['feature_passport_p1', 'feature_passport_p2', 'feature_passport_p3'],
    icon: BadgeCheck,
  },
  {
    id: 'global',
    tagKey: 'feature_global_tag',
    titleKey: 'feature_global_title',
    descKey: 'feature_global_desc',
    pointKeys: ['feature_global_p1', 'feature_global_p2', 'feature_global_p3'],
    icon: Globe2,
  },
  {
    id: 'firewall',
    tagKey: 'feature_firewall_tag',
    titleKey: 'feature_firewall_title',
    descKey: 'feature_firewall_desc',
    pointKeys: ['feature_firewall_p1', 'feature_firewall_p2', 'feature_firewall_p3'],
    icon: ShieldCheck,
  },
  {
    id: 'rag',
    tagKey: 'feature_rag_tag',
    titleKey: 'feature_rag_title',
    descKey: 'feature_rag_desc',
    pointKeys: ['feature_rag_p1', 'feature_rag_p2', 'feature_rag_p3'],
    icon: BookOpenCheck,
  },
];

const PROCESS = [
  {
    key: 'idea',
    labelKey: 'process_idea_label',
    icon: Lightbulb,
    descKey: 'lp_process_idea_desc',
  },
  {
    key: 'verification',
    labelKey: 'process_verification_label',
    icon: Search,
    descKey: 'lp_process_verification_desc',
  },
  {
    key: 'prior-art',
    labelKey: 'process_prior_art_label',
    icon: FileText,
    descKey: 'lp_process_prior_art_desc',
  },
  {
    key: 'readiness',
    labelKey: 'patent_readiness',
    icon: BadgeCheck,
    descKey: 'lp_process_readiness_desc',
  },
  {
    key: 'passport',
    labelKey: 'innovation_passport',
    icon: QrCode,
    descKey: 'lp_process_passport_desc',
  },
  {
    key: 'export',
    labelKey: 'process_export_label',
    icon: FileDown,
    descKey: 'lp_process_export_desc',
  },
];

const SOURCES = [
  { name: 'Ministry of AYUSH', href: 'https://ayush.gov.in/', icon: Landmark },
  { name: 'TKDL', href: 'https://tkdl.res.in/', icon: Database },
  { name: 'IP India', href: 'https://ipindia.gov.in/', icon: Award },
  { name: 'WIPO', href: 'https://www.wipo.int/', icon: Globe2 },
  { name: 'PubMed', href: 'https://pubmed.ncbi.nlm.nih.gov/', icon: BookOpenCheck },
  { name: 'WHO', href: 'https://www.who.int/', icon: ShieldCheck },
];

const STATS = [
  { value: '94%', labelKey: 'lp_stat_tkdl_grounded' },
  { value: '3', labelKey: 'lp_stat_jurisdictions' },
  { value: '0%', labelKey: 'lp_stat_rag_hallucination' },
  { value: '9', labelKey: 'lp_stat_languages' },
];

export default function HomePage() {
  const { lang, setLang } = useLang();
  const router = useRouter();

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const setFont = (delta: number) => {
    const root = document.documentElement;
    const cur = parseFloat(root.style.fontSize || '16');
    const next = delta === 0 ? 16 : Math.max(14, Math.min(20, cur + delta));
    root.style.fontSize = `${next}px`;
  };

  return (
    <div className="min-h-screen bg-white text-gov-ink">
      {/* Skip link (GIGW) */}
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:bg-gov-navy focus:text-white focus:px-4 focus:py-2 focus:rounded-md focus:text-sm">
        {t('landing_skip_to_main', lang)}
      </a>

      {/* ── 1. Utility strip (navy) ─────────────────────────────── */}
      <div className="bg-gov-navy text-blue-100">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 py-1.5 flex flex-wrap items-center justify-end gap-2 text-[11px] font-medium">
          <div className="ml-auto flex items-center gap-3 text-[11px]">
            <span className="hidden sm:inline text-blue-300">{t('accessibility', lang)}</span>
            <button onClick={() => setFont(-1)} className="px-1.5 py-0.5 border border-blue-400/40 rounded hover:bg-gov-blue" aria-label={t('landing_font_decrease', lang)}>A−</button>
            <button onClick={() => setFont(0)} className="px-1.5 py-0.5 border border-blue-400/40 rounded hover:bg-gov-blue" aria-label={t('landing_font_reset', lang)}>A</button>
            <button onClick={() => setFont(1)} className="px-1.5 py-0.5 border border-blue-400/40 rounded hover:bg-gov-blue" aria-label={t('landing_font_increase', lang)}>A+</button>
            <span className="text-blue-400">|</span>
            <label className="flex items-center gap-1.5">
              <Languages className="w-3.5 h-3.5 text-amber-300" />
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value as 'en' | 'hi')}
                className="bg-gov-navy border border-blue-400/40 rounded px-1.5 py-0.5 text-blue-100 text-[11px] cursor-pointer focus:outline-none"
              >
                <option value="en">English</option>
                <option value="hi">हिन्दी</option>
              </select>
            </label>
          </div>
        </div>
      </div>

      {/* ── Tricolor strip ─────────────────────────────────────── */}
      <div className="gov-strip" aria-hidden="true" />

      {/* ── 2. Official header ──────────────────────────────────── */}
      <div className="bg-white border-b border-gov-rule">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 py-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-white border-4 border-gov-blue flex items-center justify-center">
              <Leaf className="w-7 h-7 text-gov-blue" />
            </div>
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold text-gov-navy font-display leading-tight">
                {t('app_title', lang)}
              </h1>
              <p className="text-xs lg:text-sm font-semibold text-gov-blue uppercase tracking-wide">{t('landing_header_title', lang)}</p>
              <p className="text-[11px] text-gov-mute mt-0.5">{t('landing_header_subtitle', lang)}</p>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gov-wash border border-gov-rule text-[11px] font-bold text-gov-green">
              <span className="w-2 h-2 rounded-full bg-gov-green animate-pulse" /> {t('landing_tkdl_sync_active', lang)}
            </span>
          </div>
        </div>
      </div>

      {/* ── Sticky navigation (blue bar) ────────────────────────── */}
      <nav className="sticky top-0 z-40 bg-gov-blue shadow-md">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 flex items-center justify-between">
          <div className="flex items-center overflow-x-auto">
            {NAV_LINKS.map((l) => (
              <button key={l.id} onClick={() => scrollTo(l.id)} className="px-3.5 lg:px-5 py-3.5 text-[12px] lg:text-[13px] font-semibold text-white hover:bg-gov-navy hover:text-amber-300 whitespace-nowrap transition-colors border-r border-gov-blueDk last:border-r-0">
                {t(l.labelKey, lang)}
              </button>
            ))}
          </div>
          <button onClick={() => router.push('/login')} className="inline-flex items-center gap-2 px-3 lg:px-4 py-2 my-2 ml-3 lg:ml-4 bg-amber-500 hover:bg-amber-600 text-white text-[12px] font-bold rounded-md transition-colors shrink-0">
            <Lock className="w-3.5 h-3.5" /> {t('sign_in', lang)}
          </button>
        </div>
      </nav>

      <main id="main-content" className="mx-auto max-w-7xl px-4 lg:px-6 py-12 space-y-20">
        {/* ── 3. Hero section ───────────────────────────────────── */}
        <section id="hero" className="scroll-mt-24 grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-10 items-center">
          <div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gov-wash text-gov-blue border border-gov-rule text-[11px] font-bold mb-5 animate-fade-in-left">
              <Award className="w-3.5 h-3.5 text-amber-600" /> {t('landing_hero_badge', lang)}
            </span>
            <h2 className="text-4xl lg:text-5xl font-bold text-gov-navy font-display leading-[1.15] tracking-tight animate-fade-in-up">
              {t('landing_hero_title', lang)}{' '}
              <span className="text-gov-blue">{t('landing_hero_title_accent', lang)}</span>
            </h2>
            <p className="mt-5 text-[15px] lg:text-base text-gov-ink leading-relaxed max-w-xl animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
              {t('landing_hero_desc', lang)}
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3 animate-fade-in-up" style={{ animationDelay: '0.45s' }}>
              <button
                onClick={() => scrollTo('features')}
                className="inline-flex items-center gap-2 px-7 py-3.5 rounded-md bg-white border-2 border-gov-rule hover:border-gov-blue text-gov-navy text-sm font-bold transition-colors"
              >
                {t('landing_hero_explore', lang)}
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
            <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-4">
              {STATS.map((s) => (
                <div
                  key={s.labelKey}
                  className="border-l-4 border-gov-blue bg-gov-wash p-4"
                >
                  <div className="text-2xl font-bold text-gov-navy font-display">{s.value}</div>
                  <div className="text-[10px] text-gov-mute mt-1 leading-snug">{t(s.labelKey, lang)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Hero illustration — official Innovation Passport */}
          <div className="animate-fade-in-right">
            <div className="border-2 border-gov-rule shadow-lg">
              <div className="bg-gov-navy px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-md bg-amber-400 flex items-center justify-center">
                    <Leaf className="w-5 h-5 text-gov-navy" />
                  </div>
                  <div>
                    <div className="text-white font-bold text-sm">{t('innovation_passport', lang)}</div>
                    <div className="text-[10px] text-blue-200">{t('landing_passport_digital_token', lang)}</div>
                  </div>
                </div>
                <BadgeCheck className="w-5 h-5 text-amber-400" />
              </div>
              <div className="px-6 py-5 grid grid-cols-1 gap-3">
                {[
                  [t('landing_botanical', lang), 'Jyotishmati · Celastrus paniculatus'],
                  [t('landing_dosage_form', lang), 'Tri-layer mucoadhesive buccal film'],
                  [t('landing_section3p_screen', lang), 'No identical TKDL record'],
                ].map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between gap-3 border border-gov-rule bg-gov-wash px-4 py-3">
                    <span className="text-[10px] font-bold uppercase tracking-wide text-gov-mute">{k}</span>
                    <span className="text-[12px] font-semibold text-gov-ink text-right">{v}</span>
                  </div>
                ))}
                <div className="border border-amber-300 bg-amber-50 px-4 py-3 flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wide text-amber-700">{t('landing_regulatory_map', lang)}</span>
                  <div className="flex gap-1.5">
                    {['IN', 'US', 'CA'].map((c) => (
                      <span key={c} className="text-[10px] font-bold bg-white border border-amber-300 text-amber-900 rounded px-2 py-0.5">{c}</span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-gov-rule flex items-center justify-between gap-3">
                <QrCode className="w-10 h-10 text-gov-navy" />
                <div className="text-[10px] text-gov-mute">{t('landing_qr_note', lang)}</div>
                <ChevronRight className="w-4 h-4 text-gov-blue" />
              </div>
            </div>
          </div>
        </section>

        {/* ── 4. About IP-SAKTI ─────────────────────────────────── */}
        <section id="about" className="scroll-mt-24 border border-gov-rule bg-white">
          <div className="px-6 lg:px-10 py-8 lg:py-10 grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-8 items-center">
            <div>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-gov-navy text-white text-[10px] font-bold uppercase tracking-wider mb-4">
                <Newspaper className="w-3 h-3 text-amber-400" /> {t('landing_about_ip_sakti', lang)}
              </span>
              <h3 className="text-3xl font-bold text-gov-navy font-display">{t('landing_what_is_ip_sakti', lang)}</h3>
              <div className="mt-3 h-1 w-24 bg-amber-500" aria-hidden="true" />
            </div>
            <div>
              <p className="text-[14px] lg:text-[15px] text-gov-ink leading-relaxed">
                {t('landing_about_desc', lang)}
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                {['landing_chip_multilingual', 'landing_chip_source_cited', 'landing_chip_dpdp_aligned', 'landing_chip_gigw'].map((k) => (
                  <span key={k} className="inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 rounded-full border border-gov-rule bg-gov-wash text-gov-navy">
                    <BadgeCheck className="w-3 h-3 text-gov-green" /> {t(k, lang)}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── 5. Feature cards ──────────────────────────────────── */}
        <section id="features" className="scroll-mt-24">
          <div className="text-center max-w-2xl mx-auto mb-9">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-gov-navy text-white text-[10px] font-bold uppercase tracking-wider mb-4 animate-fade-in-up">
              <ShieldCheck className="w-3 h-3 text-amber-400" /> {t('landing_platform_capabilities', lang)}
            </span>
            <h3 className="text-3xl lg:text-4xl font-bold text-gov-navy font-display">{t('landing_everything_in_portal', lang)}</h3>
            <p className="mt-3 text-sm text-gov-mute">{t('landing_six_modules', lang)}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f) => (
              <div key={f.id} className="group border border-gov-rule bg-white hover:border-gov-blue transition-colors animate-fade-in-up">
                <div className="h-1 bg-gov-blue" aria-hidden="true" />
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-11 h-11 rounded-md bg-gov-wash border border-gov-rule flex items-center justify-center group-hover:bg-gov-navy transition-colors">
                        <f.icon className="w-5 h-5 text-gov-blue group-hover:text-amber-400 transition-colors" />
                      </div>
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider text-amber-600">{t(f.tagKey, lang)}</div>
                        <h4 className="text-[15px] font-bold text-gov-navy group-hover:text-gov-blue transition-colors">{t(f.titleKey, lang)}</h4>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-gov-blue group-hover:translate-x-0.5 transition-all" />
                  </div>
                  <p className="text-[13px] text-gov-mute mb-4">{t(f.descKey, lang)}</p>
                  <div className="flex flex-wrap gap-2 mt-auto">
                    {f.pointKeys.map((p) => (
                      <span key={p} className="text-[11px] font-semibold px-2.5 py-1 rounded-md border border-gov-rule bg-gov-wash text-gov-ink group-hover:border-gov-blue transition-colors">
                        {t(p, lang)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── 6. How it works ───────────────────────────────────── */}
        <section id="process" className="scroll-mt-24 border border-gov-rule bg-gov-wash">
          <div className="px-6 lg:px-10 py-10 lg:py-14">
            <div className="text-center max-w-2xl mx-auto mb-12">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-amber-500 text-white text-[10px] font-bold uppercase tracking-wider mb-4 animate-fade-in-up">
                <Lightbulb className="w-3 h-3" /> {t('landing_nav_how', lang)}
              </span>
              <h3 className="text-3xl lg:text-4xl font-bold text-gov-navy font-display">{t('landing_one_journey', lang)}</h3>
              <p className="mt-3 text-sm text-gov-mute">
                {t('landing_six_stages', lang)}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {PROCESS.map((step, i) => {
                const Icon = step.icon;
                return (
                  <div key={step.key} className="bg-white border border-gov-rule p-6 flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center justify-center w-9 h-9 rounded-full bg-gov-navy">
                          <Icon className="w-4 h-4 text-amber-400" />
                        </span>
                        <span className="text-2xl font-bold text-slate-200 font-display">{String(i + 1).padStart(2, '0')}</span>
                      </div>
                      <CheckCircle2 className="w-5 h-5 text-gov-green" />
                    </div>
                    <h4 className="text-lg font-bold text-gov-navy font-display">{t(step.labelKey, lang)}</h4>
                    <p className="text-xs text-gov-mute leading-relaxed">{t(step.descKey, lang)}</p>
                    <div className="mt-auto h-1 w-full bg-gov-wash">
                      <div className="h-full w-1/3 bg-amber-500" aria-hidden="true" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── 7. Trusted knowledge sources ──────────────────────── */}
        <section id="sources" className="scroll-mt-24">
          <div className="text-center max-w-2xl mx-auto mb-9">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-gov-navy text-white text-[10px] font-bold uppercase tracking-wider mb-4 animate-fade-in-up">
              <Database className="w-3 h-3 text-amber-400" /> {t('landing_trusted_sources', lang)}
            </span>
            <h3 className="text-3xl lg:text-4xl font-bold text-gov-navy font-display">{t('landing_verified_references', lang)}</h3>
            <p className="mt-3 text-sm text-gov-mute">
              {t('landing_rag_grounding', lang)}
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {SOURCES.map((s) => (
              <a
                key={s.name}
                href={s.href}
                target="_blank"
                rel="noreferrer"
                className="group border border-gov-rule bg-white p-5 text-center hover:border-gov-blue transition-colors"
              >
                <div className="w-11 h-11 mx-auto rounded-md bg-gov-wash border border-gov-rule flex items-center justify-center mb-3 group-hover:bg-gov-navy transition-colors">
                  <s.icon className="w-5 h-5 text-gov-blue group-hover:text-amber-400 transition-colors" />
                </div>
                <div className="text-[12px] font-bold text-gov-navy leading-snug">{s.name}</div>
              </a>
            ))}
          </div>
        </section>
      </main>

      {/* ── Compliance footer ─────────────────────────────────── */}
      <footer id="contact" className="scroll-mt-20 bg-gov-navy text-blue-100 mt-6 border-t-4 border-amber-500">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 py-12 grid grid-cols-1 md:grid-cols-3 gap-8 text-[12px] leading-relaxed">
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center"><Leaf className="w-6 h-6 text-gov-blue" /></div>
              <div>
                <div className="text-white font-bold text-base font-display">{t('app_title', lang)}</div>
                <div className="text-blue-300 text-[10px]">{t('landing_footer_engine', lang)}</div>
              </div>
            </div>
            <p className="text-blue-300 text-[11px]">{t('landing_footer_desc', lang)}</p>
          </div>
          <div>
            <h4 className="text-white font-bold mb-3 text-[12px] uppercase tracking-wide">{t('landing_statutory_databases', lang)}</h4>
            <ul className="space-y-2 text-blue-300">
              <li><a href="https://tkdl.res.in/tkdl/langdefault/common/Home.asp" target="_blank" rel="noreferrer" className="hover:text-amber-300 underline-offset-2 hover:underline">{t('landing_db_tkdl', lang)}</a></li>
              <li><a href="https://ipindia.gov.in/" target="_blank" rel="noreferrer" className="hover:text-amber-300 underline-offset-2 hover:underline">{t('landing_db_ipindia', lang)}</a></li>
              <li><a href="https://patentscope.wipo.int/" target="_blank" rel="noreferrer" className="hover:text-amber-300 underline-offset-2 hover:underline">WIPO PATENTSCOPE</a></li>
              <li><a href="https://www.canada.ca/en/health-canada/services/drugs-health-products/natural-non-prescription.html" target="_blank" rel="noreferrer" className="hover:text-amber-300 underline-offset-2 hover:underline">{t('landing_db_health_canada', lang)}</a></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-bold mb-3 text-[12px] uppercase tracking-wide">{t('landing_gigw_compliance', lang)}</h4>
            <ul className="space-y-2 text-blue-300">
              <li>{t('landing_gigw_stqc', lang)}</li>
              <li>{t('landing_gigw_keyboard', lang)}</li>
              <li>{t('landing_gigw_language_switch', lang)}</li>
              <li>{t('landing_gigw_dpdp', lang)}</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-blue-800">
          <div className="max-w-7xl mx-auto px-4 lg:px-6 py-4 flex flex-wrap items-center justify-between gap-2 text-[10px] text-blue-300/80">
            <span>{t('landing_footer_copyright', lang)}</span>
            <span>{t('landing_footer_disclaimer', lang)}</span>
            <span>{t('landing_footer_last_synced', lang)}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}