'use client';
import React from 'react';
import { HerbSprig, TulsiLeaf, TurmericRoot, HerbGarland } from '../BotanicalDecor';
import { useAccessibility } from '../../lib/AccessibilityContext';

type LeafKind = React.ComponentType<{ className?: string }>;

interface LeafSpec {
  kind: LeafKind;
  size: number;
  start: number;
  delay: number;
  duration: number;
  drift: number;
  opacity: number;
  color: string;
}

const LEAVES: LeafSpec[] = [
  { kind: TulsiLeaf,    size: 34, start: 2,    delay: 0,    duration: 16, drift: 62,  opacity: 0.65, color: '#059669' },
  { kind: HerbSprig,    size: 30, start: 14,   delay: 2.2,  duration: 19, drift: 48,  opacity: 0.6,  color: '#10b981' },
  { kind: TulsiLeaf,    size: 26, start: 27,   delay: 4.5,  duration: 14, drift: 55,  opacity: 0.55, color: '#0d9488' },
  { kind: HerbGarland,  size: 36, start: 38,   delay: 1.4,  duration: 21, drift: 44,  opacity: 0.5,  color: '#16a34a' },
  { kind: TurmericRoot, size: 28, start: 49,   delay: 6.1,  duration: 17, drift: 58,  opacity: 0.6,  color: '#d97706' },
  { kind: TulsiLeaf,    size: 32, start: 58,   delay: 3.6,  duration: 18, drift: 50,  opacity: 0.6,  color: '#15803d' },
  { kind: HerbSprig,    size: 26, start: 66,   delay: 7.4,  duration: 15, drift: 60,  opacity: 0.5,  color: '#14b8a6' },
  { kind: HerbGarland,  size: 30, start: 73,   delay: 5.2,  duration: 20, drift: 42,  opacity: 0.55, color: '#0f766e' },
  { kind: TulsiLeaf,    size: 38, start: 80,   delay: 0.8,  duration: 22, drift: 52,  opacity: 0.45, color: '#059669' },
  { kind: TurmericRoot, size: 28, start: 88,   delay: 8.9,  duration: 16, drift: 56,  opacity: 0.6,  color: '#b45309' },
  { kind: HerbSprig,    size: 24, start: 93,   delay: 3.1,  duration: 18, drift: 47,  opacity: 0.5,  color: '#22c55e' },
  { kind: TulsiLeaf,    size: 30, start: 98,   delay: 6.8,  duration: 19, drift: 54,  opacity: 0.5,  color: '#0891b2' },
];

export default function WindLeaves() {
  const { reduceMotion } = useAccessibility();
  if (reduceMotion) return null;

  return (
    <div className="fixed inset-0 z-[1] pointer-events-none overflow-hidden" aria-hidden="true">
      {LEAVES.map((l, i) => {
        const K = l.kind;
        return (
          <span
            key={i}
            className="leaf-wind absolute top-0"
            style={
              {
                left: `${l.start}%`,
                width: l.size,
                height: l.size,
                color: l.color,
                animationDelay: `${l.delay}s`,
                animationDuration: `${l.duration}s`,
                '--drift': `${l.drift}%`,
                '--leaf-opacity': l.opacity,
              } as React.CSSProperties
            }
          >
            <K className="w-full h-full" />
          </span>
        );
      })}
    </div>
  );
}