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
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-slate-900 font-display flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <span>Enterprise 3D Interactive Intelligence Cards</span>
        </h3>
        <span className="text-xs text-slate-500">Move cursor to tilt in 3D • Click 'Inspect Stat' to flip</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Patent Readiness */}
        <TiltCard
          glowColor="emerald"
          isFlippable
          backContent={
            <div className="space-y-2 text-xs">
              <span className="text-emerald-600 font-bold uppercase text-[10px]">Statutory Breakdown</span>
              <p className="text-slate-600">Indian Patents Act Section 3(p) clearance requires proving non-additive synergy.</p>
              <div className="p-2 rounded-lg bg-emerald-100/60 text-emerald-700 text-[11px] font-mono">
                IPO Form 1 Ready: 85%
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
                Active
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-medium block">Patent Readiness Index</span>
              <strong className="text-2xl font-black text-slate-900 font-display block">88 / 100</strong>
            </div>
            <p className="text-xs text-slate-600">Section 3(p) Traditional Knowledge pre-screened. Synergistic ratio verified.</p>
            <button
              onClick={() => onNavigateTab('matrix')}
              className="text-xs text-emerald-600 font-semibold flex items-center space-x-1 hover:underline pt-1"
            >
              <span>View Jurisdiction Matrix</span>
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
              <span className="text-cyan-600 font-bold uppercase text-[10px]">LangGraph Agents</span>
              <p className="text-slate-600">Coordinator Agent + Patent Agent + TKDL Agent + Regulatory Agent active in parallel.</p>
            </div>
          }
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-xl bg-cyan-100 text-cyan-600">
                <Bot className="w-5 h-5" />
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-cyan-100 text-cyan-700 border border-cyan-500/30">
                6 Agents Live
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-medium block">AI Multi-Agent Copilot</span>
              <strong className="text-2xl font-black text-slate-900 font-display block">IP-SAKTI Copilot</strong>
            </div>
            <p className="text-xs text-slate-600">Grounded strictly on primary statutory gazettes with zero hallucination rate.</p>
            <button
              onClick={() => onNavigateTab('copilot')}
              className="text-xs text-cyan-600 font-semibold flex items-center space-x-1 hover:underline pt-1"
            >
              <span>Trigger AI Agent Reasoner</span>
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
              <span className="text-amber-600 font-bold uppercase text-[10px]">Graph Connectivity</span>
              <p className="text-slate-600">Over 14,000+ API monograph entities linked with Charaka Samhita and FSSAI schedules.</p>
            </div>
          }
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-xl bg-amber-100 text-amber-600">
                <Network className="w-5 h-5" />
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-100 text-amber-700 border border-amber-500/30">
                Interactive
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-medium block">Knowledge Canvas</span>
              <strong className="text-2xl font-black text-slate-900 font-display block">9 Core Nodes</strong>
            </div>
            <p className="text-xs text-slate-600">Live relationship topology linking ingredients, patents, and regulations.</p>
            <button
              onClick={() => onNavigateTab('knowledge_graph')}
              className="text-xs text-amber-600 font-semibold flex items-center space-x-1 hover:underline pt-1"
            >
              <span>Explore Canvas Graph</span>
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
              <span className="text-violet-600 font-bold uppercase text-[10px]">Regulatory Sprints</span>
              <p className="text-slate-600">FSSAI Ayurveda Aahara approval projected in 45 days; NHP NPN in 60 days.</p>
            </div>
          }
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-xl bg-violet-100 text-violet-600">
                <Clock className="w-5 h-5" />
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-violet-100 text-violet-700 border border-violet-500/30">
                On Track
              </span>
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-medium block">Critical Path Timeline</span>
              <strong className="text-2xl font-black text-slate-900 font-display block">45 Days to Launch</strong>
            </div>
            <p className="text-xs text-slate-600">Milestone dependency scheduler for Indian & North American market entry.</p>
            <button
              onClick={() => onNavigateTab('flagship')}
              className="text-xs text-violet-600 font-semibold flex items-center space-x-1 hover:underline pt-1"
            >
              <span>Inspect Critical Path</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </TiltCard>
      </div>
    </div>
  );
}
