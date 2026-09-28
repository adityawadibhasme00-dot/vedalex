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
  blue: 'border-l-gov-blue',
  violet: 'border-l-gov-blue',
  emerald: 'border-l-gov-green',
  amber: 'border-l-amber-600',
  red: 'border-l-red-600',
  cyan: 'border-l-gov-blue',
};

const accentText: Record<string, string> = {
  blue: 'text-gov-blue', violet: 'text-gov-blue', emerald: 'text-gov-green',
  amber: 'text-amber-600', red: 'text-red-600', cyan: 'text-gov-blue',
};

const accentBg: Record<string, string> = {
  blue: 'bg-gov-wash', violet: 'bg-gov-wash', emerald: 'bg-green-50',
  amber: 'bg-amber-50', red: 'bg-red-50', cyan: 'bg-gov-wash',
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
