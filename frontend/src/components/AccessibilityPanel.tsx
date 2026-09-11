'use client';
import React from 'react';
import { useAccessibility } from '../lib/AccessibilityContext';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';
import { Accessibility, X, Type, Contrast, MousePointerClick, Volume2, Minus, Plus } from 'lucide-react';

interface AccessibilityPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onChange}
      disabled={disabled}
      aria-checked={checked}
      role="switch"
      className={`w-11 h-6 rounded-full relative transition flex-shrink-0 disabled:opacity-40 ${checked ? 'bg-blue-500' : 'bg-emerald-200'}`}
    >
      <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${checked ? 'right-0.5' : 'left-0.5'}`} />
    </button>
  );
}

export default function AccessibilityPanel({ isOpen, onClose }: AccessibilityPanelProps) {
  const { lang } = useLang();
  const { highContrast, toggleHighContrast, reduceMotion, toggleReduceMotion, screenReader, toggleScreenReader, textScale, setTextScale } = useAccessibility();

  if (!isOpen) return null;

  const options = [
    { label: t('high_contrast', lang), icon: Contrast, checked: highContrast, onChange: toggleHighContrast },
    { label: t('reduce_motion', lang), icon: MousePointerClick, checked: reduceMotion, onChange: toggleReduceMotion },
    { label: t('screen_reader', lang), icon: Volume2, checked: screenReader, onChange: toggleScreenReader },
  ];

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-white border border-emerald-200 rounded-3xl p-6 shadow-2xl animate-scaleIn">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Accessibility className="w-5 h-5 text-emerald-600" />
            <h2 className="text-lg font-bold text-slate-900">{t('accessibility', lang)}</h2>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-900">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Text Size Card */}
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <Type className="w-4 h-4 text-blue-600" />
              {t('large_text', lang)}
            </div>
            <div className="flex items-center gap-3">
              <button onClick={() => setTextScale(Math.max(1, Math.round((textScale - 0.15) * 100) / 100))} className="w-9 h-9 rounded-xl bg-emerald-100 hover:bg-emerald-200 flex items-center justify-center text-slate-900">
                <Minus className="w-4 h-4" />
              </button>
              <div className="flex-1 h-2 rounded-full bg-emerald-100 relative">
                <div className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-blue-500 to-violet-500" style={{ width: `${((textScale - 1) / 0.6) * 100}%` }} />
              </div>
              <button onClick={() => setTextScale(Math.min(1.6, Math.round((textScale + 0.15) * 100) / 100))} className="w-9 h-9 rounded-xl bg-emerald-100 hover:bg-emerald-200 flex items-center justify-center text-slate-900">
                <Plus className="w-4 h-4" />
              </button>
              <span className="text-xs text-slate-500 w-10 text-right">{Math.round(textScale * 100)}%</span>
            </div>
          </div>

          {/* Toggle Options Card */}
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 space-y-3">
            {options.map((o) => {
              const Icon = o.icon;
              return (
                <div key={o.label} className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-3">
                    <span className="w-9 h-9 rounded-xl bg-emerald-100 flex items-center justify-center">
                      <Icon className="w-4 h-4 text-slate-600" />
                    </span>
                    <span className="text-sm text-slate-700">{o.label}</span>
                  </div>
                  <Toggle checked={o.checked} onChange={o.onChange} disabled={o.label === t('screen_reader', lang) && textScale < 1.15} />
                </div>
              );
            })}
          </div>

          <p className="text-[10px] text-slate-500 text-center">
            IP-SAKTI · WCAG-ready interface
          </p>
        </div>
      </div>
    </div>
  );
}