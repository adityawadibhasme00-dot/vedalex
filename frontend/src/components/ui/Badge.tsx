'use client';
import React from 'react';
import clsx from 'clsx';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  dot?: boolean;
  className?: string;
}

export function Badge({ children, variant = 'info', dot = false, className }: BadgeProps) {
  const styles = {
    success: 'bg-green-50 text-gov-green border border-green-300',
    warning: 'bg-amber-50 text-amber-700 border border-amber-300',
    danger:  'bg-red-50 text-red-700 border border-red-300',
    info:    'bg-blue-50 text-gov-blue border border-blue-300',
    neutral: 'bg-white text-slate-600 border border-slate-300',
  };
  const dotColors = {
    success: 'bg-gov-green', warning: 'bg-amber-500', danger: 'bg-red-500',
    info: 'bg-gov-blue', neutral: 'bg-slate-400',
  };
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold rounded-md',
      styles[variant], className,
    )}>
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', dotColors[variant])} />}
      {children}
    </span>
  );
}
