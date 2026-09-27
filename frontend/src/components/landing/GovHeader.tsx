'use client';

import React from 'react';
import { useLang, type LangCode } from '../../lib/LangContext';

/** Ashoka-chakra style mark. Drawn, not the national emblem, so the portal
 *  never passes itself off as a Government of India site. */
export function ChakraMark({ className = 'w-10 h-10' }: { className?: string }) {
  const spokes = Array.from({ length: 24 }, (_, i) => i);
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      role="img"
      aria-label="Ashoka chakra"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="50" cy="50" r="48" stroke="currentColor" strokeWidth="4" />
      <circle cx="50" cy="50" r="6" fill="currentColor" />
      {spokes.map((i) => {
        const a = (i * 15 * Math.PI) / 180;
        return (
          <line
            key={i}
            x1={50 + 8 * Math.cos(a)}
            y1={50 + 8 * Math.sin(a)}
            x2={50 + 44 * Math.cos(a)}
            y2={50 + 44 * Math.sin(a)}
            stroke="currentColor"
            strokeWidth="2.5"
          />
        );
      })}
    </svg>
  );
}

export const GOV_LANGUAGES: { code: LangCode; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'mr', label: 'मराठी' },
  { code: 'bn', label: 'বাংলা' },
  { code: 'gu', label: 'ગુજરાતી' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
  { code: 'ml', label: 'മലയാളം' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'sa', label: 'संस्कृतम्' },
];

const NAV = [
  { id: 'home', label: 'Home', hi: 'होम' },
  { id: 'about', label: 'About', hi: 'परिचय' },
  { id: 'services', label: 'Services', hi: 'सेवाएँ' },
  { id: 'how', label: 'How It Works', hi: 'कार्यप्रणाली' },
  { id: 'sources', label: 'Sources', hi: 'स्रोत' },
  { id: 'notices', label: 'Notices', hi: 'सूचनाएँ' },
];

function useText() {
  const { lang } = useLang();
  return (en: string, hi: string) => (lang === 'hi' ? hi : en);
}

export function GovUtilityBar() {
  const { lang, setLang } = useLang();
  const T = useText();

  // GIGW requires a user-settable text size. We drive it on the root element so
  // every rem-based size on the page scales together.
  const setFont = (delta: number) => {
    const root = document.documentElement;
    const cur = parseFloat(root.style.fontSize || '16');
    const next = delta === 0 ? 16 : Math.max(14, Math.min(22, cur + delta));
    root.style.fontSize = `${next}px`;
  };

  return (
    <div className="bg-gov-navy text-white">
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-1.5 text-[11px] leading-5">
        <div className="flex items-center gap-2">
          <span className="font-semibold tracking-wide">
            {T('IP-SAKTI Sahayak', 'IP-SAKTI सहायक')}
          </span>
          <span aria-hidden="true" className="text-white/40">|</span>
          <span className="text-white/75">
            {T(
              'Ayurveda IP & Prior-Art Decision Portal',
              'आयुर्वेद IP एवं पूर्व-आधार निर्णय पोर्टल'
            )}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="#main-content"
            className="underline underline-offset-2 hover:text-gov-saffron focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gov-saffron"
          >
            {T('Skip to main content', 'मुख्य सामग्री पर जाएँ')}
          </a>
          <span aria-hidden="true" className="text-white/30">|</span>
          <span className="text-white/60">{T('Text size', 'अक्षर आकार')}</span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setFont(-1)}
              aria-label={T('Decrease text size', 'अक्षर आकार घटाएँ')}
              className="min-w-[28px] border border-white/40 px-1.5 leading-5 hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-gov-saffron"
            >
              A-
            </button>
            <button
              type="button"
              onClick={() => setFont(0)}
              aria-label={T('Reset text size', 'अक्षर आकार रीसेट करें')}
              className="min-w-[28px] border border-white/40 px-1.5 leading-5 hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-gov-saffron"
            >
              A
            </button>
            <button
              type="button"
              onClick={() => setFont(1)}
              aria-label={T('Increase text size', 'अक्षर आकार बढ़ाएँ')}
              className="min-w-[28px] border border-white/40 px-1.5 leading-5 hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-gov-saffron"
            >
              A+
            </button>
          </div>
          <span aria-hidden="true" className="text-white/30">|</span>
          <label className="flex items-center gap-1.5">
            <span className="sr-only">{T('Select language', 'भाषा चुनें')}</span>
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as LangCode)}
              className="border border-white/40 bg-gov-navy px-1.5 py-0.5 text-[11px] text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-gov-saffron"
            >
              {GOV_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} className="text-black">
                  {l.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
    </div>
  );
}

export function GovMasthead({ onLogin }: { onLogin: () => void }) {
  const T = useText();
  return (
    <div className="border-b border-gov-rule bg-white">
      <div className="mx-auto flex max-w-[1200px] flex-col items-start gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <span className="flex h-16 w-16 shrink-0 items-center justify-center border-2 border-gov-navy text-gov-navy">
            <ChakraMark className="h-11 w-11" />
          </span>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gov-mute">
              {T('Ministry-aligned research initiative', 'मंत्रालय-अनुरूप अनुसंधान परियोजना')}
            </p>
            <h1 className="text-2xl font-bold leading-tight text-gov-ink sm:text-[28px]">
              {T('IP-SAKTI Sahayak', 'IP-SAKTI सहायक')}
            </h1>
            <p className="mt-0.5 text-[13px] leading-snug text-gov-mute">
              {T(
                'AI-assisted Ayurveda intellectual property and prior-art decision support',
                'आयुर्वेद बौद्धिक संपदा एवं पूर्व-आधार हेतु AI-सहायता निर्णय समर्थन'
              )}
            </p>
          </div>
        </div>

        <div className="flex flex-col items-start gap-2 sm:items-end">
          <p className="text-[11px] text-gov-mute">
            {T('Content last reviewed', 'सामग्री अंतिम समीक्षा')}:{' '}
            <time dateTime="2026-09-27">27 September 2026</time>
          </p>
          <button
            type="button"
            onClick={onLogin}
            className="min-h-[44px] border-2 border-gov-blue bg-gov-blue px-6 text-sm font-semibold text-white hover:bg-gov-blueDk focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gov-saffron"
          >
            {T('Login', 'लॉगिन')}
          </button>
        </div>
      </div>
    </div>
  );
}

export function GovNav({
  onLogin,
  active,
}: {
  onLogin: () => void;
  active: string;
}) {
  const T = useText();
  return (
    <nav aria-label={T('Primary', 'प्राथमिक')} className="sticky top-0 z-40 bg-gov-blue shadow-sm">
      <div className="mx-auto flex max-w-[1200px] items-stretch justify-between">
        <ul className="flex min-w-0 flex-1 items-stretch overflow-x-auto">
          {NAV.map((n) => {
            const isActive = active === n.id;
            return (
              <li key={n.id} className="shrink-0">
                <a
                  href={`#${n.id}`}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex min-h-[44px] items-center border-b-4 px-4 text-[13px] font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-white ${
                    isActive
                      ? 'border-gov-saffron bg-gov-blueDk text-white'
                      : 'border-transparent text-white/95 hover:bg-gov-blueDk hover:text-white'
                  }`}
                >
                  {T(n.label, n.hi)}
                </a>
              </li>
            );
          })}
        </ul>
        <button
          type="button"
          onClick={onLogin}
          className="hidden min-h-[44px] shrink-0 items-center border-l border-white/25 bg-gov-blueDk px-5 text-[13px] font-semibold text-white hover:bg-gov-navy focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-gov-saffron md:flex"
        >
          {T('Sign in', 'साइन इन करें')}
        </button>
      </div>
    </nav>
  );
}

export function GovBreadcrumb({ items }: { items: { label: string; href?: string }[] }) {
  const T = useText();
  return (
    <div className="border-b border-gov-rule bg-gov-wash">
      <nav aria-label={T('Breadcrumb', 'ब्रेडक्रंब')} className="mx-auto max-w-[1200px] px-4 py-2">
        <ol className="flex flex-wrap items-center gap-1 text-[12px] text-gov-mute">
          {items.map((it, i) => (
            <li key={it.label} className="flex items-center gap-1">
              {i > 0 && (
                <span aria-hidden="true" className="px-1 text-gov-rule">
                  /
                </span>
              )}
              {it.href ? (
                <a
                  href={it.href}
                  className="text-gov-link underline underline-offset-2 hover:text-gov-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gov-saffron"
                >
                  {it.label}
                </a>
              ) : (
                <span aria-current="page" className="font-medium text-gov-ink">
                  {it.label}
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>
    </div>
  );
}
