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
    primary:   'bg-gov-blue hover:bg-gov-navy text-white border border-gov-blueDk',
    secondary: 'bg-white hover:bg-gov-wash text-slate-700 border border-gray-300',
    ghost:     'bg-transparent hover:bg-gov-wash text-slate-600',
    danger:    'bg-red-600 hover:bg-red-700 text-white border border-red-800',
    success:   'bg-gov-green hover:bg-green-800 text-white border border-green-900',
  };
  const sizes = {
    sm: 'px-3 py-1.5 text-xs rounded-lg gap-1.5',
    md: 'px-4 py-2 text-sm rounded-lg gap-2',
    lg: 'px-5 py-2.5 text-sm rounded-lg gap-2',
  };
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center font-semibold transition-colors active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed',
        variants[variant], sizes[size], className,
      )}
      {...props}
    >
      {icon && <span className="flex-shrink-0">{icon}</span>}
      {children}
    </button>
  );
}
