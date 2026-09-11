'use client';
import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Leaf, ShieldCheck, Globe2, BookOpenCheck,
  ArrowRight, Scale, BadgeCheck, Lock, Languages,
  Landmark, Database, Newspaper, QrCode, ClipboardList,
  Award, ChevronRight,
} from 'lucide-react';
import { useLang } from '../lib/LangContext';
import GlassTiltCard from '../components/landing/GlassTiltCard';
import ThreeBackground from '../components/landing/ThreeBackground';
import Text3D from '../components/landing/Text3D';
import ProcessParallax from '../components/landing/ProcessParallax';
import WindLeaves from '../components/landing/WindLeaves';

const NAV_LINKS = [
  { id: 'hero', label: 'Home', hilabel: 'होम' },
  { id: 'about', label: 'About IP-SAKTI', hilabel: 'IP-SAKTI के बारे में' },
  { id: 'features', label: 'Features', hilabel: 'विशेषताएँ' },
  { id: 'process', label: 'How It Works', hilabel: 'यह कैसे काम करता है' },
  { id: 'sources', label: 'Knowledge Sources', hilabel: 'ज्ञान स्रोत' },
  { id: 'contact', label: 'Contact', hilabel: 'संपर्क' },
];

const FEATURES = [
  {
    tag: 'AI Service',
    taghi: 'AI सेवा',
    title: 'Patent Disclosure Sentinel',
    titlehi: 'पेटेंट प्रकटीकरण संतरी',
    desc: 'Detect invention disclosure before filing.',
    deschi: 'फाइलिंग से पहले आविष्कार प्रकटीकरण पकड़ें।',
    points: ['Upload documents', 'Disclosure detection', 'Risk score'],
    pointshi: ['दस्तावेज़ अपलोड', 'प्रकटीकरण जाँच', 'जोखिम स्कोर'],
    icon: ClipboardList,
  },
  {
    tag: 'Government',
    taghi: 'सरकारी',
    title: 'Section 3(p) Search',
    titlehi: 'सेक्शन 3(p) खोज',
    desc: 'Verify Traditional Knowledge protection.',
    deschi: 'पारंपरिक ज्ञान सुरक्षा सत्यापित करें।',
    points: ['Botanical validation', 'Prior-art lookup', 'Compliance result'],
    pointshi: ['बोटैनिकल सत्यापन', 'पूर्व-आधार खोज', 'अनुपालन परिणाम'],
    icon: Scale,
  },
  {
    tag: 'Passport',
    taghi: 'पासपोर्ट',
    title: 'Innovation Passport',
    titlehi: 'इनोवेशन पासपोर्ट',
    desc: 'Generate a digital innovation passport.',
    deschi: 'डिजिटल इनोवेशन पासपोर्ट बनाएँ।',
    points: ['QR verification', 'Version tracking', 'PDF export'],
    pointshi: ['QR सत्यापन', 'संस्करण ट्रैकिंग', 'PDF निर्यात'],
    icon: BadgeCheck,
  },
  {
    tag: 'Global',
    taghi: 'वैश्विक',
    title: 'Global Passport',
    titlehi: 'ग्लोबल पासपोर्ट',
    desc: 'Compare regulatory pathways.',
    deschi: 'विनियामक मार्गों की तुलना करें।',
    points: ['India · CDSCO', 'United States · FDA', 'Canada · NHPD'],
    pointshi: ['भारत · CDSCO', 'यूएस · FDA', 'कनाडा · NHPD'],
    icon: Globe2,
  },
  {
    tag: 'Compliance',
    taghi: 'अनुपालन',
    title: 'Claim Firewall',
    titlehi: 'क्लेम फायरवॉल',
    desc: 'Detect risky marketing claims.',
    deschi: 'जोखिम भरे मार्केटिंग दावे पकड़ें।',
    points: ['Label analysis', 'Safe wording', 'High-risk phrases'],
    pointshi: ['लेबल विश्लेषण', 'सुरक्षित शब्द', 'उच्च-जोखिम वाक्यांश'],
    icon: ShieldCheck,
  },
  {
    tag: 'RAG AI',
    taghi: 'RAG AI',
    title: 'Legal RAG Engine',
    titlehi: 'लीगल RAG इंजन',
    desc: 'Answer only using trusted knowledge sources.',
    deschi: 'केवल विश्वसनीय ज्ञान स्रोतों से उत्तर दें।',
    points: ['Government sources', 'Citation-based answers', '0% hallucination target'],
    pointshi: ['सरकारी स्रोत', 'उद्धरण-आधारित उत्तर', '0% भ्रम लक्ष्य'],
    icon: BookOpenCheck,
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
  { value: '94%', label: 'Section 3(p) compliance screens auto-grounded in TKDL', hilabel: 'सेक्शन 3(p) अनुपालन जाँच TKDL से स्वतः पुष्ट' },
  { value: '3', label: 'Regulatory jurisdictions mapped · IN · US · CA', hilabel: 'विनियामक क्षेत्र मैप किए · IN · US · CA' },
  { value: '0%', label: 'RAG hallucination target — every answer cites its source', hilabel: 'RAG भ्रम लक्ष्य — हर उत्तर स्रोत सहित' },
  { value: '9', label: 'Indian languages + English decision support', hilabel: '9 भारतीय भाषाएँ + अंग्रेज़ी निर्णय सहायता' },
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

  // Language helper
  const Hi = (en: string, hi: string) => (lang === 'hi' ? hi : en);

  // 3D scroll parallax — hero layers move at different depths with perspective tilt
  const [sy, setSy] = useState(0);
  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => setSy(window.scrollY));
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#F8FAF8] text-slate-800">
      {/* Skip link (GIGW) */}
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:bg-emerald-900 focus:text-white focus:px-4 focus:py-2 focus:rounded-lg focus:text-sm">
        Skip to main content
      </a>

      {/* ── 1. Government top bar ─────────────────────────────── */}
      <div className="bg-emerald-900 text-emerald-50">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 py-1.5 flex flex-wrap items-center justify-between gap-2 text-[11px] font-medium">
          <div className="flex items-center gap-2 tracking-wide">
            <span>भारत सरकार</span>
            <span className="text-emerald-400">|</span>
            <span>Government of India</span>
            <span className="text-emerald-400">|</span>
            <span>आयुष मंत्रालय</span>
            <span className="text-emerald-400">|</span>
            <span>Ministry of AYUSH</span>
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            <span className="hidden sm:inline text-emerald-300/80">{Hi('Accessibility', 'सुगमता')}</span>
            <button onClick={() => setFont(-1)} className="px-1.5 py-0.5 border border-emerald-500/40 rounded hover:bg-emerald-800" aria-label="Decrease text size">A−</button>
            <button onClick={() => setFont(0)} className="px-1.5 py-0.5 border border-emerald-500/40 rounded hover:bg-emerald-800" aria-label="Reset text size">A</button>
            <button onClick={() => setFont(1)} className="px-1.5 py-0.5 border border-emerald-500/40 rounded hover:bg-emerald-800" aria-label="Increase text size">A+</button>
            <span className="text-emerald-400/70">|</span>
            <label className="flex items-center gap-1.5">
              <Languages className="w-3.5 h-3.5 text-emerald-300" />
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value as 'en' | 'hi')}
                className="bg-emerald-900 border border-emerald-500/40 rounded px-1.5 py-0.5 text-emerald-50 text-[11px] cursor-pointer focus:outline-none"
              >
                <option value="en">English</option>
                <option value="hi">हिन्दी</option>
              </select>
            </label>
          </div>
        </div>
      </div>

      {/* ── 2. Official header ──────────────────────────────────── */}
      <div className="bg-white border-b border-emerald-200">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 py-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-700 to-emerald-900 flex items-center justify-center shadow-md shadow-emerald-900/20">
              <Leaf className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl lg:text-3xl font-black text-emerald-900 font-display tracking-tight leading-tight">
                {Hi('IP-SAKTI', 'आईपी-शक्ति')}
              </h1>
              <p className="text-xs lg:text-sm font-semibold text-slate-600">{Hi('IP-SAKTI SAHAYAK — AI Powered Ayurveda IP & Prior-Art Decision Engine', 'IP-SAKTI सहायक — AI-संचालित आयुर्वेद IP एवं पूर्व-आधार निर्णय इंजन')}</p>
              <p className="text-[11px] text-slate-500 mt-0.5">{Hi('Multilingual RAG-based decision support for Ayurveda intellectual property protection', 'आयुर्वेद बौद्धिक संपदा संरक्षण हेतु बहुभाषी RAG-आधारित निर्णय सहायता')}</p>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
            <button onClick={() => router.push('/login')} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-800 hover:bg-emerald-700 text-white text-[12px] font-bold transition-colors shrink-0">
              <Lock className="w-3.5 h-3.5" /> {Hi('Login', 'लॉगिन')}
            </button>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-[11px] font-bold text-emerald-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> {Hi('TKDL Sync Active', 'TKDL सिंक सक्रिय')}
            </span>
          </div>
        </div>
      </div>

      {/* ── Sticky navigation ──────────────────────────────────── */}
      <nav className="sticky top-0 z-40 bg-emerald-800 shadow-md shadow-emerald-900/20">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 flex items-center justify-between">
          <div className="flex items-center overflow-x-auto">
            {NAV_LINKS.map((l) => (
              <button key={l.id} onClick={() => scrollTo(l.id)} className="px-3.5 lg:px-5 py-3.5 text-[12px] lg:text-[13px] font-semibold text-emerald-50 hover:bg-emerald-700 hover:text-white whitespace-nowrap transition-colors">
                {Hi(l.label, l.hilabel)}
              </button>
            ))}
          </div>
          <button onClick={() => router.push('/login')} className="hidden md:inline-flex items-center gap-2 px-4 py-2 my-2 ml-4 bg-amber-500 hover:bg-amber-600 text-white text-[12px] font-bold rounded-lg transition-colors shrink-0">
            <Lock className="w-3.5 h-3.5" /> {Hi('Login', 'लॉगिन')}
          </button>
        </div>
      </nav>

      <ThreeBackground />
      <WindLeaves />

      <main id="main-content" className="mx-auto max-w-7xl px-4 lg:px-6 py-12 space-y-16">
        {/* ── 3. Hero section ───────────────────────────────────── */}
        <section id="hero" className="relative scroll-mt-20 grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-10 items-center">
          <div className="will-change-transform" style={{ transform: `translate3d(0, ${sy * 0.05}px, 0)` }}>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200 text-[11px] font-bold mb-5 animate-fade-in-left" style={{ animationDelay: '0s' }}>
              <Award className="w-3.5 h-3.5" /> {Hi('National Intellectual Property Awareness Mission · aligned portal', '\u0930\u093E\u0937\u094D\u091F\u094D\u0930\u0940\u092F \u092C\u094C\u0926\u094D\u0927\u093F\u0915 \u0938\u0902\u092A\u0926\u093E \u091C\u093E\u0917\u0930\u0942\u0915\u0924\u093E \u092E\u093F\u0936\u0928 \u0938\u0902\u0930\u0947\u0916\u093F\u0924 \u092A\u094B\u0930\u094D\u091F\u0932')}
            </span>
            <h2 className="text-4xl lg:text-5xl font-black text-emerald-900 font-display leading-[1.1] tracking-tight perspective-800 transform-style-3d">
              <Text3D
                as="span"
                text={Hi("Protect India\u2019s Traditional Knowledge", '\u092D\u093E\u0930\u0924 \u0915\u0947 \u092A\u093E\u0930\u0902\u092A\u0930\u093F\u0915 \u091C\u094D\u091E\u093E\u0928 \u0915\u0940 \u0938\u0941\u0930\u0915\u094D\u0937\u093E')}
                style="split-cascade"
                delay={100}
                className="inline-block animate-hero-3d-in"
              />{' '}
              <Text3D
                as="span"
                text={Hi('with AI', 'AI \u0938\u0947 \u0915\u0930\u0947\u0902')}
                style="typewriter"
                delay={800}
                className="inline-block text-emerald-600 animate-hero-3d-in"
              />
            </h2>
            <p className="mt-5 text-[15px] lg:text-base text-slate-600 leading-relaxed max-w-xl animate-fade-in-up" style={{ animationDelay: '0.5s' }}>
              {Hi(
                'IP-SAKTI helps researchers, startups, Ayurveda companies, universities, and innovators verify patent readiness, detect prior art, analyze compliance under Section 3(p), and generate AI-powered Innovation Passports using trusted government and scientific knowledge sources.',
                'IP-SAKTI शोधकर्ताओं, स्टार्टअप्स, आयुर्वेद कंपनियों, विश्वविद्यालयों और इनोवेटर्स को पेटेंट तैयारी सत्यापित करने, पूर्व-आधार पहचानने, सेक्शन 3(p) के तहत अनुपालन जाँचने और विश्वसनीय सरकारी एवं वैज्ञानिक ज्ञान स्रोतों से AI-संचालित इनोवेशन पासपोर्ट बनाने में मदद करता है।'
              )}
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3 animate-fade-in-up" style={{ animationDelay: '0.65s' }}>
              <button
                onClick={() => router.push('/login')}
                className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-emerald-800 hover:bg-emerald-700 text-white text-sm font-bold shadow-lg shadow-emerald-900/20 transition-all hover:scale-105 hover:shadow-xl active:scale-95"
              >
                <Lock className="w-4 h-4" /> {Hi('Login', '\u0932\u0949\u0917\u093F\u0928')}
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => scrollTo('features')}
                className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-white border-2 border-emerald-200 hover:border-emerald-400 text-emerald-900 text-sm font-bold transition-all hover:scale-105 hover:shadow-lg active:scale-95"
              >
                {Hi('Explore Features', '\u0935\u093F\u0936\u0947\u0937\u0924\u093E\u090F\u0901 \u0926\u0947\u0916\u0947\u0902')}
              </button>
            </div>
            <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
              {STATS.map((s, i) => (
                <div
                  key={s.label}
                  className="rounded-xl bg-white border border-slate-300 p-3.5 will-change-transform animate-card-rise hover:shadow-lg hover:border-emerald-300 transition-all duration-300 group hover:[transform:perspective(600px)_rotateX(6deg)_translateY(-3px)_scale(1.02)]"
                  style={{ transform: `translate3d(0, ${sy * (0.02 + i * 0.015)}px, 0)`, animationDelay: `${0.8 + i * 0.1}s` }}
                >
                  <div className="text-2xl font-black text-emerald-900 group-hover:scale-110 group-hover:text-emerald-700 transition-all duration-300 origin-left">{s.value}</div>
                  <div className="text-[10px] text-slate-600 mt-1 leading-snug group-hover:text-slate-800 transition-colors duration-300">{Hi(s.label, s.hilabel)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Hero illustration — stylised Innovation Passport (3D scroll parallax) */}
          <div className="relative will-change-transform animate-fade-in-right" style={{ perspective: '1100px', animationDelay: '0.3s' }}>
            <div
              className="absolute -inset-6 rounded-[2rem] bg-gradient-to-br from-emerald-100 via-white to-amber-100 opacity-70 blur-2xl will-change-transform"
              aria-hidden="true"
              style={{ transform: `translate3d(${sy * 0.04}px, ${sy * -0.12}px, 0) scale(${1 + sy * 0.0004})` }}
            />
            <div
              className="will-change-transform"
              style={{ transform: `rotateX(${Math.min(10, sy * 0.012)}deg) translate3d(0, ${sy * -0.06}px, 0)` }}
            >
            <GlassTiltCard intensity={12} className="rounded-3xl">
            <div className="relative rounded-3xl bg-white border-2 border-emerald-200 shadow-xl shadow-emerald-900/10 overflow-hidden">
              <div className="bg-emerald-900 px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-amber-400 flex items-center justify-center">
                    <Leaf className="w-5 h-5 text-emerald-900" />
                  </div>
                  <div>
                    <div className="text-white font-black text-sm">{Hi('Innovation Passport', 'इनोवेशन पासपोर्ट')}</div>
                    <div className="text-[10px] text-emerald-300">{Hi('IP-SAKTI Sahayak · Digital Token', 'IP-SAKTI सहायक · डिजिटल टोकन')}</div>
                  </div>
                </div>
                <BadgeCheck className="w-5 h-5 text-emerald-300" />
              </div>
              <div className="px-6 py-5 grid grid-cols-1 gap-3">
                {[
                  [Hi('Botanical', 'वनस्पति'), 'Jyotishmati · Celastrus paniculatus'],
                  [Hi('Dosage form', 'खुराक रूप'), 'Tri-layer mucoadhesive buccal film'],
                  [Hi('Section 3(p) screen', 'सेक्शन 3(p) जाँच'), 'No identical TKDL record'],
                ].map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 border border-slate-200 px-4 py-3">
                    <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{k}</span>
                    <span className="text-[12px] font-semibold text-slate-900 text-right">{v}</span>
                  </div>
                ))}
                <div className="rounded-xl bg-white border border-amber-200 px-4 py-3 flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wide text-amber-700">{Hi('Regulatory map', 'विनियामक मानचित्र')}</span>
                  <div className="flex gap-1.5">
                    {['IN', 'US', 'CA'].map((c) => (
                      <span key={c} className="text-[10px] font-bold bg-amber-50 border border-amber-300 text-amber-900 rounded px-2 py-0.5">{c}</span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-slate-200 bg-white flex items-center justify-between gap-3">
                <QrCode className="w-10 h-10 text-emerald-900" />
                <div className="text-[10px] text-slate-700">{Hi('Issued with verified knowledge-source citations · Scan to verify authenticity', 'सत्यापित ज्ञान-स्रोत उद्धरणों के साथ जारी · प्रामाणिकता जाँच हेतु स्कैन करें')}</div>
                <ChevronRight className="w-4 h-4 text-emerald-600" />
              </div>
            </div>
          </GlassTiltCard>
            </div>
          </div>
        </section>

        {/* ── 4. About IP-SAKTI ─────────────────────────────────── */}
        <section id="about" className="scroll-mt-20 rounded-3xl bg-white border-2 border-emerald-200 shadow-sm overflow-hidden">
          <div className="px-6 lg:px-10 py-8 lg:py-10 grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-8 items-center">
            <div>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-800 text-white text-[10px] font-bold uppercase tracking-wider mb-4 animate-fade-in-left">
                <Newspaper className="w-3 h-3" /> {Hi('About IP-SAKTI', 'IP-SAKTI \u0915\u0947 \u092C\u093E\u0930\u0947 \u092E\u0947\u0902')}
              </span>
              <Text3D as="h3" text={Hi('What is IP-SAKTI?', 'IP-SAKTI \u0915\u094D\u092F\u093E \u0939\u0948?')} style="glitch" delay={200} className="text-3xl font-black text-emerald-900 font-display" />
            </div>
            <div>
              <p className="text-[14px] lg:text-[15px] text-slate-600 leading-relaxed">
                {Hi(
                  'IP-SAKTI is an AI-powered decision support platform designed for Ayurveda intellectual property protection. It combines Retrieval-Augmented Generation (RAG), multilingual botanical understanding, patent intelligence, and regulatory guidance to reduce IP risks before commercialization.',
                  'IP-SAKTI आयुर्वेद बौद्धिक संपदा संरक्षण हेतु बनाया गया AI-संचालित निर्णय सहायता प्लेटफ़ॉर्म है। यह Retrieval-Augmented Generation (RAG), बहुभाषी वनस्पति समझ, पेटेंट इंटेलिजेंस और विनियामक मार्गदर्शन को जोड़कर व्यावसायीकरण से पहले IP जोखिम कम करता है।'
                )}
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                {[
                  ['Multilingual', 'बहुभाषी'],
                  ['Source-cited answers', 'स्रोत-युक्त उत्तर'],
                  ['DPDP Act 2023 aligned', 'DPDP अधिनियम 2023 अनुरूप'],
                  ['GIGW 3.0 accessibility', 'GIGW 3.0 सुगमता'],
                ].map(([en, hinetxt]) => (
                  <span key={en} className="inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 rounded-full bg-slate-900 text-white">
                    <BadgeCheck className="w-3 h-3" /> {Hi(en, hinetxt)}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── 5. Feature cards ──────────────────────────────────── */}
        <section id="features" className="scroll-mt-20">
          <div className="text-center max-w-2xl mx-auto mb-9">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-800 text-white text-[10px] font-bold uppercase tracking-wider mb-4 animate-fade-in-up">
              <ShieldCheck className="w-3 h-3" /> {Hi('Platform Capabilities', '\u092A\u094D\u0932\u0947\u091F\u092B\u093C\u0949\u0930\u094D\u092E \u0915\u094D\u0937\u092E\u0924\u093E\u090F\u0901')}
            </span>
            <Text3D as="h3" text={Hi('Everything in one trusted portal', '\u0938\u092C \u0915\u0941\u091B \u090F\u0915 \u0935\u093F\u0936\u094D\u0935\u0938\u0928\u0940\u092F \u092A\u094B\u0930\u094D\u091F\u0932 \u092E\u0947\u0902')} style="wave" delay={200} className="text-3xl lg:text-4xl font-black text-emerald-900 font-display" />
            <p className="mt-3 text-sm text-slate-600 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>{Hi('Six expert modules for the complete Ayurveda IP lifecycle — from idea to export.', '\u0906\u092F\u0941\u0930\u094D\u0935\u0947\u0926 IP \u091C\u0940\u0935\u0928\u091A\u0915\u094D\u0930 \u0939\u0947\u0924\u0941 \u091B\u0939 \u0935\u093F\u0936\u0947\u0937\u094D\u091C\u094D\u091E \u092E\u0949\u0921\u094D\u092F\u0942\u0932 \u2014 \u0935\u093F\u091A\u093E\u0930 \u0938\u0947 \u0928\u093F\u0930\u094D\u092F\u093E\u0924 \u0924\u0915\u093F\u0902\u0964')}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {FEATURES.map((f, fi) => (
              <div key={f.title} className="animate-card-rise" style={{ animationDelay: `${fi * 90}ms` }}>
              <GlassTiltCard key={f.title} className="h-full" intensity={10} glowColor="rgba(16,185,129,0.16)">
                <div className="p-6 flex flex-col h-full transform-style-3d">
<div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3" style={{ transform: 'translateZ(28px)' }}>
                        <div className="w-11 h-11 rounded-xl bg-emerald-900 flex items-center justify-center transition-all duration-300 group-hover:scale-110 group-hover:rotate-6 group-hover:shadow-lg group-hover:shadow-emerald-900/30">
                          <f.icon className="w-5 h-5 text-amber-400 transition-all duration-300 group-hover:text-white" />
                        </div>
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-amber-700">{Hi(f.tag, f.taghi)}</div>
                          <h4 className="text-[15px] font-black text-slate-900 group-hover:text-emerald-800 transition-colors duration-300">{Hi(f.title, f.titlehi)}</h4>
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-600 group-hover:translate-x-1 group-hover:scale-125 transition-all duration-300" style={{ transform: 'translateZ(20px)' }} />
                    </div>
                    <p className="text-[13px] text-slate-700 mb-4" style={{ transform: 'translateZ(16px)' }}>{Hi(f.desc, f.deschi)}</p>
                    <div className="flex flex-wrap gap-2 mt-auto" style={{ transform: 'translateZ(12px)' }}>
                      {f.points.map((p, pi) => (
                        <span key={p} className="text-[11px] font-bold px-2.5 py-1 rounded-lg bg-slate-900 text-white border border-slate-900 transition-all duration-300 group-hover:bg-emerald-800 group-hover:border-emerald-700 group-hover:-translate-y-0.5" style={{ transitionDelay: `${pi * 60}ms` }}>
                          {lang === 'hi' ? f.pointshi[pi] : p}
                        </span>
                      ))}
                    </div>
                </div>
              </GlassTiltCard>
              </div>
            ))}
          </div>
        </section>

        {/* ── 6. Why choose IP-SAKTI ─────────────────────────────── */}
        <ProcessParallax />

        {/* ── 7. Trusted knowledge sources ──────────────────────── */}
        <section id="sources" className="scroll-mt-20">
          <div className="text-center max-w-2xl mx-auto mb-9">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-800 text-white text-[10px] font-bold uppercase tracking-wider mb-4 animate-fade-in-up">
              <Database className="w-3 h-3" /> {Hi('Trusted Knowledge Sources', '\u0935\u093F\u0936\u094D\u0935\u0938\u0928\u0940\u092F \u091C\u094D\u091E\u093E\u0928 \u0938\u094D\u0930\u094B\u0924')}
            </span>
            <Text3D as="h3" text={Hi('Answers grounded in verified references', '\u0938\u0924\u094D\u092F\u093E\u092A\u093F\u0924 \u0938\u0902\u0926\u0930\u094D\u092D\u094B\u0902 \u092E\u0947\u0902 \u0906\u0927\u093E\u0930\u093F\u0924 \u0909\u0924\u094D\u0924\u0930')} style="flip3d" delay={200} className="text-3xl lg:text-4xl font-black text-emerald-900 font-display" />
            <p className="mt-3 text-sm text-slate-600 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              {Hi('AI responses are grounded in verified knowledge sources through Retrieval-Augmented Generation (RAG).', 'AI \u0909\u0924\u094D\u0924\u0930 Retrieval-Augmented Generation (RAG) \u0915\u0947 \u092E\u093E\u0927\u094D\u092F\u092E \u0938\u0947 \u0938\u0924\u094D\u092F\u093E\u092A\u093F\u0924 \u091C\u094D\u091E\u093E\u0928 \u0938\u094D\u0930\u094B\u0924\u094B\u0902 \u092E\u0947\u0902 \u0906\u0927\u093E\u0930\u093F\u0924 \u0939\u0948\u0902\u0964')}
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {SOURCES.map((s, si) => (
              <a
                key={s.name}
                href={s.href}
                target="_blank"
                rel="noreferrer"
                className="group rounded-2xl bg-white border-2 border-emerald-200 shadow-sm p-5 text-center hover:border-emerald-400 hover:-translate-y-1.5 hover:shadow-lg transition-all duration-300 animate-card-rise will-change-transform hover:[transform:perspective(500px)_rotateX(8deg)_translateY(-6px)_scale(1.03)]"
                style={{ animationDelay: `${si * 80}ms` }}
              >
                <div className="w-11 h-11 mx-auto rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center mb-3 group-hover:bg-emerald-900 transition-all duration-300 group-hover:scale-110 group-hover:-rotate-6 group-hover:shadow-lg group-hover:shadow-emerald-900/20">
                  <s.icon className="w-5 h-5 text-emerald-800 group-hover:text-amber-400 transition-colors duration-300" />
                </div>
                <div className="text-[12px] font-bold text-slate-800 leading-snug group-hover:text-emerald-800 transition-colors duration-300">{s.name}</div>
                <div className="mt-1.5 h-0.5 w-0 mx-auto bg-emerald-500 transition-all duration-300 group-hover:w-full rounded-full" />
              </a>
            ))}
          </div>
        </section>
      </main>

      {/* ── Compliance footer ─────────────────────────────────── */}
      <footer id="contact" className="scroll-mt-20 bg-emerald-900 text-emerald-100 mt-6">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 py-12 grid grid-cols-1 md:grid-cols-3 gap-8 text-[12px] leading-relaxed">
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-800 border border-emerald-700 flex items-center justify-center"><Leaf className="w-6 h-6 text-amber-400" /></div>
              <div>
                <div className="text-white font-black text-base">{Hi('IP-SAKTI', 'आईपी-शक्ति')}</div>
                <div className="text-emerald-300/80 text-[10px]">{Hi('IP-SAKTI SAHAYAK — Ayurveda IP & Prior-Art Decision Engine', 'IP-SAKTI \u0938\u0939\u093E\u092F\u0915 \u2014 \u0906\u092F\u0941\u0930\u094D\u0935\u0947\u0926 IP \u090F\u0935\u0902 \u092A\u0942\u0930\u094D\u0935-\u0906\u0927\u093E\u0930 \u0928\u093F\u0930\u094D\u0923\u092F \u0907\u0902\u091C\u0928')}</div>
              </div>
            </div>
            <p className="text-emerald-200/80 text-[11px]">{Hi('Multilingual, RAG-based (source-cited) decision support for Ayurveda intellectual property and cross-border regulatory compliance.', 'आयुर्वेद बौद्धिक संपदा और सीमापार विनियामक अनुपालन हेतु बहुभाषी, RAG-आधारित (स्रोत-उद्धृत) निर्णय सहायता।')}</p>
            <button onClick={() => router.push('/login')} className="mt-4 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-[12px] font-bold transition-colors">
              <Lock className="w-3.5 h-3.5" /> {Hi('Secure Login', 'सुरक्षित लॉगिन')}
            </button>
          </div>
          <div>
            <h4 className="text-white font-bold mb-3 text-[12px] uppercase tracking-wide">{Hi('Statutory Databases', 'क़ानूनी डेटाबेस')}</h4>
            <ul className="space-y-2 text-emerald-200/80">
              <li><a href="https://tkdl.res.in/tkdl/langdefault/common/Home.asp" target="_blank" rel="noreferrer" className="hover:text-white underline-offset-2 hover:underline">CSIR-TKDL (Traditional Knowledge Digital Library)</a></li>
              <li><a href="https://ipindia.gov.in/" target="_blank" rel="noreferrer" className="hover:text-white underline-offset-2 hover:underline">IP India — Patent Search</a></li>
              <li><a href="https://patentscope.wipo.int/" target="_blank" rel="noreferrer" className="hover:text-white underline-offset-2 hover:underline">WIPO PATENTSCOPE</a></li>
              <li><a href="https://www.canada.ca/en/health-canada/services/drugs-health-products/natural-non-prescription.html" target="_blank" rel="noreferrer" className="hover:text-white underline-offset-2 hover:underline">Health Canada — NHPR</a></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-bold mb-3 text-[12px] uppercase tracking-wide">{Hi('GIGW 3.0 Compliance', 'GIGW 3.0 अनुपालन')}</h4>
            <ul className="space-y-2 text-emerald-200/80">
              <li>{Hi('STQC / WCAG 2.1 AA accessibility guidance followed', 'STQC / WCAG 2.1 AA सुगमता मार्गदर्शन का पालन')}</li>
              <li>{Hi('Skip-navigation, keyboard operability, text scaling enabled', 'स्किप-नेविगेशन, कीबोर्ड संचालन, टेक्स्ट स्केलिंग सक्षम')}</li>
              <li>{Hi('Language switching (English / हिन्दी) supported', 'भाषा परिवर्तन (English / हिन्दी) समर्थित')}</li>
              <li>{Hi('DPDP Act 2023 — consent logging active · data residency ap-south-1', 'DPDP अधिनियम 2023 — सहमति लॉगिंग सक्रिय · डेटा निवास ap-south-1')}</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-emerald-800">
          <div className="max-w-7xl mx-auto px-4 lg:px-6 py-4 flex flex-wrap items-center justify-between gap-2 text-[10px] text-emerald-300/70">
            <span>© 2026 IP-SAKTI Portal · IP-SAKTI Sahayak · Content provided for informational guidance; consult a qualified patent agent for final decisions.</span>
            <span>Last synced with CSIR-TKDL & WIPO PATENTSCOPE</span>
          </div>
        </div>
      </footer>
    </div>
  );
}