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
    bg: 'bg-green-50 hover:bg-green-100 text-green-800',
    border: 'hover:border-green-300',
    iconBg: 'bg-gov-green',
  },
  blue: {
    bg: 'bg-blue-50 hover:bg-blue-100 text-blue-800',
    border: 'hover:border-blue-300',
    iconBg: 'bg-gov-blue',
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
        'block w-full text-left p-6 rounded-xl border-2 border-transparent bg-white shadow-sm',
        c.bg, c.border,
        'transition-colors hover:shadow-md',
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