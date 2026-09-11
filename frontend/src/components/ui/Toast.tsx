'use client';
import React, { useEffect } from 'react';
import clsx from 'clsx';
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastProps {
  message: string;
  type?: ToastType;
  onClose: () => void;
  duration?: number;
}

const icons = {
  success: <CheckCircle2 className="w-4 h-4" />,
  error: <XCircle className="w-4 h-4" />,
  warning: <AlertTriangle className="w-4 h-4" />,
  info: <Info className="w-4 h-4" />,
};

const styles: Record<ToastType, string> = {
  success: 'border-emerald-300 text-emerald-700',
  error: 'border-red-300 text-red-700',
  warning: 'border-amber-300 text-amber-700',
  info: 'border-blue-300 text-blue-700',
};

export function Toast({ message, type = 'info', onClose, duration = 4000 }: ToastProps) {
  useEffect(() => {
    const t = setTimeout(onClose, duration);
    return () => clearTimeout(t);
  }, [onClose, duration]);

  return (
    <div className={clsx(
      'fixed top-5 right-5 z-[100] flex items-center gap-2.5 px-4 py-3 rounded-2xl border bg-white/95 backdrop-blur-lg shadow-[0_8px_30px_rgba(2,44,34,0.15)] animate-scaleIn',
      styles[type],
    )}>
      {icons[type]}
      <span className="text-sm text-slate-800">{message}</span>
      <button onClick={onClose} className="ml-1 text-slate-400 hover:text-slate-600 transition flex-shrink-0">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
