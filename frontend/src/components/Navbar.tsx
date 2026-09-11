'use client';

import React, { useState } from 'react';
import { SUPPORTED_LANGUAGES, t } from '../lib/i18n';
import { useLang } from '../lib/LangContext';
import { ShieldCheck, Globe, Wifi, WifiOff, Accessibility as AccessibilityIcon, Leaf } from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher';
import AccessibilityPanel from './AccessibilityPanel';

interface NavbarProps {
  isOnline: boolean;
  offlineDraftCount: number;
}

export default function Navbar({ isOnline, offlineDraftCount }: NavbarProps) {
  const { lang } = useLang();
  const [langOpen, setLangOpen] = useState(false);
  const [accessOpen, setAccessOpen] = useState(false);

  const langLabel = SUPPORTED_LANGUAGES.find((l) => l.code === lang)?.nativeName || 'English';

  return (
    <>
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-xl border-b border-emerald-200 px-4 lg:px-8 py-3.5 flex items-center justify-between shadow-sm">
        {/* Brand & Tagline */}
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-emerald-700 flex items-center justify-center shadow-md shadow-emerald-900/20">
            <Leaf className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 font-display">
                {t('app_title', lang)}
              </h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-700 border border-emerald-300">
                v1.0 Production
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block max-w-xl truncate">
              {t('tagline', lang)}
            </p>
          </div>
        </div>

        {/* Controls: DPDP, status, accessibility, language, voice */}
        <div className="flex items-center space-x-2.5">
          <div className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-700">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>DPDP Act 2023</span>
          </div>

          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs">
            {isOnline ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700">{t('online', lang)}</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-amber-600" />
                <span className="text-amber-700 hidden sm:inline">{t('offline', lang)} ({offlineDraftCount})</span>
              </>
            )}
          </div>

          <button
            onClick={() => setAccessOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-emerald-200 text-slate-600 hover:bg-emerald-50 transition"
            aria-label={t('accessibility', lang)}
            title={t('accessibility', lang)}
          >
            <AccessibilityIcon className="w-4 h-4" />
            <span className="hidden lg:inline text-xs font-medium">{t('accessibility', lang)}</span>
          </button>

          <button
            onClick={() => setLangOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-emerald-200 text-slate-700 hover:bg-emerald-50 transition"
            aria-label="Select Language"
            title={t('app_title', lang)}
          >
            <Globe className="w-4 h-4 text-emerald-600" />
            <span className="text-sm font-medium">{langLabel}</span>
          </button>
        </div>
      </header>

      {langOpen && <LanguageSwitcher isOpen={langOpen} onClose={() => setLangOpen(false)} />}
      {accessOpen && <AccessibilityPanel isOpen={accessOpen} onClose={() => setAccessOpen(false)} />}
    </>
  );
}