'use client';

import React from 'react';
import { StatutoryCitation } from '../types';
import { BookOpen, ExternalLink, ShieldCheck, X } from 'lucide-react';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface CitationPopoverProps {
  citation: StatutoryCitation | null;
  onClose: () => void;
}

export default function CitationPopover({ citation, onClose }: CitationPopoverProps) {
  const { lang } = useLang();
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel max-w-xl w-full rounded-2xl p-6 border border-emerald-500/30 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-emerald-200">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-emerald-100 text-emerald-600">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-600">
                {t('citation_primary_ref', lang)} ({t('citation_rank', lang)} #{citation.authority_rank} {t('citation_authority_word', lang)})
              </span>
              <h3 className="text-lg font-bold text-slate-900 leading-snug">{citation.act_title}</h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-emerald-50 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-4 my-5">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200">
              <span className="text-slate-500 block mb-1">{t('citation_section_ref', lang)}</span>
              <span className="font-semibold text-slate-900">{citation.section_reference}</span>
            </div>
            <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200">
              <span className="text-slate-500 block mb-1">{t('citation_effective_date', lang)}</span>
              <span className="font-semibold text-emerald-600">{citation.effective_date}</span>
            </div>
          </div>

          <div>
            <span className="text-xs text-slate-500 block mb-1.5 font-medium">{t('citation_statutory_text', lang)}</span>
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-300 text-xs text-slate-700 leading-relaxed font-mono">
              &quot;{citation.exact_passage}&quot;
            </div>
          </div>

          <div className="p-3 rounded-xl bg-emerald-100 border border-emerald-300 text-[11px] text-emerald-800 flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 flex-shrink-0" />
            <span>{t('citation_verified', lang)}</span>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-emerald-200 text-xs">
          <span className="text-slate-500">{t('citation_authority_label', lang)} {citation.authority}</span>
          {citation.source_url && (
            <a
              href={citation.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1.5 text-emerald-600 hover:text-emerald-500 font-medium underline"
            >
              <span>{t('citation_view_gazette', lang)}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
