'use client';
import React, { useEffect, useState } from 'react';
import { Leaf, X, ScrollText, BookOpen } from 'lucide-react';
import { useLang } from '../../lib/LangContext';
import { t } from '../../lib/i18n';

interface Herb {
  key: string;
  en: string;
  latin: string;
  color: string;
  descKey: string;
  noteKey: string;
  factKeys: string[];
}

const HERBS: Herb[] = [
  {
    key: 'tulsi',
    en: 'Tulsi',
    latin: 'Ocimum sanctum',
    color: 'from-emerald-600 to-green-500',
    descKey: 'sh_tulsi_desc',
    noteKey: 'sh_tulsi_note',
    factKeys: ['sh_tulsi_f1', 'sh_tulsi_f2', 'sh_tulsi_f3'],
  },
  {
    key: 'ashwagandha',
    en: 'Ashwagandha',
    latin: 'Withania somnifera',
    color: 'from-amber-600 to-yellow-500',
    descKey: 'sh_ashwagandha_desc',
    noteKey: 'sh_ashwagandha_note',
    factKeys: ['sh_ashwagandha_f1', 'sh_ashwagandha_f2', 'sh_ashwagandha_f3'],
  },
  {
    key: 'brahmi',
    en: 'Brahmi',
    latin: 'Bacopa monnieri',
    color: 'from-teal-600 to-cyan-500',
    descKey: 'sh_brahmi_desc',
    noteKey: 'sh_brahmi_note',
    factKeys: ['sh_brahmi_f1', 'sh_brahmi_f2', 'sh_brahmi_f3'],
  },
  {
    key: 'haldi',
    en: 'Haldi · Turmeric',
    latin: 'Curcuma longa',
    color: 'from-orange-600 to-amber-500',
    descKey: 'sh_haldi_desc',
    noteKey: 'sh_haldi_note',
    factKeys: ['sh_haldi_f1', 'sh_haldi_f2', 'sh_haldi_f3'],
  },
  {
    key: 'amla',
    en: 'Amla',
    latin: 'Phyllanthus emblica',
    color: 'from-lime-600 to-green-500',
    descKey: 'sh_amla_desc',
    noteKey: 'sh_amla_note',
    factKeys: ['sh_amla_f1', 'sh_amla_f2', 'sh_amla_f3'],
  },
  {
    key: 'neem',
    en: 'Neem',
    latin: 'Azadirachta indica',
    color: 'from-green-700 to-emerald-500',
    descKey: 'sh_neem_desc',
    noteKey: 'sh_neem_note',
    factKeys: ['sh_neem_f1', 'sh_neem_f2', 'sh_neem_f3'],
  },
  {
    key: 'shatavari',
    en: 'Shatavari',
    latin: 'Asparagus racemosus',
    color: 'from-pink-600 to-rose-500',
    descKey: 'sh_shatavari_desc',
    noteKey: 'sh_shatavari_note',
    factKeys: ['sh_shatavari_f1', 'sh_shatavari_f2', 'sh_shatavari_f3'],
  },
  {
    key: 'guduchi',
    en: 'Guduchi · Giloy',
    latin: 'Tinospora cordifolia',
    color: 'from-violet-600 to-purple-500',
    descKey: 'sh_guduchi_desc',
    noteKey: 'sh_guduchi_note',
    factKeys: ['sh_guduchi_f1', 'sh_guduchi_f2', 'sh_guduchi_f3'],
  },
];

export default function ScrollingHerbs() {
  const { lang } = useLang();
  const [index, setIndex] = useState(-1);
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [hint, setHint] = useState(true);

  useEffect(() => {
    let raf = 0;
    const update = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const doc = document.documentElement;
        const max = doc.scrollHeight - window.innerHeight;
        const p = max > 0 ? window.scrollY / max : 0;
        const idx = Math.min(HERBS.length - 1, Math.max(0, Math.floor(p * HERBS.length)));
        setIndex(idx);
      });
    };
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    const t = setTimeout(() => setHint(false), 7000);
    return () => {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
      cancelAnimationFrame(raf);
      clearTimeout(t);
    };
  }, []);

  const herb = index >= 0 ? HERBS[index] : null;
  const isLeft = index % 2 === 0;
  const open = herb ? HERBS.find((h) => h.key === openKey) || null : null;

  return (
    <>
      {/* Scroll-triggered herb layer (one at a time, alternating sides) */}
      <div className="pointer-events-none fixed inset-0 z-30" aria-hidden={open ? true : false}>
        {herb && (
          <button
            type="button"
            onClick={() => setOpenKey(openKey === herb.key ? null : herb.key)}
            className={`pointer-events-auto group absolute top-[24%] flex items-center gap-2 focus:outline-none transition-all duration-[750ms] ease-out will-change-transform ${
              isLeft ? 'left-2 sm:left-4 lg:left-8' : 'right-2 sm:right-4 lg:right-8'
            } ${openKey === herb.key ? 'scale-95 opacity-90' : 'opacity-100 hover:scale-105'}`}
          >
            <span className={`rounded-full bg-gradient-to-br ${herb.color} shadow-lg shadow-black/20 ring-2 ring-white/80 flex items-center justify-center animate-float w-12 h-12 sm:w-14 sm:h-14`}>
              <Leaf className="text-white w-6 h-6 sm:w-7 sm:h-7 drop-shadow" />
            </span>
            <span className="bg-white/95 backdrop-blur border border-slate-200 rounded-full px-3 py-1 text-[11px] font-bold text-slate-800 shadow-md shadow-slate-900/10 hidden sm:inline-flex">
              {herb.en}
              <span className="text-emerald-600 ml-1.5">· {herb.latin.split(' ')[0]}</span>
            </span>
          </button>
        )}

        {/* Info panel for the active herb (same side as the herb) */}
        <div
          className={`pointer-events-auto fixed top-[30%] z-40 w-[290px] max-w-[82vw] transition-all duration-[750ms] ease-out ${
            isLeft ? 'left-2 sm:left-4 lg:left-10' : 'right-2 sm:right-4 lg:right-10'
          }`}
          style={{
            opacity: open ? 1 : 0,
            transform: open ? 'translateY(0) scale(1)' : isLeft ? 'translateY(24px) scale(0.96)' : 'translateY(24px) scale(0.96)',
            pointerEvents: open ? 'auto' : 'none',
          }}
        >
          {open && (
            <div className="rounded-2xl bg-white/95 backdrop-blur-xl border border-slate-200 shadow-2xl shadow-slate-900/20 overflow-hidden">
              <div className={`bg-gradient-to-br ${open.color} px-4 py-3 flex items-start justify-between gap-2`}>
                <div>
                  <div className="text-white font-black text-base leading-tight">{open.en}</div>
                  <div className="text-white/85 text-[11px] italic font-medium">{open.latin}</div>
                </div>
                <button type="button" onClick={() => setOpenKey(null)} className="text-white/85 hover:text-white bg-white/15 hover:bg-white/25 rounded-full p-1.5 transition" aria-label={t('sh_close', lang)}>
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="p-4 space-y-3">
                <p className="text-xs text-slate-600 leading-relaxed">{t(open.descKey, lang)}</p>
                <div className="flex flex-wrap gap-1.5">
                  {open.factKeys.map((f, i) => (
                    <span key={i} className="px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-semibold text-emerald-700">
                      {t(f, lang)}
                    </span>
                  ))}
                </div>
                <div className="flex items-start gap-2 rounded-xl bg-violet-50 border border-violet-200 px-3 py-2.5">
                  <BookOpen className="w-3.5 h-3.5 text-violet-600 mt-0.5 flex-shrink-0" />
                  <p className="text-[10.5px] text-violet-700 leading-snug">{t(open.noteKey, lang)}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* First-visit hint */}
      {hint && !open && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 pointer-events-none animate-fade-in-up">
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-white/95 backdrop-blur border border-emerald-200 shadow-lg shadow-emerald-900/10 text-[11px] font-semibold text-emerald-800">
            <ScrollText className="w-3.5 h-3.5" />
            {t('sh_scroll_hint', lang)}
          </div>
        </div>
      )}
    </>
  );
}