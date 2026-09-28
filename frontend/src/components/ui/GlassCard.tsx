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
        'rounded-xl border border-gray-300 bg-white',
        hover && 'glass-interactive cursor-pointer',
        pad[padding],
        glow === 'blue' && 'hover:shadow-glow-blue',
        glow === 'violet' && 'hover:shadow-glow-blue',
        glow === 'emerald' && 'hover:shadow-glow-blue',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
