'use client';

import React from 'react';
import TiltCard from './TiltCard';
import {
  ShieldCheck,
  Bot,
  Network,
  Clock,
  Dna,
  Radar,
  Leaf,
  TrendingUp,
  ArrowRight,
  Sparkles,
  Zap,
  CheckCircle2
} from 'lucide-react';
import { InnovationPassport, RegulatoryFinding } from '../types';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface Dashboard3DCardsProps {
  passport: InnovationPassport | null;
  findings: RegulatoryFinding[];
  onNavigateTab: (tabId: string) => void;
}

export default function Dashboard3DCards({
  passport,
  findings,
  onNavigateTab
}: Dashboard3DCardsProps) {
  const { lang } = useLang();
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-slate-900 font-display flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <span>{t('c3_title', lang)}</span>
        </h3>
        <span className="text-xs text-slate-500">{t('c3_hint', lang)}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Patent Readiness */}
        <TiltCard
          glowColor="emerald"
          isFlippable
          backContent={
            <div className="space-y-2 text-xs">
              <span className="text-emerald-600 font-bold uppercase text-[10px]">{t('c3_statutory', lang)}</span>
              <p className="text-slate-600">{t('c3_sec3p', lang)}</p>
              <div className="p-2 rounded-lg bg-emerald-100/60 text-emerald-700 text-[11px] font-mono">
                {t('c3_form1', lang)}
              </div>
            </div>
          }
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-xl bg-emerald-100 text-emerald-600">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-100 text-emerald-700 border border-emerald-500/30">
                {t('c3_active', lang)}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-medium block">{t('c3_pri', lang)}</span>
              <strong className="text-2xl font-black text-slate-900 font-display block">88 / 100</strong>
            </div>
            <p className="text-xs text-slate-600">{t('c3_pri_desc', lang)}</p>
            <button
              onClick={() => onNavigateTab('matrix')}
              className="text-xs text-emerald-600 font-semibold flex items-center space-x-1 hover:underline pt-1"
            >
              <span>{t('c3_view_matrix', lang)}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </TiltCard>

        {/* Card 2: AI Multi-Agent Copilot */}
        <TiltCard
          glowColor="cyan"
          isFlippable
          backContent={
            <div className="space-y-2 text-xs">
              <span className="text-cyan-600 font-bold uppercase text-[10px]">{t('c3_langgraph', lang)}</span>
              <p className="text-slate-600">{t('c3_agents_desc', lang)}</p>
            </div>
          }
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-xl bg-cyan-100 text-cyan-600">
                <Bot className="w-5 h-5" />
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-cyan-100 text-cyan-700 border border-cyan-500/30">
                {t('c3_6agents', lang)}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-medium block">{t('c3_copilot', lang)}</span>
              <strong className="text-2xl font-black text-slate-900 font-display block">IP-SAKTI Copilot</strong>
            </div>
            <p className="text-xs text-slate-600">{t('c3_copilot_desc', lang)}</p>
            <button
              onClick={() => onNavigateTab('copilot')}
              className="text-xs text-cyan-600 font-semibold flex items-center space-x-1 hover:underline pt-1"
            >
              <span>{t('c3_trigger', lang)}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </TiltCard>

        {/* Card 3: Interactive Knowledge Graph */}
        <TiltCard
          glowColor="gold"
          isFlippable
          backContent={
            <div className="space-y-2 text-xs">
              <span className="text-amber-600 font-bold uppercase text-[10px]">{t('c3_graph_conn', lang)}</span>
              <p className="text-slate-600">{t('c3_graph_desc', lang)}</p>
            </div>
          }
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-xl bg-amber-100 text-amber-600">
                <Network className="w-5 h-5" />
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-100 text-amber-700 border border-amber-500/30">
                {t('c3_interactive', lang)}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-medium block">{t('c3_canvas', lang)}</span>
              <strong className="text-2xl font-black text-slate-900 font-display block">9 Core Nodes</strong>
            </div>
            <p className="text-xs text-slate-600">{t('c3_canvas_desc', lang)}</p>
            <button
              onClick={() => onNavigateTab('knowledge_graph')}
              className="text-xs text-amber-600 font-semibold flex items-center space-x-1 hover:underline pt-1"
            >
              <span>{t('c3_explore', lang)}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </TiltCard>

        {/* Card 4: Innovation Timeline */}
        <TiltCard
          glowColor="purple"
          isFlippable
          backContent={
            <div className="space-y-2 text-xs">
              <span className="text-violet-600 font-bold uppercase text-[10px]">{t('c3_sprints', lang)}</span>
              <p className="text-slate-600">{t('c3_sprints_desc', lang)}</p>
            </div>
          }
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-xl bg-violet-100 text-violet-600">
                <Clock className="w-5 h-5" />
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-violet-100 text-violet-700 border border-violet-500/30">
                {t('c3_on_track', lang)}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-medium block">{t('c3_critical', lang)}</span>
              <strong className="text-2xl font-black text-slate-900 font-display block">{t('c3_45days', lang)}</strong>
            </div>
            <p className="text-xs text-slate-600">{t('c3_critical_desc', lang)}</p>
            <button
              onClick={() => onNavigateTab('flagship')}
              className="text-xs text-violet-600 font-semibold flex items-center space-x-1 hover:underline pt-1"
            >
              <span>{t('c3_inspect', lang)}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </TiltCard>
      </div>
    </div>
  );
}
