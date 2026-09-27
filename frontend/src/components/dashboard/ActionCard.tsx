'use client';
import React from 'react';
import clsx from 'clsx';

interface ActionCardProps {
  icon: React.ReactNode;
  label: string;
  description: string;
  color: 'emerald' | 'blue' | 'amber';
  onClick: () => void;
}

const colorClasses: Record<ActionCardProps['color'], { bg: string; border: string; iconBg: string }> = {
  emerald: {
    bg: 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800',
    border: 'hover:border-emerald-300',
    iconBg: 'bg-emerald-600',
  },
  blue: {
    bg: 'bg-blue-50 hover:bg-blue-100 text-blue-800',
    border: 'hover:border-blue-300',
    iconBg: 'bg-blue-600',
  },
  amber: {
    bg: 'bg-amber-50 hover:bg-amber-100 text-amber-800',
    border: 'hover:border-amber-300',
    iconBg: 'bg-amber-500',
  },
};

export function ActionCard({ icon, label, description, color, onClick }: ActionCardProps) {
  const c = colorClasses[color];
  return (
    <button
      onClick={onClick}
      className={clsx(
        'block w-full text-left p-6 rounded-2xl border-2 border-transparent bg-white shadow-sm',
        c.bg, c.border,
        'transition-all hover:scale-[1.02] hover:shadow-lg',
      )}
    >
      <div className="flex items-start gap-4">
        <div className={clsx('h-12 w-12 rounded-xl flex items-center justify-center shadow-md flex-shrink-0', c.iconBg)}>
          <span className="text-white">{icon}</span>
        </div>
        <div className="min-w-0">
          <h3 className="font-semibold text-lg text-gray-900 mb-1">{label}</h3>
          <p className="text-sm text-gray-600 leading-snug">{description}</p>
        </div>
      </div>
    </button>
  );
}