'use client';
import React from 'react';
import { GlassCard } from './GlassCard';

interface PageHeaderProps {
  title: React.ReactNode;
  subtitle?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageHeader({ title, subtitle, icon, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
      <div className="flex items-center gap-3">
        {icon && (
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-white shadow-glow-blue flex-shrink-0">
            {icon}
          </div>
        )}
        <div>
          <h1 className="text-xl font-bold font-display text-slate-900 tracking-tight">{title}</h1>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </div>
  );
}
