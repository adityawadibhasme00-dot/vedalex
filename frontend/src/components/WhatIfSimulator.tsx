'use client';

import React, { useState } from 'react';
import { WhatIfSimulationResponse } from '../types';
import { Play, AlertTriangle, ArrowRight, CheckCircle2, ShieldAlert, Sparkles, RefreshCw } from 'lucide-react';

interface WhatIfSimulatorProps {
  passportId: string;
  onSimulate: (mutatedClaims: string[]) => void;
  simulationResult: WhatIfSimulationResponse | null;
  isLoading: boolean;
}

export default function WhatIfSimulator({
  passportId,
  onSimulate,
  simulationResult,
  isLoading
}: WhatIfSimulatorProps) {
  const [claimInput, setClaimInput] = useState('Treats chronic insomnia and eliminates sleep disorders');

  const presetOptions = [
    { label: 'Wellness: "Supports healthy sleep"', value: 'Supports healthy sleep and natural relaxation' },
    { label: 'Disease: "Treats chronic insomnia"', value: 'Treats chronic insomnia and eliminates sleep disorders' },
    { label: 'Anxiety: "Cures clinical stress & anxiety"', value: 'Cures clinical depression, panic attacks and anxiety' }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel rounded-2xl p-5 border border-emerald-200">
        <div className="flex items-center space-x-2.5 mb-1">
          <Sparkles className="w-5 h-5 text-amber-600" />
          <h3 className="text-base font-bold text-slate-900 font-display">
            Section 6.6 Live Reactive What-If Simulator
          </h3>
        </div>
        <p className="text-xs text-slate-500">
          Mutate promotional claims or formulation parameters live. The reactive dependency DAG recomputes only the affected classifier/rule nodes and highlights the precise compliance diff.
        </p>
      </div>

      {/* Editor & Diff Split Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Mutation Editor */}
        <div className="lg:col-span-5 glass-panel rounded-2xl p-5 border border-emerald-200 space-y-4">
          <h4 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
            1. Mutate Promotional Claim
          </h4>

          <div className="space-y-2">
            <label className="text-xs text-slate-500 font-medium">New Proposed Claim Wording:</label>
            <textarea
              rows={3}
              value={claimInput}
              onChange={(e) => setClaimInput(e.target.value)}
              className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-3 text-sm text-slate-800 placeholder-slate-500 focus:outline-none focus:border-amber-500/50 transition font-sans"
            />
          </div>

          <div className="space-y-2">
            <span className="text-[11px] text-slate-500 font-medium block">Quick Presets:</span>
            <div className="space-y-1.5">
              {presetOptions.map((opt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setClaimInput(opt.value)}
                  className="w-full text-left px-3 py-2 rounded-xl bg-emerald-50/70 hover:bg-emerald-100 border border-emerald-200 text-xs text-slate-600 transition truncate"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={() => onSimulate([claimInput])}
            disabled={isLoading}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white font-semibold text-xs flex items-center justify-center space-x-2 shadow-lg shadow-amber-900/30 transition disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Traversing Dependency Graph...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Simulate Downstream Impact</span>
              </>
            )}
          </button>
        </div>

        {/* Right: Live Reactive Diff Output */}
        <div className="lg:col-span-7 space-y-4">
          {simulationResult ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between glass-panel p-3.5 rounded-xl border border-emerald-200">
                <span className="text-xs text-slate-600">
                  Affected Dependency Nodes: <strong className="text-amber-600">{simulationResult.affected_nodes_count}</strong>
                </span>
                <span className="text-[11px] font-bold uppercase rounded px-2 py-0.5 bg-amber-100 text-amber-700 border border-amber-500/30">
                  Reactive Diff Generated
                </span>
              </div>

              {simulationResult.diffs.map((diff, dIdx) => (
                <div key={dIdx} className="glass-panel rounded-2xl p-5 border border-red-500/30 space-y-3.5 shadow-xl">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-xs font-bold uppercase text-slate-500">{diff.jurisdiction}</span>
                      <h4 className="text-base font-bold text-red-600 mt-0.5">
                        Shifted to: {diff.new_classification}
                      </h4>
                    </div>
                    <span className="px-2.5 py-1 text-[10px] font-bold uppercase rounded-full bg-red-100 text-red-700 border border-red-500/40">
                      {diff.impact_severity}
                    </span>
                  </div>

                  <div className="p-3 rounded-xl bg-red-100/70 border border-red-500/20 text-xs text-red-700 flex items-start space-x-2">
                    <ShieldAlert className="w-4 h-4 flex-shrink-0 text-red-600 mt-0.5" />
                    <span>{diff.risk_alert}</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
                    <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200">
                      <span className="text-slate-500 font-semibold block mb-1 text-[11px] uppercase">
                        Removed Requirements:
                      </span>
                      <ul className="space-y-1 text-slate-500">
                        {diff.removed_requirements.length > 0 ? (
                          diff.removed_requirements.map((r, i) => (
                            <li key={i} className="line-through text-slate-500">- {r}</li>
                          ))
                        ) : (
                          <li className="text-slate-500">None</li>
                        )}
                      </ul>
                    </div>

                    <div className="p-3 rounded-xl bg-emerald-50/70 border border-red-500/20">
                      <span className="text-red-700 font-semibold block mb-1 text-[11px] uppercase">
                        Newly Required Compliance:
                      </span>
                      <ul className="space-y-1 text-red-700">
                        {diff.new_requirements.map((r, i) => (
                          <li key={i} className="font-semibold text-red-700">+ {r}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="glass-panel rounded-2xl p-8 text-center border border-emerald-200 h-full flex flex-col items-center justify-center">
              <Sparkles className="w-8 h-8 text-slate-500 mb-2" />
              <p className="text-slate-500 text-xs">Run a simulation on the left to see reactive diffs appear here.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
