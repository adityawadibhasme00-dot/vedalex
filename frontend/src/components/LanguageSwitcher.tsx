'use client';
import React from 'react';
import { useLang } from '../lib/LangContext';
import { t, SUPPORTED_LANGUAGES } from '../lib/i18n';
import { Globe, X } from 'lucide-react';

interface LanguageSwitcherProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LanguageSwitcher({ isOpen, onClose }: LanguageSwitcherProps) {
  const { lang, setLang } = useLang();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-[#111827]/95 border border-white/10 rounded-3xl p-6 shadow-2xl animate-scaleIn">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-bold text-white">{t('app_title', lang)}</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-4">
          <p className="text-xs text-slate-500 mb-4 font-semibold uppercase tracking-wider">Select Language / भाषा चुनें</p>
          <div className="grid grid-cols-2 gap-2">
            {SUPPORTED_LANGUAGES.map((l) => (
              <button
                key={l.code}
                onClick={() => {
                  setLang(l.code as any);
                  onClose();
                }}
                className={`p-3 rounded-xl text-left transition-all border ${
                  lang === l.code
                    ? 'bg-blue-500/20 border-blue-500/40 text-white shadow-lg shadow-blue-900/20'
                    : 'bg-white/[0.02] border-white/5 text-slate-300 hover:bg-white/[0.05]'
                }`}
              >
                <div className="font-semibold text-sm">{l.nativeName}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">{l.scriptLabel}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
