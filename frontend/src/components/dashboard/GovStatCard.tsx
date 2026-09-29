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
    <div className="bg-white rounded-xl border border-gov-rule p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="h-12 w-12 bg-gov-wash border border-gov-rule rounded-lg flex items-center justify-center flex-shrink-0">
          <span className="text-gov-blue">{icon}</span>
        </div>
        <span className={clsx(
          'text-xs font-medium text-right',
          trend === 'up' ? 'text-gov-green' : 'text-red-600',
        )}>
          {change}
        </span>
      </div>
      <div className="text-3xl font-bold text-gray-900 mb-1 tracking-tight">{value}</div>
      <div className="text-sm text-gray-600">{label}</div>
    </div>
  );
}