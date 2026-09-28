'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { SUPPORTED_LANGUAGES, t } from '../lib/i18n';
import { useLang } from '../lib/LangContext';
import { ShieldCheck, Globe, Wifi, WifiOff, Accessibility as AccessibilityIcon, Leaf, FlaskConical } from 'lucide-react';
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
      <header className="sticky top-0 z-50 bg-white border-b border-gov-rule px-4 lg:px-8 py-3 flex items-center justify-between">
        {/* Brand & Tagline */}
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-md bg-gov-blue flex items-center justify-center">
            <Leaf className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-gov-navy font-display">
                {t('app_title', lang)}
              </h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-gov-wash text-gov-blue border border-gov-rule">
                v1.0 Production
              </span>
            </div>
            <p className="text-xs text-gov-mute hidden sm:block max-w-xl truncate">
              {t('tagline', lang)}
            </p>
          </div>
        </div>

        {/* Controls: DPDP, status, accessibility, language, voice */}
        <div className="flex items-center space-x-2.5">
          <div className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-gov-wash border border-gov-rule text-xs text-gov-blue">
            <ShieldCheck className="w-3.5 h-3.5 text-gov-green" />
            <span>DPDP Act 2023</span>
          </div>

          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-gov-wash border border-gov-rule text-xs">
            {isOnline ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-gov-green" />
                <span className="text-gov-green">{t('online', lang)}</span>
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
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-gray-300 text-slate-600 hover:bg-gov-wash transition"
            aria-label={t('accessibility', lang)}
            title={t('accessibility', lang)}
          >
            <AccessibilityIcon className="w-4 h-4" />
            <span className="hidden lg:inline text-xs font-medium">{t('accessibility', lang)}</span>
          </button>

          <button
            onClick={() => setLangOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-gray-300 text-slate-700 hover:bg-gov-wash transition"
            aria-label="Select Language"
            title={t('app_title', lang)}
          >
            <Globe className="w-4 h-4 text-gov-blue" />
            <span className="text-sm font-medium">{langLabel}</span>
          </button>

          <span className="hidden md:flex">
            <Link
              href="/innovation-lab"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gov-blue text-white border border-gov-blueDk hover:bg-gov-navy transition text-xs font-medium"
            >
              <FlaskConical className="w-4 h-4" />
              Innovation AI Lab
            </Link>
          </span>
        </div>
      </header>

      {langOpen && <LanguageSwitcher isOpen={langOpen} onClose={() => setLangOpen(false)} />}
      {accessOpen && <AccessibilityPanel isOpen={accessOpen} onClose={() => setAccessOpen(false)} />}
    </>
  );
}