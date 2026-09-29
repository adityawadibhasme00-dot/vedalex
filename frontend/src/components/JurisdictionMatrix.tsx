'use client';

import React from 'react';
import { RegulatoryFinding, StatutoryCitation } from '../types';
import { CheckCircle2, XCircle, AlertCircle, BookOpen, ShieldCheck, ArrowRight } from 'lucide-react';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface JurisdictionMatrixProps {
  findings: RegulatoryFinding[];
  onSelectCitation: (citation: StatutoryCitation) => void;
  coverageMeterScore: number;
}

export default function JurisdictionMatrix({
  findings,
  onSelectCitation,
  coverageMeterScore
}: JurisdictionMatrixProps) {
  const { lang } = useLang();
  if (!findings || findings.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center border border-emerald-200">
        <p className="text-slate-500 text-sm">{t('jm_empty', lang)}</p>
      </div>
    );
  }

  const renderConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case 'HIGH':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full badge-high flex items-center space-x-1"><span>{t('jm_confidence_high', lang)}</span></span>;
      case 'MEDIUM':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full badge-medium flex items-center space-x-1"><span>{t('jm_confidence_medium', lang)}</span></span>;
      case 'LOW':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full badge-low flex items-center space-x-1"><span>{t('jm_confidence_low', lang)}</span></span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full badge-abstain flex items-center space-x-1"><span>{t('jm_confidence_abstain', lang)}</span></span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Overview Header */}
      <div className="flex flex-wrap items-center justify-between glass-panel p-4 rounded-2xl border border-emerald-200 gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900 font-display">{t('jm_title', lang)}</h3>
          <p className="text-xs text-slate-500">
            {t('jm_subtitle', lang)}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="text-right">
            <span className="text-[11px] text-slate-500 block font-medium">{t('jm_coverage_meter', lang)}</span>
            <span className="text-sm font-bold text-emerald-600">{t('jm_evaluated', lang).replace('{n}', String(coverageMeterScore))}</span>
          </div>
          <div className="w-10 h-10 rounded-full border-2 border-emerald-500/40 flex items-center justify-center bg-emerald-100 text-xs font-bold text-emerald-700">
            {coverageMeterScore}%
          </div>
        </div>
      </div>

      {/* 3-Column Comparative Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {findings.map((f, idx) => {
          const isSatisfied = f.status === 'condition_satisfied';
          return (
            <div
              key={idx}
              className={`glass-panel rounded-2xl p-5 border flex flex-col justify-between space-y-4 ${
                isSatisfied ? 'border-emerald-500/30' : 'border-amber-500/40'
              }`}
            >
              <div className="space-y-3.5">
                {/* Jurisdiction Title & Badge */}
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{f.jurisdiction}</span>
                    <h4 className="text-base font-bold text-slate-900 mt-0.5">{f.pathway_category}</h4>
                  </div>
                  {renderConfidenceBadge(f.confidence)}
                </div>

                {/* Status Explanation */}
                <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-slate-600 leading-relaxed">
                  {f.explanation_text || t('jm_fallback_explanation', lang)}
                </div>

                {/* Conditions Evaluated */}
                <div>
                  <span className="text-[11px] font-bold uppercase text-slate-500 block mb-2">{t('jm_conditions_evaluated', lang)}</span>
                  <ul className="space-y-1.5">
                    {f.conditions_evaluated.map((cond, cIdx) => (
                      <li key={cIdx} className="text-xs text-slate-600 flex items-start space-x-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                        <span>{cond}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Clickable Statutory Citations */}
                <div>
                  <span className="text-[11px] font-bold uppercase text-slate-500 block mb-2">
                    {t('jm_citations_title', lang)}
                  </span>
                  <div className="space-y-1.5">
                    {f.supporting_citations.map((cite, citeIdx) => (
                      <button
                        key={citeIdx}
                        onClick={() => onSelectCitation(cite)}
                        className="w-full text-left p-2.5 rounded-xl bg-emerald-100 hover:bg-emerald-50 border border-emerald-500/30 hover:border-emerald-400 text-xs text-emerald-700 flex items-center justify-between transition group"
                      >
                        <div className="flex items-center space-x-2 truncate">
                          <BookOpen className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                          <span className="truncate font-semibold">{cite.act_title} ({cite.section_reference})</span>
                        </div>
                        <span className="text-[10px] text-emerald-600 group-hover:underline flex-shrink-0 ml-2">{t('jm_inspect_gazette', lang)}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Next Action Steps */}
                <div>
                  <span className="text-[11px] font-bold uppercase text-slate-500 block mb-2">{t('jm_next_prep_actions', lang)}</span>
                  <ul className="space-y-1.5">
                    {f.next_action_steps.map((step, sIdx) => (
                      <li key={sIdx} className="text-xs text-slate-600 flex items-start space-x-2">
                        <ArrowRight className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                        <span>{step}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Coverage Limitations Box */}
              <div className="pt-3 border-t border-emerald-200">
                <div className="p-2.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-[11px] text-slate-500">
                  <span className="font-semibold text-slate-600 block mb-0.5">{t('jm_coverage_limitations', lang)}</span>
                  {f.coverage_limitations}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
