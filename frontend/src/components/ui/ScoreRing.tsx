'use client';
import React from 'react';
import { GlassCard } from './GlassCard';

interface ScoreRingProps {
  value: number;
  label: string;
  color?: 'blue' | 'violet' | 'emerald' | 'amber';
  size?: number;
  sublabel?: string;
  bare?: boolean;
}

const ringColors = {
  blue: '#3B82F6',
  violet: '#8B5CF6',
  emerald: '#22C55E',
  amber: '#F59E0B',
};

export function ScoreRing({ value, label, color = 'blue', size = 120, sublabel, bare = false }: ScoreRingProps) {
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (value / 100) * circumference;

  const body = (
    <>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="rgba(5,150,105,0.12)" strokeWidth={stroke}
          />
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none"
            stroke={ringColors[color]}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            style={{ transition: 'stroke-dashoffset 1s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold font-display text-slate-900">{Math.round(value)}%</span>
        </div>
      </div>
      <p className="mt-4 text-sm font-semibold text-slate-700">{label}</p>
      {sublabel && <p className="text-[11px] text-slate-500 mt-1">{sublabel}</p>}
    </>
  );

  if (bare) {
    return <div className="flex flex-col items-center justify-center text-center p-5">{body}</div>;
  }

  return (
    <GlassCard padding="lg" className="flex flex-col items-center justify-center text-center">
      {body}
    </GlassCard>
  );
}
