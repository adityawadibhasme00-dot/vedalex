'use client';
import React, { useEffect, useRef, useState } from 'react';

type AnimStyle =
  | 'typewriter'
  | 'glitch'
  | 'wave'
  | 'flip3d'
  | 'morph'
  | 'split-cascade'
  | 'neon-glow'
  | 'depth-stack';

interface Text3DProps {
  text: string;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'span';
  style?: AnimStyle;
  className?: string;
  delay?: number;
  gradient?: boolean;
  gradientClass?: string;
}

function useInView(threshold = 0.3) {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVisible(true); obs.unobserve(el); } },
      { threshold, rootMargin: '0px 0px -40px 0px' }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

/* ── Typewriter ──────────────────────────────────────────── */
function TypewriterText({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const { ref, visible } = useInView(0.3);
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!visible) return;
    let i = 0;
    const t = setTimeout(() => {
      const iv = setInterval(() => {
        i++;
        setCount(i);
        if (i >= text.length) clearInterval(iv);
      }, 35);
      return () => clearInterval(iv);
    }, delay);
    return () => clearTimeout(t);
  }, [visible, text, delay]);

  return (
    <span ref={ref as any} className={className}>
      {text.slice(0, count)}
      {count < text.length && visible && (
        <span className="inline-block w-[3px] h-[0.85em] bg-emerald-600 ml-0.5 animate-pulse align-middle" />
      )}
    </span>
  );
}

/* ── Glitch ──────────────────────────────────────────────── */
function GlitchText({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const { ref, visible } = useInView(0.3);
  return (
    <span
      ref={ref as any}
      className={`relative inline-block ${className} ${visible ? 'animate-glitch-in' : 'opacity-0'}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <span className="relative z-10">{text}</span>
      <span className="absolute top-0 left-0 text-cyan-500 opacity-0 animate-glitch-layer1 z-0" aria-hidden="true">{text}</span>
      <span className="absolute top-0 left-0 text-rose-500 opacity-0 animate-glitch-layer2 z-0" aria-hidden="true">{text}</span>
    </span>
  );
}

/* ── Wave (per-letter bounce) ────────────────────────────── */
function WaveText({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const { ref, visible } = useInView(0.3);
  return (
    <span ref={ref as any} className={`inline-flex flex-wrap ${className}`}>
      {text.split('').map((ch, i) => (
        <span
          key={i}
          className={`inline-block transition-all duration-500 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
          style={{
            transitionDelay: visible ? `${delay + i * 50}ms` : '0ms',
            animation: visible ? `wave-bounce 0.6s ease ${delay + i * 50}ms both` : 'none',
          }}
        >
          {ch === ' ' ? '\u00A0' : ch}
        </span>
      ))}
    </span>
  );
}

/* ── Flip 3D ─────────────────────────────────────────────── */
function Flip3DText({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const { ref, visible } = useInView(0.3);
  return (
    <span ref={ref as any} className={`inline-block perspective-[800px] ${className}`}>
      <span
        className={`inline-block transition-all duration-700 ${visible ? 'opacity-100 rotateX-0' : 'opacity-0 -rotateX-90'}`}
        style={{ transformOrigin: 'bottom center', transitionDelay: `${delay}ms` }}
      >
        {text}
      </span>
    </span>
  );
}

/* ── Morph (scale + blur + color shift) ──────────────────── */
function MorphText({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const { ref, visible } = useInView(0.3);
  return (
    <span
      ref={ref as any}
      className={`inline-block ${className} ${visible ? 'animate-morph-in' : 'opacity-0 blur-xl scale-125'}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {text}
    </span>
  );
}

/* ── Split Cascade (words drop in) ───────────────────────── */
function SplitCascadeText({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const { ref, visible } = useInView(0.3);
  const words = text.split(' ');
  return (
    <span ref={ref as any} className={`inline-flex flex-wrap gap-x-[0.35em] ${className}`}>
      {words.map((w, i) => (
        <span
          key={i}
          className={`inline-block transition-all duration-600 ${visible ? 'opacity-100 translate-y-0 rotateX-0' : 'opacity-0 -translate-y-8 -rotateX-60'}`}
          style={{ transitionDelay: visible ? `${delay + i * 100}ms` : '0ms', transformOrigin: 'top center' }}
        >
          {w}
        </span>
      ))}
    </span>
  );
}

/* ── Neon Glow pulse ─────────────────────────────────────── */
function NeonGlowText({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const { ref, visible } = useInView(0.3);
  return (
    <span
      ref={ref as any}
      className={`inline-block ${className} ${visible ? 'animate-neon-pulse' : 'opacity-0'}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {text}
    </span>
  );
}

/* ── Depth Stack (layers from behind) ────────────────────── */
function DepthStackText({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const { ref, visible } = useInView(0.3);
  return (
    <span ref={ref as any} className={`relative inline-block ${className}`}>
      {[...Array(3)].map((_, i) => (
        <span
          key={i}
          className={`absolute inset-0 transition-all duration-700 ${visible ? 'opacity-100' : 'opacity-0'}`}
          style={{
            color: i === 0 ? 'rgba(16,185,129,0.15)' : i === 1 ? 'rgba(16,185,129,0.1)' : 'rgba(16,185,129,0.05)',
            transform: visible
              ? `translateZ(${-20 - i * 15}px) scale(${1 + 0.02 * (3 - i)})`
              : `translateZ(-60px) scale(1.1)`,
            transitionDelay: `${delay + i * 100}ms`,
            zIndex: 3 - i,
          }}
          aria-hidden="true"
        >
          {text}
        </span>
      ))}
      <span
        className={`relative z-10 transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
        style={{ transitionDelay: `${delay + 300}ms` }}
      >
        {text}
      </span>
    </span>
  );
}

const STYLE_MAP: Record<AnimStyle, React.FC<{ text: string; className?: string; delay?: number }>> = {
  typewriter: TypewriterText,
  glitch: GlitchText,
  wave: WaveText,
  flip3d: Flip3DText,
  morph: MorphText,
  'split-cascade': SplitCascadeText,
  'neon-glow': NeonGlowText,
  'depth-stack': DepthStackText,
};

export default function Text3D({
  text,
  as: Tag = 'h2',
  style = 'wave',
  className = '',
  delay = 0,
  gradient = false,
  gradientClass = 'text-gradient',
}: Text3DProps) {
  const Comp = STYLE_MAP[style] || STYLE_MAP.wave;
  return (
    <Tag className={`${className} ${gradient ? gradientClass : ''}`}>
      <Comp text={text} delay={delay} />
    </Tag>
  );
}

export { Text3D };
