'use client';
import React, { useState } from 'react';
import { PencilLine } from 'lucide-react';

const selectCls =
  "w-full px-4 py-3 bg-emerald-50/70 border border-emerald-200 rounded-xl text-sm text-slate-900 placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition";
const otherCls =
  "w-full px-3.5 py-2.5 mt-2 bg-white border border-dashed border-blue-400 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500/60 focus:bg-blue-50/30 transition";

interface SelectOrOtherProps {
  label?: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  allowOther?: boolean;
  otherLabel?: string;
  hint?: string;
  inputPlaceholder?: string;
  otherCaption?: string;
  className?: string;
}

/**
 * A native <select> dropdown with a final "Other" option. Picking "Other"
 * reveals a free-text input so users can type a custom value (e.g. an exact
 * ethanol concentration like "Ethanol 90% + Water 10%"), write "official",
 * or paste an official source link when they don't have the exact data.
 * The typed value becomes the field's value (serialised as-is downstream).
 */
export function SelectOrOther({
  label,
  options,
  value,
  onChange,
  placeholder,
  allowOther = true,
  otherLabel = 'Other (type your own / official value)',
  hint,
  inputPlaceholder = 'Type your value — e.g. Ethanol 90% + Water 10%, "official", or paste the official source link',
  otherCaption = 'Custom value noted — it will be saved with the passport.',
  className,
}: SelectOrOtherProps) {
  const isOtherValue =
    value !== '' && value !== (placeholder ?? '') && !options.includes(value);
  const [editingOther, setEditingOther] = useState(isOtherValue);
  const [otherDraft, setOtherDraft] = useState(isOtherValue ? value : '');

  const isOther = editingOther || isOtherValue;

  const handleSelect = (v: string) => {
    if (v === '__other__') {
      setEditingOther(true);
      onChange(otherDraft);
    } else {
      setEditingOther(false);
      setOtherDraft('');
      onChange(v);
    }
  };

  const handleOtherInput = (t: string) => {
    setOtherDraft(t);
    onChange(t);
  };

  return (
    <div className={className}>
      {label && <label className="text-xs text-slate-500 mb-1.5 block">{label}</label>}
      <div className="relative">
        <select
          value={isOther ? '__other__' : value}
          onChange={(e) => handleSelect(e.target.value)}
          className={`${selectCls} ${isOther ? 'border-blue-400' : ''}`}
        >
          {placeholder !== undefined && (
            <option value="" disabled>{placeholder}</option>
          )}
          {options.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
          {allowOther && <option value="__other__">{otherLabel}</option>}
        </select>
        {isOther && (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-blue-500">
            <PencilLine className="w-4 h-4" />
          </span>
        )}
      </div>

      {isOther && (
        <div className="mt-2">
          <input
            value={otherDraft}
            onChange={(e) => handleOtherInput(e.target.value)}
            placeholder={inputPlaceholder}
            className={otherCls}
            autoFocus
          />
          <p className="text-[10px] text-blue-500 mt-1 flex items-center gap-1">
            <PencilLine className="w-3 h-3" /> {otherCaption}
          </p>
        </div>
      )}

      {hint && !isOther && (
        <p className="text-[10px] text-slate-400 mt-1">{hint}</p>
      )}
    </div>
  );
}