'use client';

import React from 'react';
import { ClarificationQuery } from '../types';
import { AlertCircle, ArrowRight, Check } from 'lucide-react';

interface ClarificationAlertProps {
  clarifications: ClarificationQuery[];
  currentLang: string;
  onResolve: (queryId: string, selectedOption: string) => void;
}

export default function ClarificationAlert({
  clarifications,
  currentLang,
  onResolve
}: ClarificationAlertProps) {
  if (!clarifications || clarifications.length === 0) return null;

  const query = clarifications[0];
  const questionText = query.question_text[currentLang] || query.question_text['en'] || Object.values(query.question_text)[0];

  return (
    <div className="mb-6 p-4 rounded-2xl bg-amber-100 border border-amber-300 shadow-xl backdrop-blur-md">
      <div className="flex items-start space-x-3.5">
        <div className="p-2 rounded-xl bg-amber-200 text-amber-700 mt-0.5">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider rounded bg-amber-200 text-amber-700 border border-amber-300">
              Decision-Critical Clarification Required
            </span>
          </div>
          <h2 className="text-base font-semibold text-slate-900 mt-1.5">{questionText}</h2>
          <p className="text-xs text-amber-700/90 mt-1">
            Resolving this variable determines whether your product falls under the FSSAI Ayurveda Aahara food category or requires an AYUSH Drug Manufacturing License under Rule 158-B.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3.5">
            {query.options.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => onResolve(query.id, opt)}
                className="flex items-center justify-between text-left px-3.5 py-2.5 rounded-xl bg-emerald-50/70 hover:bg-emerald-100 border border-emerald-200 hover:border-emerald-400 text-xs font-medium text-slate-700 transition group"
              >
                <span>{opt}</span>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-600 transform group-hover:translate-x-1 transition" />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
