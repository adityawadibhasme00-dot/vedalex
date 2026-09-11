'use client';
import React from 'react';
import clsx from 'clsx';
import { GlassCard } from './GlassCard';

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon: React.ReactNode;
  accent?: 'blue' | 'violet' | 'emerald' | 'amber' | 'red' | 'cyan';
  trend?: 'up' | 'down' | null;
  className?: string;
}

const accentBorder: Record<string, string> = {
  blue: 'border-l-blue-500',
  violet: 'border-l-violet-500',
  emerald: 'border-l-emerald-500',
  amber: 'border-l-amber-500',
  red: 'border-l-red-500',
  cyan: 'border-l-cyan-500',
};

const accentText: Record<string, string> = {
  blue: 'text-blue-600', violet: 'text-violet-600', emerald: 'text-emerald-600',
  amber: 'text-amber-600', red: 'text-red-600', cyan: 'text-cyan-600',
};

const accentBg: Record<string, string> = {
  blue: 'bg-blue-100', violet: 'bg-violet-100', emerald: 'bg-emerald-100',
  amber: 'bg-amber-100', red: 'bg-red-100', cyan: 'bg-cyan-100',
};

export function StatCard({ label, value, subtext, icon, accent = 'blue', className }: StatCardProps) {
  return (
    <GlassCard
      padding="md"
      className={clsx(
        'border-l-4',
        accentBorder[accent],
        'group',
        className,
      )}
      hover
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-1.5">{label}</p>
          <p className="text-2xl font-bold font-display text-slate-900 tracking-tight">{value}</p>
          {subtext && <p className="text-xs text-slate-500 mt-1.5">{subtext}</p>}
        </div>
        <div className={clsx(
          'w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0',
          accentBg[accent],
        )}>
          <span className={accentText[accent]}>{icon}</span>
        </div>
      </div>
    </GlassCard>
  );
}
