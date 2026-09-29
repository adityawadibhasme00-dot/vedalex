'use client';
import React, { useEffect, useRef, useState } from 'react';
import {
  Lightbulb, Search, FileText, BadgeCheck, QrCode, FileDown,
  CheckCircle2,
} from 'lucide-react';
import { useLang } from '../../lib/LangContext';
import { t } from '../../lib/i18n';
import Text3D from './Text3D';

interface Step {
  key: string;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
  descKey: string;
  pointKeys: string[];
  tagKey: string;
}

const STEPS: Step[] = [
  {
    key: 'idea',
    labelKey: 'process_idea_label',
    icon: Lightbulb,
    descKey: 'process_idea_desc',
    pointKeys: ['process_idea_p1', 'process_idea_p2', 'process_idea_p3'],
    tagKey: 'process_idea_tag',
  },
  {
    key: 'verification',
    labelKey: 'process_verification_label',
    icon: Search,
    descKey: 'process_verification_desc',
    pointKeys: ['process_verification_p1', 'process_verification_p2', 'process_verification_p3'],
    tagKey: 'process_verification_tag',
  },
  {
    key: 'prior-art',
    labelKey: 'process_prior_art_label',
    icon: FileText,
    descKey: 'process_prior_art_desc',
    pointKeys: ['process_prior_art_p1', 'process_prior_art_p2', 'process_prior_art_p3'],
    tagKey: 'process_prior_art_tag',
  },
  {
    key: 'readiness',
    labelKey: 'patent_readiness',
    icon: BadgeCheck,
    descKey: 'process_readiness_desc',
    pointKeys: ['process_readiness_p1', 'process_readiness_p2', 'process_readiness_p3'],
    tagKey: 'process_readiness_tag',
  },
  {
    key: 'passport',
    labelKey: 'innovation_passport',
    icon: QrCode,
    descKey: 'process_passport_desc',
    pointKeys: ['process_passport_p1', 'process_passport_p2', 'process_passport_p3'],
    tagKey: 'process_passport_tag',
  },
  {
    key: 'export',
    labelKey: 'process_export_label',
    icon: FileDown,
    descKey: 'process_export_desc',
    pointKeys: ['process_export_p1', 'process_export_p2', 'process_export_p3'],
    tagKey: 'process_export_tag',
  },
];

/* Scroll-progress hook — returns 0..1 progressively as element scrolls into view */
function useScrollProgress() {
  const ref = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let raf = 0;
    const update = () => {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      const p = Math.min(1, Math.max(0, 1 - (rect.top - vh * 0.12) / (vh * 0.65)));
      setProgress(p);
    };
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  return { ref, progress };
}

function ProcessStep({ step, index }: { step: Step; index: number }) {
  const { lang } = useLang();
  const { ref, progress } = useScrollProgress();
  const isLeft = index % 2 === 0;
  const Icon = step.icon;
  const r = progress;

  return (
    <div ref={ref} className="relative mb-12 md:mb-16 last:mb-0">
      {/* Center timeline line */}
      <div className="hidden lg:block absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-emerald-600/0 via-emerald-500/40 to-emerald-600/0" aria-hidden="true" />

      {/* Node on the line */}
      <div className="hidden lg:flex absolute top-1 left-1/2 -translate-x-1/2 z-10">
        <div className={`w-11 h-11 rounded-full bg-emerald-900 border border-amber-400/50 flex items-center justify-center ${r > 0.15 ? 'animate-step-3d' : ''}`}>
          <Icon className="w-5 h-5 text-amber-400" />
        </div>
      </div>

      {/* Minimal row — glides in from its side with scroll */}
      <div className={`${isLeft ? 'lg:pr-[calc(50%+3rem)]' : 'lg:pl-[calc(50%+3rem)]'} will-change-transform`}>
        <div
          className="relative"
          style={{
            opacity: 0.35 + r * 0.65,
            transform: `perspective(1100px) rotateY(${(1 - r) * (isLeft ? 10 : -10)}deg) translate3d(${(1 - r) * (isLeft ? -70 : 70)}px, 0, 0)`,
            filter: `blur(${(1 - r) * 4}px)`,
            transition: 'transform 0.15s linear, opacity 0.15s linear, filter 0.15s linear',
          }}
        >
          {/* Thin accent rail */}
          <div className="border-l-2 border-amber-400/60 pl-4 md:pl-5">
            {/* Header */}
            <div className="flex items-center gap-3">
              <div className="flex lg:hidden w-9 h-9 rounded-full bg-emerald-900 border border-emerald-700 flex items-center justify-center">
                <Icon className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <span className="text-[10px] font-black tracking-[0.2em] uppercase text-amber-400">{t(step.tagKey, lang)}</span>
                  <span className="h-px w-8 bg-emerald-500/40" aria-hidden="true" />
                  <span className="text-[10px] font-bold text-emerald-300/70">{String(index + 1).padStart(2, '0')}</span>
                </div>
                <h4 className="text-xl font-black text-white font-display leading-tight">{t(step.labelKey, lang)}</h4>
              </div>
              <CheckCircle2
                className={`w-5 h-5 text-emerald-400 ml-auto hidden lg:block transition-all duration-700 ${r > 0 ? 'opacity-100 scale-100' : 'opacity-0 scale-50'}`}
              />
            </div>

            <p className="mt-2 text-sm text-emerald-100/75 leading-relaxed max-w-md">{t(step.descKey, lang)}</p>

            {/* Fill line that grows with scroll */}
            <div className="mt-4 h-px bg-emerald-700/40 overflow-hidden" aria-hidden="true">
              <div className="h-full bg-gradient-to-r from-amber-400 to-emerald-400 transition-[width] duration-150" style={{ width: `${Math.round(r * 100)}%` }} />
            </div>

            {/* Points revealed one-by-one */}
            <ul className="mt-3 space-y-1.5">
              {step.pointKeys.map((pt, i) => {
                const shown = r > 0.2 + i * 0.16;
                return (
                  <li
                    key={pt}
                    className="flex items-start gap-2 text-xs text-emerald-100/80 transition-all duration-300"
                    style={{ opacity: shown ? 1 : 0.3, transform: `translateX(${(1 - r) * 12}px)` }}
                  >
                    <CheckCircle2
                      className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0 transition-all duration-300"
                      style={{ opacity: shown ? 1 : 0.35, transform: shown ? 'scale(1)' : 'scale(0.7)' }}
                    />
                    <span>{t(pt, lang)}</span>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Ghost step number */}
          <span className="absolute -top-6 right-0 text-[56px] font-black text-emerald-500/15 font-display leading-none select-none" aria-hidden="true">
            {String(index + 1).padStart(2, '0')}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function ProcessParallax() {
  const { lang } = useLang();

  return (
    <section id="process" className="scroll-mt-20 rounded-3xl bg-emerald-900 shadow-xl shadow-emerald-900/20 overflow-hidden">
      <div className="px-6 lg:px-10 py-10 lg:py-14">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500 text-white text-[10px] font-bold uppercase tracking-wider mb-4 animate-fade-in-up">
            <Lightbulb className="w-3 h-3" /> {t('process_why_choose', lang)}
          </span>
          <Text3D
            as="h3"
            text={t('landing_one_journey', lang)}
            style="neon-glow"
            delay={200}
            className="text-3xl font-black text-white font-display"
          />
          <p className="mt-3 text-sm text-emerald-200/90 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            {t('process_scroll_hint', lang)}
          </p>
        </div>

        {/* Timeline steps */}
        <div className="relative max-w-5xl mx-auto">
          {/* Mobile line */}
          <div className="lg:hidden absolute left-[7px] top-0 bottom-0 w-px bg-gradient-to-b from-emerald-600/0 via-emerald-500/50 to-emerald-600/0" aria-hidden="true" />
          <div className="space-y-6 md:space-y-10">
            {STEPS.map((step, i) => (
              <ProcessStep key={step.key} step={step} index={i} />
            ))}
          </div>
        </div>

        <p className="mt-12 text-center text-[11px] text-emerald-300/70">
          {t('process_sources_note', lang)}
        </p>
      </div>
    </section>
  );
}