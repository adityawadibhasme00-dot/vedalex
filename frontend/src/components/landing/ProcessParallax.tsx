'use client';
import React, { useEffect, useRef, useState } from 'react';
import {
  Lightbulb, Search, FileText, BadgeCheck, QrCode, FileDown,
  CheckCircle2,
} from 'lucide-react';
import { useLang } from '../../lib/LangContext';
import Text3D from './Text3D';

interface Step {
  key: string;
  label: string;
  hilabel: string;
  icon: React.ComponentType<{ className?: string }>;
  descEn: string;
  descHi: string;
  points: [string, string][];
  tagEn: string;
  tagHi: string;
}

const STEPS: Step[] = [
  {
    key: 'idea',
    label: 'Idea',
    hilabel: 'विचार',
    icon: Lightbulb,
    descEn: 'Document your formulation, botanical ingredients and intended claims in a structured innovation dossier.',
    descHi: 'अपने फॉर्मूलेशन, वनस्पति घटकों और इच्छित दावों को संरचित इनोवेशन डोज़ियर में दर्ज करें।',
    points: [
      ['Record your formulation & ingredients', 'अपना फॉर्मूलेशन और घटक दर्ज करें'],
      ['List proposed claims & intended use', 'प्रस्तावित दावे और उपयोग सूचीबद्ध करें'],
      ['One structured innovation dossier', 'एक संरचित इनोवेशन डोज़ियर'],
    ],
    tagEn: 'Capture',
    tagHi: 'पकड़ें',
  },
  {
    key: 'verification',
    label: 'Verification',
    hilabel: 'जाँच',
    icon: Search,
    descEn: 'AI validates botanical identity, cross-matches 9 Indian languages and flags missing evidence.',
    descHi: 'AI वनस्पति पहचान सत्यापित करता है, 9 भारतीय भाषाओं में मिलान करता है और लुप्त साक्ष्य चिह्नित करता है।',
    points: [
      ['Botanical identity auto-validated', 'वनस्पति पहचान स्वतः सत्यापित'],
      ['9 Indian languages cross-matched', '9 भारतीय भाषाओं में मिलान'],
      ['Missing evidence flagged instantly', 'लुप्त साक्ष्य तुरंत चिह्नित'],
    ],
    tagEn: 'Screen',
    tagHi: 'जाँचें',
  },
  {
    key: 'prior-art',
    label: 'Prior Art',
    hilabel: 'पूर्व आधार',
    icon: FileText,
    descEn: 'RAG engine sweeps TKDL, IP India, WIPO, PubMed and WHO to uncover overlapping disclosures.',
    descHi: 'RAG इंजन TKDL, IP India, WIPO, PubMed और WHO में झाँककर अतिव्यापी प्रकटीकरण खोजता है।',
    points: [
      ['TKDL · IP India · WIPO sweep', 'TKDL · IP India · WIPO खोज'],
      ['PubMed & WHO manuscripts', 'PubMed और WHO दस्तावेज़'],
      ['Overlapping disclosures revealed', 'अतिव्यापी प्रकटीकरण सामने आएं'],
    ],
    tagEn: 'Search',
    tagHi: 'खोजें',
  },
  {
    key: 'readiness',
    label: 'Patent Readiness',
    hilabel: 'पेटेंट तैयारी',
    icon: BadgeCheck,
    descEn: 'Section 3(p) compliance score with TKDL grounding and claim-by-claim risk analysis.',
    descHi: 'TKDL-पुष्ट सेक्शन 3(p) अनुपालन स्कोर और दावे-दर-दावे जोखिम विश्लेषण।',
    points: [
      ['Section 3(p) compliance score', 'सेक्शन 3(p) अनुपालन स्कोर'],
      ['TKDL-grounded reasoning', 'TKDL-पुष्ट तर्क'],
      ['Claim-by-claim risk analysis', 'दावे-दर-दावे जोखिम विश्लेषण'],
    ],
    tagEn: 'Assess',
    tagHi: 'मूल्यांकन',
  },
  {
    key: 'passport',
    label: 'Innovation Passport',
    hilabel: 'इनोवेशन पासपोर्ट',
    icon: QrCode,
    descEn: 'A verifiable digital passport with QR authenticity, version history and PDF export.',
    descHi: 'QR प्रामाणिकता, संस्करण इतिहास और PDF निर्यात के साथ सत्यापन-योग्य डिजिटल पासपोर्ट।',
    points: [
      ['Verifiable digital passport', 'सत्यापन-योग्य डिजिटल पासपोर्ट'],
      ['QR authenticity stamp', 'QR प्रामाणिकता मुहर'],
      ['Version history & PDF export', 'संस्करण इतिहास और PDF निर्यात'],
    ],
    tagEn: 'Generate',
    tagHi: 'बनाएँ',
  },
  {
    key: 'export',
    label: 'Export',
    hilabel: 'निर्यात',
    icon: FileDown,
    descEn: 'Regulatory pathway maps for IN · US · CA jurisdictions to launch your innovation worldwide.',
    descHi: 'IN · US · CA क्षेत्रों के लिए विनियामक मार्ग-मानचित्र — वैश्विक स्तर पर लॉन्च करें।',
    points: [
      ['IN · US · CA pathway maps', 'IN · US · CA मार्ग मानचित्र'],
      ['Jurisdiction risk preview', 'क्षेत्रीय जोखिम पूर्वाभास'],
      ['Launch globally with confidence', 'आत्मविश्वास के साथ वैश्विक लॉन्च'],
    ],
    tagEn: 'Go Global',
    tagHi: 'वैश्विक पहुँच',
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
  const Hi = (en: string, hi: string) => (lang === 'hi' ? hi : en);
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
                  <span className="text-[10px] font-black tracking-[0.2em] uppercase text-amber-400">{Hi(step.tagEn, step.tagHi)}</span>
                  <span className="h-px w-8 bg-emerald-500/40" aria-hidden="true" />
                  <span className="text-[10px] font-bold text-emerald-300/70">{String(index + 1).padStart(2, '0')}</span>
                </div>
                <h4 className="text-xl font-black text-white font-display leading-tight">{Hi(step.label, step.hilabel)}</h4>
              </div>
              <CheckCircle2
                className={`w-5 h-5 text-emerald-400 ml-auto hidden lg:block transition-all duration-700 ${r > 0 ? 'opacity-100 scale-100' : 'opacity-0 scale-50'}`}
              />
            </div>

            <p className="mt-2 text-sm text-emerald-100/75 leading-relaxed max-w-md">{Hi(step.descEn, step.descHi)}</p>

            {/* Fill line that grows with scroll */}
            <div className="mt-4 h-px bg-emerald-700/40 overflow-hidden" aria-hidden="true">
              <div className="h-full bg-gradient-to-r from-amber-400 to-emerald-400 transition-[width] duration-150" style={{ width: `${Math.round(r * 100)}%` }} />
            </div>

            {/* Points revealed one-by-one */}
            <ul className="mt-3 space-y-1.5">
              {step.points.map((pt, i) => {
                const shown = r > 0.2 + i * 0.16;
                return (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-xs text-emerald-100/80 transition-all duration-300"
                    style={{ opacity: shown ? 1 : 0.3, transform: `translateX(${(1 - r) * 12}px)` }}
                  >
                    <CheckCircle2
                      className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0 transition-all duration-300"
                      style={{ opacity: shown ? 1 : 0.35, transform: shown ? 'scale(1)' : 'scale(0.7)' }}
                    />
                    <span>{Hi(pt[0], pt[1])}</span>
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
  const Hi = (en: string, hi: string) => (lang === 'hi' ? hi : en);

  return (
    <section id="process" className="scroll-mt-20 rounded-3xl bg-emerald-900 shadow-xl shadow-emerald-900/20 overflow-hidden">
      <div className="px-6 lg:px-10 py-10 lg:py-14">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500 text-white text-[10px] font-bold uppercase tracking-wider mb-4 animate-fade-in-up">
            <Lightbulb className="w-3 h-3" /> {Hi('Why Choose IP-SAKTI', 'IP-SAKTI \u0915\u094D\u092F\u094B\u0902 \u091A\u0941\u0928\u0947\u0902')}
          </span>
          <Text3D
            as="h3"
            text={Hi('One journey, every safeguard', '\u090F\u0915 \u092F\u093E\u0924\u094D\u0930\u093E, \u0939\u0930 \u0938\u0941\u0930\u0915\u094D\u0937\u093E')}
            style="neon-glow"
            delay={200}
            className="text-3xl font-black text-white font-display"
          />
          <p className="mt-3 text-sm text-emerald-200/90 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            {Hi('Scroll through the journey — each stage glides in from its side as you scroll.', '\u092F\u093E\u0924\u094D\u0930\u093E को स्क्रॉल करें — हर चरण स्क्रॉल करते ही अपनी ओर से ग्लाइड करके सामने आता है।')}
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
          {Hi('Every stage is grounded in statutory sources — TKDL, IP India, WIPO, PubMed, and WHO.', 'हर चरण क़ानूनी स्रोतों से पुष्ट — TKDL, IP India, WIPO, PubMed, और WHO।')}
        </p>
      </div>
    </section>
  );
}