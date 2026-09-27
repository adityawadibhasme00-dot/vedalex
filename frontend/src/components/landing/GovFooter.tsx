'use client';

import React from 'react';
import { useLang } from '../../lib/LangContext';
import { ChakraMark } from './GovHeader';

const LINK_GROUPS = [
  {
    title: 'Statutory sources',
    titleHi: 'क़ानूनी स्रोत',
    links: [
      { label: 'CSIR-TKDL', href: 'https://tkdl.res.in/' },
      { label: 'IP India', href: 'https://ipindia.gov.in/' },
      { label: 'WIPO PATENTSCOPE', href: 'https://patentscope.wipo.int/' },
      { label: 'India Code', href: 'https://www.indiacode.nic.in/' },
      { label: 'Ministry of AYUSH', href: 'https://ayush.gov.in/' },
      { label: 'NCBI PubMed', href: 'https://pubmed.ncbi.nlm.nih.gov/' },
    ],
  },
  {
    title: 'Policy',
    titleHi: 'नीति',
    links: [
      { label: 'Privacy policy', href: '/privacy' },
      { label: 'Terms of use', href: '/terms' },
      { label: 'Accessibility statement', href: '/accessibility' },
      { label: 'Grievance redressal', href: '/grievance' },
    ],
  },
];

const COMPLIANCE = [
  {
    en: 'Built to WCAG 2.1 AA and GIGW 3.0: skip navigation, keyboard operability, and user-settable text size.',
    hi: 'WCAG 2.1 AA तथा GIGW 3.0 के अनुरूप: स्किप नेविगेशन, कीबोर्ड संचालन और उपयोगकर्ता-निर्धारित अक्षर आकार।',
  },
  {
    en: 'Decision support only. Outputs are grounded in cited sources and are not a substitute for a qualified patent agent.',
    hi: 'केवल निर्णय सहायता। परिणाम उद्धृत स्रोतों पर आधारित हैं, पात्र पेटेंट एजेंट का विकल्प नहीं।',
  },
  {
    en: 'DPDP Act 2023 aligned: consent logging enabled, data residency ap-south-1.',
    hi: 'DPDP अधिनियम 2023 अनुरूप: सहमति लॉगिंग सक्षम, डेटा निवास ap-south-1।',
  },
];

export default function GovFooter({ onLogin }: { onLogin: () => void }) {
  const { lang } = useLang();
  const T = (en: string, hi: string) => (lang === 'hi' ? hi : en);

  return (
    <footer className="mt-12 border-t-4 border-gov-saffron bg-gov-navy text-white/90">
      <div className="mx-auto grid max-w-[1200px] grid-cols-1 gap-8 px-4 py-10 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <div className="flex items-center gap-3">
            <ChakraMark className="h-9 w-9 shrink-0 text-white" />
            <div>
              <p className="text-sm font-bold text-white">{T('IP-SAKTI Sahayak', 'IP-SAKTI सहायक')}</p>
              <p className="text-[11px] text-white/60">
                {T('Ayurveda IP decision support', 'आयुर्वेद IP निर्णय सहायता')}
              </p>
            </div>
          </div>
          <p className="mt-4 text-[12px] leading-relaxed text-white/70">
            {T(
              'A research portal for Ayurveda intellectual property research. It is not a Government of India website and does not represent one.',
              'आयुर्वेद बौद्धिक संपदा अनुसंधान हेतु एक अनुसंधान पोर्टल। यह भारत सरकार की वेबसाइट नहीं है।'
            )}
          </p>
          <button
            type="button"
            onClick={onLogin}
            className="mt-4 min-h-[44px] border-2 border-gov-saffron bg-transparent px-5 text-[13px] font-semibold text-gov-saffron hover:bg-gov-saffron hover:text-gov-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            {T('Secure login', 'सुरक्षित लॉगिन')}
          </button>
        </div>

        {LINK_GROUPS.map((g) => (
          <nav key={g.title} aria-label={T(g.title, g.titleHi)}>
            <h2 className="mb-3 border-b border-white/15 pb-2 text-[12px] font-bold uppercase tracking-wider text-white">
              {T(g.title, g.titleHi)}
            </h2>
            <ul className="space-y-2 text-[12px]">
              {g.links.map((l) => (
                <li key={l.label}>
                  <a
                    href={l.href}
                    {...(l.href.startsWith('http')
                      ? { target: '_blank', rel: 'noreferrer' }
                      : {})}
                    className="text-white/75 underline-offset-2 hover:text-gov-saffron hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gov-saffron"
                  >
                    {l.label}
                    {l.href.startsWith('http') && (
                      <span className="sr-only"> (opens in a new tab)</span>
                    )}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        ))}

        <section aria-label={T('Compliance notes', 'अनुपालन टिप्पणियाँ')}>
          <h2 className="mb-3 border-b border-white/15 pb-2 text-[12px] font-bold uppercase tracking-wider text-white">
            {T('Compliance', 'अनुपालन')}
          </h2>
          <ul className="space-y-3 text-[12px] leading-relaxed text-white/70">
            {COMPLIANCE.map((c) => (
              <li key={c.en} className="flex gap-2">
                <span aria-hidden="true" className="mt-1.5 h-1.5 w-1.5 shrink-0 bg-gov-saffron" />
                <span>{T(c.en, c.hi)}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="border-t border-white/15 bg-black/25">
        <div className="mx-auto flex max-w-[1200px] flex-col gap-1 px-4 py-4 text-[11px] text-white/60 sm:flex-row sm:items-center sm:justify-between">
          <p>
            {T(
              'Content is provided for informational guidance. Consult a qualified patent agent before filing.',
              'सामग्री सूचनात्मक मार्गदर्शन हेतु प्रदत्त है। फाइलिंग से पूर्व पात्र पेटेंट एजेंट से परामर्श करें।'
            )}
          </p>
          <p className="shrink-0">
            {T('Last updated', 'अंतिम अद्यतन')}:{' '}
            <time dateTime="2026-09-27">27 Sep 2026</time>
          </p>
        </div>
      </div>
    </footer>
  );
}
