'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import {
  ShieldCheck,
  Scale,
  BadgeCheck,
  Globe2,
  BookOpenCheck,
  ClipboardList,
  Search,
  FileSearch,
  Landmark,
  Database,
  ArrowRight,
  CircleDot,
  FileText,
  Building2,
  FlaskConical,
} from 'lucide-react';
import { useLang } from '../lib/LangContext';
import GovFooter from '../components/landing/GovFooter';
import {
  GovUtilityBar,
  GovMasthead,
  GovNav,
  GovBreadcrumb,
} from '../components/landing/GovHeader';

/** The circular service icons that carry a public portal's front page. */
const SERVICES = [
  {
    icon: ClipboardList,
    title: 'Patent Disclosure Sentinel',
    titleHi: 'पेटेंट प्रकटीकरण संतरी',
    desc: 'Screen a disclosure before it is filed and flag what a examiner would raise.',
    deschi: 'फाइलिंग से पूर्व प्रकटीकरण की जाँच करें।',
    href: '/innovation-lab/agents/invention_disclosure',
  },
  {
    icon: Scale,
    title: 'Section 3(p) Clearance',
    titleHi: 'सेक्शन 3(p) मंज़ूरी',
    desc: 'Check a formulation against traditional knowledge entries and prior art.',
    deschi: 'पारंपरिक ज्ञान प्रविष्टियों और पूर्व-आधार से जाँच करें।',
    href: '/innovation-lab/agents/novelty_search',
  },
  {
    icon: FileSearch,
    title: 'Prior-Art Search',
    titleHi: 'पूर्व-आधार खोज',
    desc: 'Deterministic novelty and inventiveness assessment over cited passages.',
    deschi: 'उद्धृत अंशों पर आधारित नवीनता एवं आविष्कारशीलता आकलन।',
    href: '/innovation-lab/agents/prior_art_search',
  },
  {
    icon: BadgeCheck,
    title: 'Innovation Passport',
    titleHi: 'इनोवेशन पासपोर्ट',
    desc: 'Issue a versioned, QR-verifiable record of the search history.',
    deschi: 'खोज इतिहास का संस्करणित, QR-सत्यापन योग्य रिकॉर्ड जारी करें।',
    href: '/innovation-lab',
  },
  {
    icon: FlaskConical,
    title: 'Formulation Intelligence',
    titleHi: 'संयोजन बुद्धिमत्ता',
    desc: 'Excipient and process rationale grounded in pharmacopoeial monographs.',
    deschi: 'औषधि-कोश मोनोग्राफ़ पर आधारित सहायक एवं प्रक्रिया तर्क।',
    href: '/innovation-lab/agents/formulation',
  },
  {
    icon: Globe2,
    title: 'Cross-Border Pathway Map',
    titleHi: 'सीमापार मार्ग मानचित्र',
    desc: 'India, United States and Canada pathways side by side.',
    deschi: 'भारत, संयुक्त राज्य और कनाडा के मार्गों की तुलना।',
    href: '/innovation-lab',
  },
];

/** Flat card body, the plainest possible government-style service listing. */
const MODULES = [
  {
    icon: ShieldCheck,
    title: 'Claim Firewall',
    titleHi: 'दावा फायरवॉल',
    desc: 'Flags high-risk marketing language and proposes compliant wording.',
    deschi: 'उच्च-जोखिम विपणन भाषा चिह्नित करता है और अनुपालित शब्दावली प्रस्तावित करता है।',
    points: ['Label analysis', 'Safe wording', 'High-risk phrases'],
    pointshi: ['लेबल विश्लेषण', 'सुरक्षित शब्दावली', 'उच्च-जोखिम वाक्यांश'],
  },
  {
    icon: BookOpenCheck,
    title: 'Grounded Legal Retrieval',
    titleHi: 'आधारित विधिक पुनर्प्राप्ति',
    desc: 'Every answer resolves to a passage with its authority and effective date.',
    deschi: 'प्रत्येक उत्तर उसके प्राधिकरण सहित अंश तक जाता है।',
    points: ['Passage-level citation', 'Authority ranking', 'Gap reporting'],
    pointshi: ['अंश-स्तरीय उद्धरण', 'प्राधिकरण वर्गीकरण', 'अंतराल रिपोर्टिंग'],
  },
];

const STATS = [
  { value: '39', en: 'Registered agent workflows', hi: 'पंजीकृत एजेंट कार्यप्रवाह' },
  { value: '3', en: 'Regulatory jurisdictions mapped', hi: 'मैप किए गए विनियामक क्षेत्र' },
  { value: '6', en: 'Official knowledge sources', hi: 'आधिकारिक ज्ञान स्रोत' },
  { value: '10', en: 'Interface languages', hi: 'इंटरफ़ेस भाषाएँ' },
];

const NOTICES = [
  {
    date: '2026-09-12',
    en: 'Section 3(p) screening coverage extended to 12,400 traditional knowledge entries.',
    hi: 'सेक्शन 3(p) जाँच का विस्तार 12,400 पारंपरिक ज्ञान प्रविष्टियों तक किया गया।',
  },
  {
    date: '2026-08-28',
    en: 'United States and Canada regulatory pathway mapping added to the passport export.',
    hi: 'पासपोर्ट निर्यात में संयुक्त राज्य और कनाडा विनियामक मार्ग मानचित्रण जोड़ा गया।',
  },
  {
    date: '2026-08-05',
    en: 'Prior-art engine upgraded to cite the exact passage behind every novelty claim.',
    hi: 'पूर्व-आधार इंजन को प्रत्येक नवीनता दावे के पीछे का सटीक अंश उद्धृत करने हेतु उन्नत किया गया।',
  },
];

const SOURCES = [
  { name: 'Ministry of AYUSH', publisher: 'Government of India', href: 'https://ayush.gov.in/' },
  { name: 'CSIR-TKDL', publisher: 'Council of Scientific and Industrial Research', href: 'https://tkdl.res.in/' },
  { name: 'IP India', publisher: 'Office of the CGPDTM', href: 'https://ipindia.gov.in/' },
  { name: 'WIPO PATENTSCOPE', publisher: 'World Intellectual Property Organization', href: 'https://patentscope.wipo.int/' },
  { name: 'India Code', publisher: 'Legislative Department', href: 'https://www.indiacode.nic.in/' },
  { name: 'PubMed', publisher: 'National Library of Medicine', href: 'https://pubmed.ncbi.nlm.nih.gov/' },
];

export default function HomePage() {
  const { lang } = useLang();
  const router = useRouter();
  const T = (en: string, hi: string) => (lang === 'hi' ? hi : en);

  const goLogin = () => router.push('/login');

  return (
    <div className="min-h-screen bg-white text-gov-ink">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:bg-gov-blue focus:px-4 focus:py-3 focus:text-sm focus:font-semibold focus:text-white"
      >
        {T('Skip to main content', 'मुख्य सामग्री पर जाएँ')}
      </a>

      <GovUtilityBar />
      <GovMasthead onLogin={goLogin} />
      <GovNav onLogin={goLogin} active="home" />
      <GovBreadcrumb
        items={[{ label: T('Home', 'होम') }]}
      />

      <main id="main-content" className="mx-auto max-w-[1200px] px-4">
        {/* ── Portal search ─────────────────────────────────────────── */}
        <section aria-label={T('Portal search', 'पोर्टल खोज')} className="py-6">
          <form
            role="search"
            onSubmit={(e) => {
              e.preventDefault();
              router.push('/innovation-lab');
            }}
            className="flex flex-col gap-2 sm:flex-row"
          >
            <label htmlFor="portal-search" className="sr-only">
              {T('Search services and agents', 'सेवाएँ और एजेंट खोजें')}
            </label>
            <div className="flex flex-1 items-stretch border-2 border-gov-blue">
              <Search aria-hidden="true" className="ml-3 w-5 shrink-0 self-center text-gov-blue" />
              <input
                id="portal-search"
                type="search"
                placeholder={T(
                  'Search a service, an agent, or a statutory question',
                  'सेवा, एजेंट या क़ानूनी प्रश्न खोजें'
                )}
                className="min-h-[44px] w-full border-0 px-3 text-sm text-gov-ink placeholder:text-gov-mute focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-gov-blue"
              />
            </div>
            <button
              type="submit"
              className="min-h-[44px] shrink-0 bg-gov-blue px-8 text-sm font-semibold text-white hover:bg-gov-blueDk focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gov-saffron"
            >
              {T('Search', 'खोजें')}
            </button>
          </form>
        </section>

        {/* ── Intro ─────────────────────────────────────────────────── */}
        <section
          id="about"
          aria-labelledby="about-heading"
          className="scroll-mt-16 border-t border-gov-rule py-8"
        >
          <h2
            id="about-heading"
            className="border-l-4 border-gov-saffron pl-3 text-xl font-bold text-gov-ink sm:text-2xl"
          >
            {T('About this portal', 'इस पोर्टल के बारे में')}
          </h2>
          <div className="mt-4 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <div className="space-y-4 text-[14px] leading-7 text-gov-ink/90">
              <p>
                {T(
                  'IP-SAKTI Sahayak is decision-support software for Ayurveda intellectual property research. It helps a researcher decide whether an invention is worth pursuing, what prior art already exists, whether a formulation is likely to fall foul of Section 3(p), and which regulatory pathway applies in each target market.',
                  'IP-SAKTI सहायक आयुर्वेद बौद्धिक संपदा अनुसंधान हेतु निर्णय-सहायता सॉफ़्टवेयर है। यह शोधकर्ता को यह निर्णय लेने में सहायता करता है कि आविष्कार पर आगे बढ़ना उचित है या नहीं, क्या पूर्व-आधार मौजूद है, तथा लक्ष्य बाज़ार में कौन-सा विनियामक मार्ग लागू होता है।'
                )}
              </p>
              <p>
                {T(
                  'The reasoning is deterministic. Published rules decide the outcome and retrieval supplies the evidence; a language model is used only to explain that outcome in plain language. Where the corpus has no answer, the system reports the gap rather than guessing.',
                  'तर्क निर्धारित है। प्रकाशित नियम परिणाम तय करते हैं और पुनर्प्राप्ति साक्ष्य देती है; भाषा मॉडल केवल उसी परिणाम को सरल भाषा में समझाने हेतु प्रयुक्त होता है। जहाँ संग्रह में उत्तर नहीं है, वहाँ प्रणाली अनुमान लगाने के बजाय अंतराल की सूचना देती है।'
                )}
              </p>
            </div>
            <dl className="grid grid-cols-2 gap-px border border-gov-rule bg-gov-rule">
              {STATS.map((s) => (
                <div key={s.value} className="bg-white p-4">
                  <dt className="sr-only">{T(s.en, s.hi)}</dt>
                  <dd>
                    <span className="block text-3xl font-bold leading-none text-gov-blue">
                      {s.value}
                    </span>
                    <span className="mt-2 block text-[11px] leading-snug text-gov-mute">
                      {T(s.en, s.hi)}
                    </span>
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* ── Services ─────────────────────────────────────────────── */}
        <section
          id="services"
          aria-labelledby="services-heading"
          className="scroll-mt-16 border-t border-gov-rule py-8"
        >
          <h2
            id="services-heading"
            className="border-l-4 border-gov-saffron pl-3 text-xl font-bold text-gov-ink sm:text-2xl"
          >
            {T('Services', 'सेवाएँ')}
          </h2>
          <p className="mt-2 max-w-3xl text-[13px] leading-6 text-gov-mute">
            {T(
              'Select a service to open its agent. Every result is reproducible from the sources listed at the foot of this page.',
              'सेवा चुनें और संबंधित एजेंट खोलें। प्रत्येक परिणाम इस पृष्ठ के अंत में दिए स्रोतों से पुनःप्राप्य है।'
            )}
          </p>

          <ul className="mt-6 grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3">
            {SERVICES.map((s) => (
              <li key={s.title} className="flex flex-col items-center text-center">
                <a
                  href={s.href}
                  className="group flex w-full flex-col items-center rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-gov-blue"
                >
                  <span className="flex h-24 w-24 items-center justify-center rounded-full border-2 border-gov-blue bg-white text-gov-blue transition-colors group-hover:bg-gov-blue group-hover:text-white">
                    <s.icon aria-hidden="true" className="h-10 w-10" />
                  </span>
                  <span className="mt-3 text-[13px] font-semibold leading-snug text-gov-link underline-offset-2 group-hover:underline">
                    {T(s.title, s.titleHi)}
                  </span>
                </a>
                <p className="mt-2 max-w-[16rem] text-[11px] leading-5 text-gov-mute">
                  {T(s.desc, s.deschi)}
                </p>
              </li>
            ))}
          </ul>
        </section>

        {/* ── Modules ──────────────────────────────────────────────── */}
        <section aria-labelledby="modules-heading" className="border-t border-gov-rule py-8">
          <h2
            id="modules-heading"
            className="border-l-4 border-gov-saffron pl-3 text-xl font-bold text-gov-ink sm:text-2xl"
          >
            {T('Platform modules', 'प्लेटफ़ॉर्म मॉड्यूल')}
          </h2>
          <div className="mt-6 grid gap-5 md:grid-cols-2">
            {MODULES.map((m) => (
              <article key={m.title} className="border border-gov-rule bg-white p-5">
                <div className="flex items-start gap-3">
                  <m.icon aria-hidden="true" className="mt-0.5 h-6 w-6 shrink-0 text-gov-blue" />
                  <div>
                    <h3 className="text-[15px] font-bold text-gov-ink">
                      {T(m.title, m.titleHi)}
                    </h3>
                    <p className="mt-1.5 text-[13px] leading-6 text-gov-mute">
                      {T(m.desc, m.deschi)}
                    </p>
                  </div>
                </div>
                <ul className="mt-4 flex flex-wrap gap-2">
                  {m.points.map((p, i) => (
                    <li
                      key={p}
                      className="border border-gov-rule bg-gov-wash px-2.5 py-1 text-[11px] text-gov-ink"
                    >
                      {lang === 'hi' ? m.pointshi[i] : p}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>

        {/* ── How it works ─────────────────────────────────────────── */}
        <section
          id="how"
          aria-labelledby="how-heading"
          className="scroll-mt-16 border-t border-gov-rule py-8"
        >
          <h2
            id="how-heading"
            className="border-l-4 border-gov-saffron pl-3 text-xl font-bold text-gov-ink sm:text-2xl"
          >
            {T('How it works', 'यह कैसे काम करता है')}
          </h2>
          <ol className="mt-6 grid gap-px border border-gov-rule bg-gov-rule sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                icon: FileText,
                step: T('Step 1', 'चरण 1'),
                title: T('Submit the invention', 'आविष्कार प्रस्तुत करें'),
                body: T(
                  'A problem statement, a formulation, or an uploaded document.',
                  'समस्या कथन, संयोजन, अथवा अपलोडित दस्तावेज़।'
                ),
              },
              {
                icon: Search,
                step: T('Step 2', 'चरण 2'),
                title: T('Retrieve evidence', 'साक्ष्य पुनर्प्राप्त करें'),
                body: T(
                  'Matching statutory passages, monographs and patent records are scored.',
                  'मिलान वाले क़ानूनी अंश, मोनोग्राफ़ एवं पेटेंट अभिलेख अंकित होते हैं।'
                ),
              },
              {
                icon: CircleDot,
                step: T('Step 3', 'चरण 3'),
                title: T('Apply reviewed rules', 'समीक्षित नियम लागू करें'),
                body: T(
                  'Deterministic rule packs decide novelty, freedom to operate and risk.',
                  'निर्धारित नियम-पैक नवीनता, FTO एवं जोखिम तय करते हैं।'
                ),
              },
              {
                icon: BadgeCheck,
                step: T('Step 4', 'चरण 4'),
                title: T('Issue the record', 'रिकॉर्ड जारी करें'),
                body: T(
                  'A cited, versioned result that can be exported and re-verified.',
                  'उद्धृत, संस्करणित परिणाम जो निर्यात एवं पुनःसत्यापन योग्य है।'
                ),
              },
            ].map((s) => (
              <li key={s.step} className="bg-white p-5">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-gov-saffron">
                  <s.icon aria-hidden="true" className="h-4 w-4" />
                  {s.step}
                </div>
                <h3 className="mt-2 text-[14px] font-bold text-gov-ink">{s.title}</h3>
                <p className="mt-1.5 text-[12px] leading-5 text-gov-mute">{s.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* ── Notices ──────────────────────────────────────────────── */}
        <section
          id="notices"
          aria-labelledby="notices-heading"
          className="scroll-mt-16 border-t border-gov-rule py-8"
        >
          <h2
            id="notices-heading"
            className="border-l-4 border-gov-saffron pl-3 text-xl font-bold text-gov-ink sm:text-2xl"
          >
            {T('What’s new', 'नया क्या है')}
          </h2>
          <ul className="mt-5 divide-y divide-gov-rule border-y border-gov-rule">
            {NOTICES.map((n) => (
              <li key={n.date} className="flex flex-col gap-1 py-3 sm:flex-row sm:gap-6">
                <time
                  dateTime={n.date}
                  className="shrink-0 font-mono text-[12px] text-gov-mute sm:w-32"
                >
                  {new Date(n.date).toLocaleDateString('en-IN', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                  })}
                </time>
                <p className="text-[13px] leading-6 text-gov-ink/90">{T(n.en, n.hi)}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* ── Sources ──────────────────────────────────────────────── */}
        <section
          id="sources"
          aria-labelledby="sources-heading"
          className="scroll-mt-16 border-t border-gov-rule py-8"
        >
          <h2
            id="sources-heading"
            className="border-l-4 border-gov-saffron pl-3 text-xl font-bold text-gov-ink sm:text-2xl"
          >
            {T('Knowledge sources', 'ज्ञान स्रोत')}
          </h2>
          <p className="mt-2 max-w-3xl text-[13px] leading-6 text-gov-mute">
            {T(
              'Retrieval is restricted to these publishers. A claim that cannot be traced to one of them is not made.',
              'पुनर्प्राप्ति इन्हीं प्रकाशकों तक सीमित है। जिस दावे का इनमें से किसी से स्रोत नहीं, वह नहीं किया जाता।'
            )}
          </p>

          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[34rem] border-collapse text-left text-[13px]">
              <caption className="sr-only">
                {T('Knowledge sources and publishers', 'ज्ञान स्रोत और प्रकाशक')}
              </caption>
              <thead>
                <tr className="bg-gov-wash">
                  <th scope="col" className="border border-gov-rule px-4 py-2.5 font-semibold">
                    {T('Source', 'स्रोत')}
                  </th>
                  <th scope="col" className="border border-gov-rule px-4 py-2.5 font-semibold">
                    {T('Publisher', 'प्रकाशक')}
                  </th>
                  <th scope="col" className="border border-gov-rule px-4 py-2.5 font-semibold">
                    {T('Link', 'लिंक')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {SOURCES.map((s) => (
                  <tr key={s.name} className="hover:bg-gov-wash">
                    <th scope="row" className="border border-gov-rule px-4 py-2.5 font-medium">
                      <span className="flex items-center gap-2">
                        {s.name === 'CSIR-TKDL' ? (
                          <Database aria-hidden="true" className="h-4 w-4 text-gov-blue" />
                        ) : s.name === 'IP India' || s.name === 'Ministry of AYUSH' ? (
                          <Landmark aria-hidden="true" className="h-4 w-4 text-gov-blue" />
                        ) : (
                          <Building2 aria-hidden="true" className="h-4 w-4 text-gov-blue" />
                        )}
                        {s.name}
                      </span>
                    </th>
                    <td className="border border-gov-rule px-4 py-2.5 text-gov-mute">
                      {s.publisher}
                    </td>
                    <td className="border border-gov-rule px-4 py-2.5">
                      <a
                        href={s.href}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-gov-link underline underline-offset-2 hover:text-gov-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gov-saffron"
                      >
                        {T('Open', 'खोलें')}
                        <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
                        <span className="sr-only">
                          {s.name} ({T('opens in a new tab', 'नए टैब में खुलता है')})
                        </span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <GovFooter onLogin={goLogin} />
    </div>
  );
}
