'use client';

import React from 'react';
import { ProvenanceGraphData, StatutoryCitation } from '../types';
import { ArrowRight, BookOpen, CheckCircle, Database, HelpCircle, ShieldAlert, Sparkles } from 'lucide-react';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface ProvenanceGraphProps {
  graphData: ProvenanceGraphData | null;
  onSelectCitation: (cite: StatutoryCitation) => void;
}

export default function ProvenanceGraph({
  graphData,
  onSelectCitation
}: ProvenanceGraphProps) {
  const { lang } = useLang();
  if (!graphData) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center border border-emerald-200">
        <p className="text-slate-500 text-sm">{t('pv_empty', lang)}</p>
      </div>
    );
  }

  const factNodes = graphData.nodes.filter(n => n.type === 'USER_FACT' || n.type === 'USER_CLAIM');
  const ruleNodes = graphData.nodes.filter(n => n.type === 'DETERMINISTIC_RULE');
  const citationNodes = graphData.nodes.filter(n => n.type === 'STATUTORY_CITATION');
  const findingNodes = graphData.nodes.filter(n => n.type === 'DECISION_FINDING');

  return (
    <div className="space-y-6">
      <div className="glass-panel rounded-2xl p-5 border border-emerald-200">
        <div className="flex items-center space-x-2.5 mb-1">
          <Sparkles className="w-5 h-5 text-emerald-600" />
          <h3 className="text-base font-bold text-slate-900 font-display">
            {t('pv_title', lang)}
          </h3>
        </div>
        <p className="text-xs text-slate-500">
          {t('pv_subtitle', lang)}
        </p>
      </div>

      {/* Visual Horizontal Provenance Flow */}
      <div className="glass-panel rounded-2xl p-6 border border-emerald-500/20 overflow-x-auto">
        <div className="flex items-stretch space-x-4 min-w-[760px]">
          {/* Column 1: User Facts */}
          <div className="flex-1 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-emerald-600 flex items-center space-x-1.5 pb-2 border-b border-emerald-200">
              <Database className="w-3.5 h-3.5" />
              <span>{t('pv_facts', lang)}</span>
            </div>
            {factNodes.map((node) => (
              <div key={node.id} className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-500/30 text-xs space-y-1">
                <span className="font-semibold text-slate-900 block">{node.label}</span>
                {node.details && <span className="text-[11px] text-slate-500 block">{node.details}</span>}
                <span className="inline-block mt-1 px-2 py-0.5 text-[9px] font-bold rounded bg-emerald-100 text-emerald-700">
                  {node.status || t('pv_confirmed', lang)}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-center text-slate-600">
            <ArrowRight className="w-5 h-5" />
          </div>

          {/* Column 2: Evaluated Rule Engine */}
          <div className="flex-1 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-amber-600 flex items-center space-x-1.5 pb-2 border-b border-emerald-200">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>{t('pv_rule', lang)}</span>
            </div>
            {ruleNodes.map((node) => (
              <div key={node.id} className="p-3.5 rounded-xl bg-emerald-50/70 border border-amber-500/30 text-xs space-y-2">
                <span className="font-semibold text-slate-900 block">{node.label}</span>
                <span className="text-[11px] text-amber-700/90 block">{t('pv_jurisdiction', lang)} {node.jurisdiction}</span>
                <span className="inline-block px-2 py-0.5 text-[9px] font-bold rounded bg-amber-100 text-amber-700">
                  {t('pv_condition', lang)} {node.condition_state}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-center text-slate-600">
            <ArrowRight className="w-5 h-5" />
          </div>

          {/* Column 3: Statutory Citations */}
          <div className="flex-1 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-blue-600 flex items-center space-x-1.5 pb-2 border-b border-emerald-200">
              <BookOpen className="w-3.5 h-3.5" />
              <span>{t('pv_gazette', lang)}</span>
            </div>
            {citationNodes.map((node) => (
              <div key={node.id} className="p-3.5 rounded-xl bg-emerald-50/70 border border-blue-500/30 text-xs space-y-2">
                <span className="font-semibold text-slate-900 block leading-snug">{node.label}</span>
                <p className="text-[10px] text-slate-600 font-mono italic line-clamp-3">
                  &quot;{node.passage_excerpt}&quot;
                </p>
                <div className="flex items-center justify-between text-[10px] text-blue-600 pt-1 border-t border-emerald-200">
                  <span>{node.effective_date}</span>
                  <span className="font-semibold">{node.authority}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-center text-slate-600">
            <ArrowRight className="w-5 h-5" />
          </div>

          {/* Column 4: Final Finding */}
          <div className="flex-1 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-violet-600 flex items-center space-x-1.5 pb-2 border-b border-emerald-200">
              <Sparkles className="w-3.5 h-3.5" />
              <span>{t('pv_finding', lang)}</span>
            </div>
            {findingNodes.map((node) => (
              <div key={node.id} className="p-3.5 rounded-xl bg-violet-100/70 border border-purple-500/40 text-xs space-y-2">
                <span className="font-semibold text-slate-900 block">{node.label}</span>
                <span className="inline-block px-2 py-0.5 text-[9px] font-bold rounded bg-violet-100 text-violet-700">
                  {t('pv_confidence', lang)} {node.confidence}
                </span>
                <span className="block text-[10px] text-slate-600">{t('pv_trail', lang)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
