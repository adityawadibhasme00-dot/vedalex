'use client';
import React from 'react';
import clsx from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
}

export function Button({ children, variant = 'primary', size = 'md', icon, className, ...props }: ButtonProps) {
  const variants = {
    primary:   'bg-emerald-700 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-700/20',
    secondary: 'bg-white hover:bg-emerald-50 text-slate-700 border border-emerald-200',
    ghost:     'bg-transparent hover:bg-emerald-50 text-slate-600',
    danger:    'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/20',
    success:   'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20',
  };
  const sizes = {
    sm: 'px-3 py-1.5 text-xs rounded-xl gap-1.5',
    md: 'px-4 py-2 text-sm rounded-xl gap-2',
    lg: 'px-5 py-2.5 text-sm rounded-2xl gap-2',
  };
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center font-semibold transition-all active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed',
        variants[variant], sizes[size], className,
      )}
      {...props}
    >
      {icon && <span className="flex-shrink-0">{icon}</span>}
      {children}
    </button>
  );
}
