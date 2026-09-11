'use client';

import React from 'react';
import { RedTeamResult } from '../types';
import { ShieldAlert, AlertTriangle, X, CheckSquare, Sparkles } from 'lucide-react';

interface RedTeamModalProps {
  isOpen: boolean;
  onClose: () => void;
  redTeamResult: RedTeamResult | null;
  isLoading: boolean;
  onRunChallenge: () => void;
}

export default function RedTeamModal({
  isOpen,
  onClose,
  redTeamResult,
  isLoading,
  onRunChallenge
}: RedTeamModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel max-w-2xl w-full rounded-2xl p-6 border border-red-500/30 shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-emerald-200 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-red-100 text-red-600">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-red-600">
                Section 6.7 Pre-Filing Objections Simulator
              </span>
              <h3 className="text-lg font-bold text-slate-900 font-display">
                "Challenge My Innovation" (Patent Examiner Red-Team)
              </h3>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-emerald-50 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Objections List */}
        <div className="overflow-y-auto my-4 space-y-4 pr-1 flex-1">
          {redTeamResult ? (
            <>
              <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-slate-600 italic">
                {redTeamResult.disclaimer}
              </div>

              {redTeamResult.objections.map((obj, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-emerald-50/70 border border-red-300 space-y-2.5">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-bold uppercase text-red-600 block">{obj.authority_simulated}</span>
                      <h4 className="text-sm font-bold text-slate-900 mt-0.5">{obj.objection_title}</h4>
                    </div>
                    <span className="px-2 py-0.5 text-[9px] font-mono rounded bg-red-100 text-red-700 border border-red-300">
                      {obj.legal_basis}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed font-sans">
                    {obj.summary}
                  </p>

                  <div className="p-3 rounded-xl bg-emerald-100 border border-emerald-300 text-xs text-emerald-800 flex items-start space-x-2">
                    <CheckSquare className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="block text-emerald-700">Recommended Investigable Pre-Filing Action:</strong>
                      <span>{obj.investigable_action}</span>
                    </div>
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs">
              Click the button below to simulate examiner objections against your current Innovation Passport.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-emerald-200 flex items-center justify-between flex-shrink-0">
          <span className="text-xs text-slate-500">Total Objections Simulated: {redTeamResult?.total_objections || 0}</span>
          <button
            onClick={onRunChallenge}
            disabled={isLoading}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white font-semibold text-xs transition disabled:opacity-50 flex items-center space-x-1.5 shadow-lg shadow-red-900/30"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isLoading ? 'Simulating Objections...' : 'Run Red-Team Challenge'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
