'use client';

import React, { useState, useEffect } from 'react';
import { RegulatoryDiffRecord } from '../types';
import { getRegulatoryDiffs } from '../lib/api';
import { BellRing, ChevronRight, X, Sparkles } from 'lucide-react';

export default function RegulatoryDiffBanner() {
  const [updates, setUpdates] = useState<RegulatoryDiffRecord[]>([]);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    getRegulatoryDiffs().then(res => setUpdates(res)).catch(() => {});
  }, []);

  if (isDismissed || updates.length === 0) return null;

  const currentUpdate = updates[0];

  return (
    <div className="mb-6 p-4 rounded-2xl bg-blue-950/40 border border-blue-500/30 text-xs shadow-lg backdrop-blur-md">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="p-2 rounded-xl bg-blue-500/20 text-blue-400 mt-0.5">
            <BellRing className="w-4 h-4" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                Section 7.3.1 Living Regulatory-Diff Alert
              </span>
              <span className="text-slate-400 text-[11px]">{currentUpdate.new_version_date}</span>
            </div>
            <h4 className="font-semibold text-white">{currentUpdate.act_title}</h4>
            <p className="text-slate-300 leading-relaxed max-w-4xl">{currentUpdate.summary_of_change}</p>
            <div className="flex items-center space-x-2 pt-1 text-[11px] text-blue-300">
              <strong className="text-slate-400">Affected Provisions:</strong>
              <span>{currentUpdate.affected_provisions.join(' • ')}</span>
            </div>
          </div>
        </div>

        <button
          onClick={() => setIsDismissed(true)}
          className="p-1 rounded-lg text-slate-400 hover:text-white transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
