'use client';
import React, { useEffect, useRef, useState } from 'react';
import { Leaf, BookOpen, ChevronDown } from 'lucide-react';
import { useLang } from '../../lib/LangContext';
import { t } from '../../lib/i18n';

interface HerbEntry {
  key: string;
  en: string;
  latin: string;
  image: string;
  accent: string;
  accentBg: string;
  accentBorder: string;
  descKey: string;
  useKeys: string[];
  patentNoteKey: string;
}

const HERBS: HerbEntry[] = [
  {
    key: 'tulsi',
    en: 'Tulsi',
    latin: 'Ocimum sanctum',
    image: 'https://images.unsplash.com/photo-1615485500704-8e990f9900f7?w=800&q=80&auto=format',
    accent: 'from-emerald-700 to-green-500',
    accentBg: 'bg-emerald-50',
    accentBorder: 'border-emerald-300',
    descKey: 'herb_tulsi_desc',
    useKeys: ['herb_tulsi_use1', 'herb_tulsi_use2', 'herb_tulsi_use3', 'herb_tulsi_use4'],
    patentNoteKey: 'herb_tulsi_note',
  },
  {
    key: 'ashwagandha',
    en: 'Ashwagandha',
    latin: 'Withania somnifera',
    image: 'https://images.unsplash.com/photo-1611241893603-3c359704e0ee?w=800&q=80&auto=format',
    accent: 'from-amber-700 to-yellow-500',
    accentBg: 'bg-amber-50',
    accentBorder: 'border-amber-300',
    descKey: 'herb_ashwagandha_desc',
    useKeys: ['herb_ashwagandha_use1', 'herb_ashwagandha_use2', 'herb_ashwagandha_use3', 'herb_ashwagandha_use4'],
    patentNoteKey: 'herb_ashwagandha_note',
  },
  {
    key: 'brahmi',
    en: 'Brahmi',
    latin: 'Bacopa monnieri',
    image: 'https://images.unsplash.com/photo-1598532163257-ae3c6b2524b6?w=800&q=80&auto=format',
    accent: 'from-teal-700 to-cyan-500',
    accentBg: 'bg-teal-50',
    accentBorder: 'border-teal-300',
    descKey: 'herb_brahmi_desc',
    useKeys: ['herb_brahmi_use1', 'herb_brahmi_use2', 'herb_brahmi_use3', 'herb_brahmi_use4'],
    patentNoteKey: 'herb_brahmi_note',
  },
  {
    key: 'haldi',
    en: 'Turmeric · Haldi',
    latin: 'Curcuma longa',
    image: 'https://images.unsplash.com/photo-1615484477778-ca3b77940c25?w=800&q=80&auto=format',
    accent: 'from-orange-700 to-amber-500',
    accentBg: 'bg-orange-50',
    accentBorder: 'border-orange-300',
    descKey: 'herb_haldi_desc',
    useKeys: ['herb_haldi_use1', 'herb_haldi_use2', 'herb_haldi_use3', 'herb_haldi_use4'],
    patentNoteKey: 'herb_haldi_note',
  },
  {
    key: 'neem',
    en: 'Neem',
    latin: 'Azadirachta indica',
    image: 'https://images.unsplash.com/photo-1597848212624-a19eb35e2651?w=800&q=80&auto=format',
    accent: 'from-green-800 to-emerald-500',
    accentBg: 'bg-green-50',
    accentBorder: 'border-green-300',
    descKey: 'herb_neem_desc',
    useKeys: ['herb_neem_use1', 'herb_neem_use2', 'herb_neem_use3', 'herb_neem_use4'],
    patentNoteKey: 'herb_neem_note',
  },
  {
    key: 'amla',
    en: 'Amla',
    latin: 'Phyllanthus emblica',
    image: 'https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=800&q=80&auto=format',
    accent: 'from-lime-700 to-green-500',
    accentBg: 'bg-lime-50',
    accentBorder: 'border-lime-300',
    descKey: 'herb_amla_desc',
    useKeys: ['herb_amla_use1', 'herb_amla_use2', 'herb_amla_use3', 'herb_amla_use4'],
    patentNoteKey: 'herb_amla_note',
  },
];

function useScrollReveal(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.unobserve(el);
        }
      },
      { threshold, rootMargin: '0px 0px -60px 0px' }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);

  return { ref, visible };
}

function HerbCard({ herb, index }: { herb: HerbEntry; index: number }) {
  const { lang } = useLang();
  const { ref, visible } = useScrollReveal(0.12);
  const isEven = index % 2 === 0;

  return (
    <div ref={ref} className="relative py-8 md:py-12">
      {/* Background glow */}
      <div
        className={`absolute inset-0 opacity-0 transition-opacity duration-1000 ${visible ? 'opacity-100' : ''}`}
        aria-hidden="true"
      >
        <div className={`absolute top-1/2 ${isEven ? 'left-0' : 'right-0'} -translate-y-1/2 w-[400px] h-[400px] bg-gradient-to-br ${herb.accent} rounded-full blur-[120px] opacity-[0.06]`} />
      </div>

      <div className={`relative flex flex-col ${isEven ? 'lg:flex-row' : 'lg:flex-row-reverse'} items-center gap-8 lg:gap-14`}>
        {/* Image side */}
        <div className="w-full lg:w-[45%] relative">
          <div
            className={`relative rounded-3xl overflow-hidden shadow-2xl shadow-black/10 transition-all duration-[1200ms] ease-out ${
              visible
                ? 'opacity-100 translate-y-0 scale-100'
                : 'opacity-0 translate-y-12 scale-90'
            }`}
          >
            {/* Image container with grow effect */}
            <div className="relative aspect-[4/5] md:aspect-[3/4] overflow-hidden">
              <img
                src={herb.image}
                alt={herb.en}
                className={`w-full h-full object-cover transition-all duration-[1800ms] ease-out ${
                  visible ? 'scale-100' : 'scale-110'
                }`}
                loading="lazy"
              />
              {/* Gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />

              {/* Floating badge on image */}
              <div
                className={`absolute top-4 ${isEven ? 'left-4' : 'right-4'} transition-all duration-700 delay-500 ${
                  visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
                }`}
              >
                <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/90 backdrop-blur-sm text-[11px] font-bold text-slate-800 shadow-lg`}>
                  <Leaf className="w-3.5 h-3.5 text-emerald-600" />
                  {herb.latin}
                </span>
              </div>

              {/* Bottom info on image */}
              <div className="absolute bottom-0 left-0 right-0 p-5 md:p-6">
                <h4 className="text-white text-2xl md:text-3xl font-black font-display drop-shadow-lg">
                  {herb.en}
                </h4>
              </div>
            </div>
          </div>

          {/* Decorative elements */}
          <div
            className={`absolute -z-10 transition-all duration-[1400ms] delay-200 ${
              visible ? 'opacity-100' : 'opacity-0'
            } ${isEven ? '-bottom-4 -right-4' : '-bottom-4 -left-4'}`}
          >
            <div className={`w-24 h-24 rounded-2xl bg-gradient-to-br ${herb.accent} opacity-20 rotate-12`} />
          </div>
          <div
            className={`absolute -z-10 transition-all duration-[1400ms] delay-300 ${
              visible ? 'opacity-100' : 'opacity-0'
            } ${isEven ? '-top-3 -left-3' : '-top-3 -right-3'}`}
          >
            <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${herb.accent} opacity-15 -rotate-6`} />
          </div>
        </div>

        {/* Content side */}
        <div className="w-full lg:w-[55%] space-y-6">
          {/* Name and Latin */}
          <div
            className={`transition-all duration-700 delay-200 ${
              visible ? 'opacity-100 translate-x-0' : `opacity-0 ${isEven ? '-translate-x-8' : 'translate-x-8'}`
            }`}
          >
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-gradient-to-r ${herb.accent} text-white text-[10px] font-bold uppercase tracking-wider mb-3`}>
              <Leaf className="w-3 h-3" />
              {t('herb_badge', lang)}
            </span>
            <h3 className="text-3xl md:text-4xl font-black text-slate-900 font-display">
              {herb.en}
            </h3>
            <p className="text-sm text-slate-400 italic mt-1">{herb.latin}</p>
          </div>

          {/* Description */}
          <p
            className={`text-[15px] text-slate-600 leading-relaxed max-w-lg transition-all duration-700 delay-300 ${
              visible ? 'opacity-100 translate-x-0' : `opacity-0 ${isEven ? '-translate-x-6' : 'translate-x-6'}`
            }`}
          >
            {t(herb.descKey, lang)}
          </p>

          {/* Uses tags */}
          <div
            className={`flex flex-wrap gap-2 transition-all duration-700 delay-[400ms] ${
              visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}
          >
            {herb.useKeys.map((use, i) => (
              <span
                key={use}
                className={`px-3 py-1.5 rounded-full text-[11px] font-bold border ${herb.accentBg} ${herb.accentBorder} text-slate-700 transition-all duration-500`}
                style={{ transitionDelay: `${500 + i * 80}ms` }}
              >
                {t(use, lang)}
              </span>
            ))}
          </div>

          {/* Patent note card */}
          <div
            className={`rounded-2xl border-2 border-dashed ${herb.accentBorder} ${herb.accentBg} p-5 transition-all duration-700 delay-500 ${
              visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${herb.accent} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                <BookOpen className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                  {t('herb_patent_insight', lang)}
                </div>
                <p className="text-[13px] text-slate-600 leading-relaxed">
                  {t(herb.patentNoteKey, lang)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function HerbShowcase() {
  const { lang } = useLang();
  const { ref: headerRef, visible: headerVisible } = useScrollReveal(0.2);

  return (
    <section id="herbs" className="scroll-mt-20 relative">
      {/* Section header */}
      <div ref={headerRef} className="text-center max-w-2xl mx-auto mb-6 md:mb-10">
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-800 text-white text-[10px] font-bold uppercase tracking-wider mb-4 transition-all duration-600 ${
            headerVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <Leaf className="w-3 h-3" />
          {t('herb_section_badge', lang)}
        </span>
        <h3
          className={`text-3xl md:text-4xl font-black text-emerald-900 font-display transition-all duration-700 delay-100 ${
            headerVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          {t('herb_section_title', lang)}
        </h3>
        <p
          className={`mt-3 text-sm text-slate-600 max-w-lg mx-auto transition-all duration-700 delay-200 ${
            headerVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          {t('herb_section_desc', lang)}
        </p>
      </div>

      {/* Scroll hint */}
      <div className="flex justify-center mb-6 md:mb-10">
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-emerald-200 shadow-sm text-[11px] font-semibold text-emerald-700 animate-bounce">
          <ChevronDown className="w-4 h-4" />
          {t('herb_scroll_hint', lang)}
        </div>
      </div>

      {/* Herb cards */}
      <div className="space-y-4 md:space-y-8">
        {HERBS.map((herb, i) => (
          <HerbCard key={herb.key} herb={herb} index={i} />
        ))}
      </div>
    </section>
  );
}
