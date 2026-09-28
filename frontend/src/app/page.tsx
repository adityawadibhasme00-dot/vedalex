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
    tag: 'Regulatory',
    taghi: 'विनियामक',
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
    points: ['Statutory sources', 'Citation-based answers', '0% hallucination target'],
    pointshi: ['क़ानूनी स्रोत', 'उद्धरण-आधारित उत्तर', '0% भ्रम लक्ष्य'],
    icon: BookOpenCheck,
  },
];

const PROCESS = [
  {
    key: 'idea',
    label: 'Idea',
    hilabel: 'विचार',
    icon: Lightbulb,
    descEn: 'Document your formulation, botanical ingredients and intended claims in one structured innovation dossier.',
    descHi: 'अपने फॉर्मूलेशन, वनस्पति घटकों और इच्छित दावों को एक संरचित इनोवेशन डोज़ियर में दर्ज करें।',
  },
  {
    key: 'verification',
    label: 'Verification',
    hilabel: 'जाँच',
    icon: Search,
    descEn: 'AI validates botanical identity and cross-matches 9 Indian languages.',
    descHi: 'AI वनस्पति पहचान सत्यापित करता है और 9 भारतीय भाषाओं में मिलान करता है।',
  },
  {
    key: 'prior-art',
    label: 'Prior Art',
    hilabel: 'पूर्व आधार',
    icon: FileText,
    descEn: 'RAG engine sweeps TKDL, IP India, WIPO, PubMed and WHO to uncover overlapping disclosures.',
    descHi: 'RAG इंजन TKDL, IP India, WIPO, PubMed और WHO में झाँककर अतिव्यापी प्रकटीकरण खोजता है।',
  },
  {
    key: 'readiness',
    label: 'Patent Readiness',
    hilabel: 'पेटेंट तैयारी',
    icon: BadgeCheck,
    descEn: 'Section 3(p) compliance score with TKDL grounding and claim-by-claim risk analysis.',
    descHi: 'TKDL-पुष्ट सेक्शन 3(p) अनुपालन स्कोर और दावे-दर-दावे जोखिम विश्लेषण।',
  },
  {
    key: 'passport',
    label: 'Innovation Passport',
    hilabel: 'इनोवेशन पासपोर्ट',
    icon: QrCode,
    descEn: 'A verifiable digital passport with QR authenticity, version history and PDF export.',
    descHi: 'QR प्रामाणिकता, संस्करण इतिहास और PDF निर्यात के साथ सत्यापन-योग्य डिजिटल पासपोर्ट।',
  },
  {
    key: 'export',
    label: 'Export',
    hilabel: 'निर्यात',
    icon: FileDown,
    descEn: 'Regulatory pathway maps for IN · US · CA jurisdictions to launch your innovation worldwide.',
    descHi: 'IN · US · CA क्षेत्रों के लिए विनियामक मार्ग-मानचित्र — वैश्विक स्तर पर लॉन्च करें।',
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

  return (
    <div className="min-h-screen bg-white text-gov-ink">
      {/* Skip link (GIGW) */}
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:bg-gov-navy focus:text-white focus:px-4 focus:py-2 focus:rounded-md focus:text-sm">
        Skip to main content
      </a>

      {/* ── 1. Utility strip (navy) ─────────────────────────────── */}
      <div className="bg-gov-navy text-blue-100">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 py-1.5 flex flex-wrap items-center justify-end gap-2 text-[11px] font-medium">
          <div className="ml-auto flex items-center gap-3 text-[11px]">
            <span className="hidden sm:inline text-blue-300">{Hi('Accessibility', 'सुगमता')}</span>
            <button onClick={() => setFont(-1)} className="px-1.5 py-0.5 border border-blue-400/40 rounded hover:bg-gov-blue" aria-label="Decrease text size">A−</button>
            <button onClick={() => setFont(0)} className="px-1.5 py-0.5 border border-blue-400/40 rounded hover:bg-gov-blue" aria-label="Reset text size">A</button>
            <button onClick={() => setFont(1)} className="px-1.5 py-0.5 border border-blue-400/40 rounded hover:bg-gov-blue" aria-label="Increase text size">A+</button>
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
                {Hi('IP-SAKTI', 'आईपी-शक्ति')}
              </h1>
              <p className="text-xs lg:text-sm font-semibold text-gov-blue uppercase tracking-wide">{Hi('IP-SAKTI SAHAYAK — AI Powered Ayurveda IP & Prior-Art Decision Engine', 'IP-SAKTI सहायक — AI-संचालित आयुर्वेद IP एवं पूर्व-आधार निर्णय इंजन')}</p>
              <p className="text-[11px] text-gov-mute mt-0.5">{Hi('Multilingual RAG-based decision support for Ayurveda intellectual property protection', 'आयुर्वेद बौद्धिक संपदा संरक्षण हेतु बहुभाषी RAG-आधारित निर्णय सहायता')}</p>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
            <button onClick={() => router.push('/login')} className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-amber-500 hover:bg-amber-600 text-white text-[12px] font-bold transition-colors shrink-0">
              <Lock className="w-3.5 h-3.5" /> {Hi('Login', 'लॉगिन')}
            </button>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gov-wash border border-gov-rule text-[11px] font-bold text-gov-green">
              <span className="w-2 h-2 rounded-full bg-gov-green animate-pulse" /> {Hi('TKDL Sync Active', 'TKDL सिंक सक्रिय')}
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
                {Hi(l.label, l.hilabel)}
              </button>
            ))}
          </div>
          <button onClick={() => router.push('/login')} className="hidden md:inline-flex items-center gap-2 px-4 py-2 my-2 ml-4 bg-amber-500 hover:bg-amber-600 text-white text-[12px] font-bold rounded-md transition-colors shrink-0">
            <Lock className="w-3.5 h-3.5" /> {Hi('Login', 'लॉगिन')}
          </button>
        </div>
      </nav>

      <main id="main-content" className="mx-auto max-w-7xl px-4 lg:px-6 py-12 space-y-20">
        {/* ── 3. Hero section ───────────────────────────────────── */}
        <section id="hero" className="scroll-mt-24 grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-10 items-center">
          <div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gov-wash text-gov-blue border border-gov-rule text-[11px] font-bold mb-5 animate-fade-in-left">
              <Award className="w-3.5 h-3.5 text-amber-600" /> {Hi('National Intellectual Property Awareness Mission · aligned portal', '\u0930\u093E\u0937\u094D\u091F\u094D\u0930\u0940\u092F \u092C\u094C\u0926\u094D\u0927\u093F\u0915 \u0938\u0902\u092A\u0926\u093E \u091C\u093E\u0917\u0930\u0942\u0915\u0924\u093E \u092E\u093F\u0936\u0928 \u0938\u0902\u0930\u0947\u0916\u093F\u0924 \u092A\u094B\u0930\u094D\u091F\u0932')}
            </span>
            <h2 className="text-4xl lg:text-5xl font-bold text-gov-navy font-display leading-[1.15] tracking-tight animate-fade-in-up">
              {Hi("Protect India\u2019s Traditional Knowledge", '\u092D\u093E\u0930\u0924 \u0915\u0947 \u092A\u093E\u0930\u0902\u092A\u0930\u093F\u0915 \u091C\u094D\u091E\u093E\u0928 \u0915\u0940 \u0938\u0941\u0930\u0915\u094D\u0937\u093E')}{' '}
              <span className="text-gov-blue">{Hi('with AI', 'AI \u0938\u0947 \u0915\u0930\u0947\u0902')}</span>
            </h2>
            <p className="mt-5 text-[15px] lg:text-base text-gov-ink leading-relaxed max-w-xl animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
              {Hi(
                'IP-SAKTI helps researchers, startups, Ayurveda companies, universities, and innovators verify patent readiness, detect prior art, analyze compliance under Section 3(p), and generate AI-powered Innovation Passports using trusted statutory and scientific knowledge sources.',
                'IP-SAKTI शोधकर्ताओं, स्टार्टअप्स, आयुर्वेद कंपनियों, विश्वविद्यालयों और इनोवेटर्स को पेटेंट तैयारी सत्यापित करने, पूर्व-आधार पहचानने, सेक्शन 3(p) के तहत अनुपालन जाँचने और विश्वसनीय क़ानूनी एवं वैज्ञानिक ज्ञान स्रोतों से AI-संचालित इनोवेशन पासपोर्ट बनाने में मदद करता है।'
              )}
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3 animate-fade-in-up" style={{ animationDelay: '0.45s' }}>
              <button
                onClick={() => router.push('/login')}
                className="inline-flex items-center gap-2 px-7 py-3.5 rounded-md bg-gov-blue hover:bg-gov-navy text-white text-sm font-bold border border-gov-blueDk transition-colors"
              >
                <Lock className="w-4 h-4" /> {Hi('Login', '\u0932\u0949\u0917\u093F\u0928')}
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => scrollTo('features')}
                className="inline-flex items-center gap-2 px-7 py-3.5 rounded-md bg-white border-2 border-gov-rule hover:border-gov-blue text-gov-navy text-sm font-bold transition-colors"
              >
                {Hi('Explore Features', '\u0935\u093F\u0936\u0947\u0937\u0924\u093E\u090F\u0901 \u0926\u0947\u0916\u0947\u0902')}
              </button>
            </div>
            <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-4">
              {STATS.map((s) => (
                <div
                  key={s.label}
                  className="border-l-4 border-gov-blue bg-gov-wash p-4"
                >
                  <div className="text-2xl font-bold text-gov-navy font-display">{s.value}</div>
                  <div className="text-[10px] text-gov-mute mt-1 leading-snug">{Hi(s.label, s.hilabel)}</div>
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
                    <div className="text-white font-bold text-sm">{Hi('Innovation Passport', 'इनोवेशन पासपोर्ट')}</div>
                    <div className="text-[10px] text-blue-200">{Hi('IP-SAKTI Sahayak · Digital Token', 'IP-SAKTI सहायक · डिजिटल टोकन')}</div>
                  </div>
                </div>
                <BadgeCheck className="w-5 h-5 text-amber-400" />
              </div>
              <div className="px-6 py-5 grid grid-cols-1 gap-3">
                {[
                  [Hi('Botanical', 'वनस्पति'), 'Jyotishmati · Celastrus paniculatus'],
                  [Hi('Dosage form', 'खुराक रूप'), 'Tri-layer mucoadhesive buccal film'],
                  [Hi('Section 3(p) screen', 'सेक्शन 3(p) जाँच'), 'No identical TKDL record'],
                ].map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between gap-3 border border-gov-rule bg-gov-wash px-4 py-3">
                    <span className="text-[10px] font-bold uppercase tracking-wide text-gov-mute">{k}</span>
                    <span className="text-[12px] font-semibold text-gov-ink text-right">{v}</span>
                  </div>
                ))}
                <div className="border border-amber-300 bg-amber-50 px-4 py-3 flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wide text-amber-700">{Hi('Regulatory map', 'विनियामक मानचित्र')}</span>
                  <div className="flex gap-1.5">
                    {['IN', 'US', 'CA'].map((c) => (
                      <span key={c} className="text-[10px] font-bold bg-white border border-amber-300 text-amber-900 rounded px-2 py-0.5">{c}</span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-gov-rule flex items-center justify-between gap-3">
                <QrCode className="w-10 h-10 text-gov-navy" />
                <div className="text-[10px] text-gov-mute">{Hi('Issued with verified knowledge-source citations · Scan to verify authenticity', 'सत्यापित ज्ञान-स्रोत उद्धरणों के साथ जारी · प्रामाणिकता जाँच हेतु स्कैन करें')}</div>
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
                <Newspaper className="w-3 h-3 text-amber-400" /> {Hi('About IP-SAKTI', 'IP-SAKTI \u0915\u0947 \u092C\u093E\u0930\u0947 \u092E\u0947\u0902')}
              </span>
              <h3 className="text-3xl font-bold text-gov-navy font-display">{Hi('What is IP-SAKTI?', 'IP-SAKTI \u0915\u094D\u092F\u093E \u0939\u0948?')}</h3>
              <div className="mt-3 h-1 w-24 bg-amber-500" aria-hidden="true" />
            </div>
            <div>
              <p className="text-[14px] lg:text-[15px] text-gov-ink leading-relaxed">
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
                  <span key={en} className="inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 rounded-full border border-gov-rule bg-gov-wash text-gov-navy">
                    <BadgeCheck className="w-3 h-3 text-gov-green" /> {Hi(en, hinetxt)}
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
              <ShieldCheck className="w-3 h-3 text-amber-400" /> {Hi('Platform Capabilities', '\u092A\u094D\u0932\u0947\u091F\u092B\u093C\u0949\u0930\u094D\u092E \u0915\u094D\u0937\u092E\u0924\u093E\u090F\u0901')}
            </span>
            <h3 className="text-3xl lg:text-4xl font-bold text-gov-navy font-display">{Hi('Everything in one trusted portal', '\u0938\u092C \u0915\u0941\u091B \u090F\u0915 \u0935\u093F\u0936\u094D\u0935\u0938\u0928\u0940\u092F \u092A\u094B\u0930\u094D\u091F\u0932 \u092E\u0947\u0902')}</h3>
            <p className="mt-3 text-sm text-gov-mute">{Hi('Six expert modules for the complete Ayurveda IP lifecycle — from idea to export.', '\u0906\u092F\u0941\u0930\u094D\u0935\u0947\u0926 IP \u091C\u0940\u0935\u0928\u091A\u0915\u094D\u0930 \u0939\u0947\u0924\u0941 \u091B\u0939 \u0935\u093F\u0936\u0947\u0937\u094D\u091C\u094D\u091E \u092E\u0949\u0921\u094D\u092F\u0942\u0932 \u2014 \u0935\u093F\u091A\u093E\u0930 \u0938\u0947 \u0928\u093F\u0930\u094D\u092F\u093E\u0924 \u0924\u0915\u093F\u0902\u0964')}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f) => (
              <div key={f.title} className="group border border-gov-rule bg-white hover:border-gov-blue transition-colors animate-fade-in-up">
                <div className="h-1 bg-gov-blue" aria-hidden="true" />
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-11 h-11 rounded-md bg-gov-wash border border-gov-rule flex items-center justify-center group-hover:bg-gov-navy transition-colors">
                        <f.icon className="w-5 h-5 text-gov-blue group-hover:text-amber-400 transition-colors" />
                      </div>
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider text-amber-600">{Hi(f.tag, f.taghi)}</div>
                        <h4 className="text-[15px] font-bold text-gov-navy group-hover:text-gov-blue transition-colors">{Hi(f.title, f.titlehi)}</h4>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-gov-blue group-hover:translate-x-0.5 transition-all" />
                  </div>
                  <p className="text-[13px] text-gov-mute mb-4">{Hi(f.desc, f.deschi)}</p>
                  <div className="flex flex-wrap gap-2 mt-auto">
                    {f.points.map((p, pi) => (
                      <span key={p} className="text-[11px] font-semibold px-2.5 py-1 rounded-md border border-gov-rule bg-gov-wash text-gov-ink group-hover:border-gov-blue transition-colors">
                        {lang === 'hi' ? f.pointshi[pi] : p}
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
                <Lightbulb className="w-3 h-3" /> {Hi('How It Works', '\u092F\u0939 \u0915\u0948\u0938\u0947 \u0915\u093E\u092E \u0915\u0930\u0924\u093E \u0939\u0948')}
              </span>
              <h3 className="text-3xl lg:text-4xl font-bold text-gov-navy font-display">{Hi('One journey, every safeguard', '\u090F\u0915 \u092F\u093E\u0924\u094D\u0930\u093E, \u0939\u0930 \u0938\u0941\u0930\u0915\u094D\u0937\u093E')}</h3>
              <p className="mt-3 text-sm text-gov-mute">
                {Hi('Six stages from idea to global export — every stage grounded in statutory sources: TKDL, IP India, WIPO, PubMed, and WHO.', '\u0935\u093F\u091A\u093E\u0930 \u0938\u0947 \u0935\u0948\u0936\u094D\u0935\u093F\u0915 \u0928\u093F\u0930\u094D\u092F\u093E\u0924 \u0924\u0915 \u091B\u0939 \u091A\u0930\u0923 \u2014 \u0939\u0930 \u091A\u0930\u0923 \u0915\u093C\u093E\u0928\u0942\u0928\u0940 \u0938\u094D\u0930\u094B\u0924\u094B\u0902 \u0938\u0947 \u092A\u0941\u0937\u094D\u091F: TKDL, IP India, WIPO, PubMed, \u0914\u0930 WHO\u0964')}
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
                    <h4 className="text-lg font-bold text-gov-navy font-display">{Hi(step.label, step.hilabel)}</h4>
                    <p className="text-xs text-gov-mute leading-relaxed">{Hi(step.descEn, step.descHi)}</p>
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
              <Database className="w-3 h-3 text-amber-400" /> {Hi('Trusted Knowledge Sources', '\u0935\u093F\u0936\u094D\u0935\u0938\u0928\u0940\u092F \u091C\u094D\u091E\u093E\u0928 \u0938\u094D\u0930\u094B\u0924')}
            </span>
            <h3 className="text-3xl lg:text-4xl font-bold text-gov-navy font-display">{Hi('Answers grounded in verified references', '\u0938\u0924\u094D\u092F\u093E\u092A\u093F\u0924 \u0938\u0902\u0926\u0930\u094D\u092D\u094B\u0902 \u092E\u0947\u0902 \u0906\u0927\u093E\u0930\u093F\u0924 \u0909\u0924\u094D\u0924\u0930')}</h3>
            <p className="mt-3 text-sm text-gov-mute">
              {Hi('AI responses are grounded in verified knowledge sources through Retrieval-Augmented Generation (RAG).', 'AI \u0909\u0924\u094D\u0924\u0930 Retrieval-Augmented Generation (RAG) \u0915\u0947 \u092E\u093E\u0927\u094D\u092F\u092E \u0938\u0947 \u0938\u0924\u094D\u092F\u093E\u092A\u093F\u0924 \u091C\u094D\u091E\u093E\u0928 \u0938\u094D\u0930\u094B\u0924\u094B\u0902 \u092E\u0947\u0902 \u0906\u0927\u093E\u0930\u093F\u0924 \u0939\u0948\u0902\u0964')}
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
                <div className="text-white font-bold text-base font-display">{Hi('IP-SAKTI', 'आईपी-शक्ति')}</div>
                <div className="text-blue-300 text-[10px]">{Hi('IP-SAKTI SAHAYAK — Ayurveda IP & Prior-Art Decision Engine', 'IP-SAKTI \u0938\u0939\u093E\u092F\u0915 \u2014 \u0906\u092F\u0941\u0930\u094D\u0935\u0947\u0926 IP \u090F\u0935\u0902 \u092A\u0942\u0930\u094D\u0935-\u0906\u0927\u093E\u0930 \u0928\u093F\u0930\u094D\u0923\u092F \u0907\u0902\u091C\u0928')}</div>
              </div>
            </div>
            <p className="text-blue-300 text-[11px]">{Hi('Multilingual, RAG-based (source-cited) decision support for Ayurveda intellectual property and cross-border regulatory compliance.', 'आयुर्वेद बौद्धिक संपदा और सीमापार विनियामक अनुपालन हेतु बहुभाषी, RAG-आधारित (स्रोत-उद्धृत) निर्णय सहायता।')}</p>
            <button onClick={() => router.push('/login')} className="mt-4 inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-amber-500 hover:bg-amber-600 text-white text-[12px] font-bold transition-colors">
              <Lock className="w-3.5 h-3.5" /> {Hi('Secure Login', 'सुरक्षित लॉगिन')}
            </button>
          </div>
          <div>
            <h4 className="text-white font-bold mb-3 text-[12px] uppercase tracking-wide">{Hi('Statutory Databases', 'क़ानूनी डेटाबेस')}</h4>
            <ul className="space-y-2 text-blue-300">
              <li><a href="https://tkdl.res.in/tkdl/langdefault/common/Home.asp" target="_blank" rel="noreferrer" className="hover:text-amber-300 underline-offset-2 hover:underline">CSIR-TKDL (Traditional Knowledge Digital Library)</a></li>
              <li><a href="https://ipindia.gov.in/" target="_blank" rel="noreferrer" className="hover:text-amber-300 underline-offset-2 hover:underline">IP India — Patent Search</a></li>
              <li><a href="https://patentscope.wipo.int/" target="_blank" rel="noreferrer" className="hover:text-amber-300 underline-offset-2 hover:underline">WIPO PATENTSCOPE</a></li>
              <li><a href="https://www.canada.ca/en/health-canada/services/drugs-health-products/natural-non-prescription.html" target="_blank" rel="noreferrer" className="hover:text-amber-300 underline-offset-2 hover:underline">Health Canada — NHPR</a></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-bold mb-3 text-[12px] uppercase tracking-wide">{Hi('GIGW 3.0 Compliance', 'GIGW 3.0 अनुपालन')}</h4>
            <ul className="space-y-2 text-blue-300">
              <li>{Hi('STQC / WCAG 2.1 AA accessibility guidance followed', 'STQC / WCAG 2.1 AA सुगमता मार्गदर्शन का पालन')}</li>
              <li>{Hi('Skip-navigation, keyboard operability, text scaling enabled', 'स्किप-नेविगेशन, कीबोर्ड संचालन, टेक्स्ट स्केलिंग सक्षम')}</li>
              <li>{Hi('Language switching (English / हिन्दी) supported', 'भाषा परिवर्तन (English / हिन्दी) समर्थित')}</li>
              <li>{Hi('DPDP Act 2023 — consent logging active · data residency ap-south-1', 'DPDP अधिनियम 2023 — सहमति लॉगिंग सक्रिय · डेटा निवास ap-south-1')}</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-blue-800">
          <div className="max-w-7xl mx-auto px-4 lg:px-6 py-4 flex flex-wrap items-center justify-between gap-2 text-[10px] text-blue-300/80">
            <span>© 2026 IP-SAKTI Portal · IP-SAKTI Sahayak · Content provided for informational guidance; consult a qualified patent agent for final decisions.</span>
            <span>Vedalex is an independent research project and is not affiliated with, endorsed by, or representing any government or ministry. Portals named in the sources list are cited as data sources only.</span>
            <span>Last synced with CSIR-TKDL & WIPO PATENTSCOPE</span>
          </div>
        </div>
      </footer>
    </div>
  );
}