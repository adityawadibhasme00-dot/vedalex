'use client';

import React from 'react';
import clsx from 'clsx';
import { Globe, MapPin, Scale } from 'lucide-react';

export type JurisdictionValue = 'india' | 'international' | 'both';

interface JurisdictionToggleProps {
  value: JurisdictionValue;
  onChange: (value: JurisdictionValue) => void;
  className?: string;
  disabled?: boolean;
  /** Rendered above the segmented control (screen-reader friendly). */
  label?: string;
}

const OPTIONS: {
  id: JurisdictionValue;
  label: string;
  icon: React.ReactNode;
  hint: string;
}[] = [
  {
    id: 'india',
    label: 'India',
    icon: <MapPin className="w-3.5 h-3.5" aria-hidden="true" />,
    hint: 'Indian statutes · IP India · AYUSH · NBA',
  },
  {
    id: 'international',
    label: 'International',
    icon: <Globe className="w-3.5 h-3.5" aria-hidden="true" />,
    hint: 'WIPO · PCT · TRIPS · Madrid',
  },
  {
    id: 'both',
    label: 'Both',
    icon: <Scale className="w-3.5 h-3.5" aria-hidden="true" />,
    hint: 'Separate sections — never merged',
  },
];

/**
 * India ↔ International scope switch (Master Prompt v7.0.0, Component 3).
 *
 * Jurisdiction-filtered retrieval contract: the selected value is passed to
 * the backend so India and International sources are NEVER mixed in one
 * answer — `both` keeps two independent, separately-cited sections.
 */
export function JurisdictionToggle({
  value,
  onChange,
  className,
  disabled = false,
  label = 'Jurisdiction scope',
}: JurisdictionToggleProps) {
  return (
    <div className={clsx('flex flex-col gap-1', className)}>
      <span
        id="jurisdiction-toggle-label"
        className="text-[10px] font-bold uppercase tracking-wider text-slate-500"
      >
        {label}
      </span>
      <div
        role="group"
        aria-labelledby="jurisdiction-toggle-label"
        className="inline-flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm"
      >
        {OPTIONS.map((opt) => {
          const active = value === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              disabled={disabled}
              aria-pressed={active}
              title={opt.hint}
              onClick={() => onChange(opt.id)}
              className={clsx(
                'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                active
                  ? 'bg-emerald-700 text-white shadow'
                  : 'text-slate-600 hover:bg-slate-100'
              )}
            >
              {opt.icon}
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default JurisdictionToggle;
