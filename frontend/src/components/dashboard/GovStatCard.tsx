'use client';
import React from 'react';
import clsx from 'clsx';

interface GovStatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
}

export function GovStatCard({ icon, label, value, change, trend }: GovStatCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-lg hover:-translate-y-0.5 transition-all">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="h-12 w-12 bg-emerald-50 rounded-xl flex items-center justify-center flex-shrink-0">
          <span className="text-emerald-600">{icon}</span>
        </div>
        <span className={clsx(
          'text-xs font-medium text-right',
          trend === 'up' ? 'text-emerald-600' : 'text-red-600',
        )}>
          {change}
        </span>
      </div>
      <div className="text-3xl font-bold text-gray-900 mb-1 tracking-tight">{value}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </div>
  );
}