'use client';
import React from 'react';
import clsx from 'clsx';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
  glow?: 'blue' | 'violet' | 'emerald' | null;
  padding?: 'sm' | 'md' | 'lg';
}

export function GlassCard({ children, className, hover = false, glow = null, padding = 'md', ...props }: GlassCardProps) {
  const pad = { sm: 'p-4', md: 'p-5', lg: 'p-6' };
  return (
    <div
      className={clsx(
        'rounded-3xl border border-emerald-200 bg-white/80 backdrop-blur-xl shadow-[0_8px_30px_rgba(2,44,34,0.08)]',
        hover && 'glass-interactive cursor-pointer',
        pad[padding],
        glow === 'blue' && 'hover:shadow-glow-blue',
        glow === 'violet' && 'hover:shadow-glow-violet',
        glow === 'emerald' && 'hover:shadow-glow-emerald',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
