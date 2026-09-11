'use client';

import React from 'react';
import { EvidenceGapSummary, EvidenceItem } from '../types';
import { CheckCircle2, Clock, Upload, AlertCircle, FileCheck, ArrowRight } from 'lucide-react';

interface EvidenceGapListProps {
  evidenceSummary: EvidenceGapSummary | null;
  onUpdateStatus: (itemId: string, newStatus: string) => void;
  isLoading: boolean;
}

export default function EvidenceGapList({
  evidenceSummary,
  onUpdateStatus,
  isLoading
}: EvidenceGapListProps) {
  if (!evidenceSummary) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center border border-emerald-200">
        <p className="text-slate-500 text-sm">No evidence checklist loaded. Generate an assessment to view requirements.</p>
      </div>
    );
  }

  const renderStatusPill = (status: string) => {
    switch (status) {
      case 'Accepted for this assessment':
        return <span className="px-2.5 py-1 text-[10px] font-bold uppercase rounded-full bg-emerald-100 text-emerald-700 border border-emerald-300">Accepted</span>;
      case 'Needs review':
        return <span className="px-2.5 py-1 text-[10px] font-bold uppercase rounded-full bg-blue-100 text-blue-700 border border-blue-300">Needs Review</span>;
      case 'Uploaded':
        return <span className="px-2.5 py-1 text-[10px] font-bold uppercase rounded-full bg-violet-100 text-violet-700 border border-violet-300">Uploaded</span>;
      default:
        return <span className="px-2.5 py-1 text-[10px] font-bold uppercase rounded-full bg-red-100 text-red-700 border border-red-300">Missing Evidence</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Coverage Meter */}
      <div className="glass-panel rounded-2xl p-5 border border-emerald-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 font-display">
            Section 6.5 Evidence-Gap Analysis & Action Plan
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Requirements follow a strict lifecycle (Missing ➔ Uploaded ➔ Needs review ➔ Accepted).
          </p>
        </div>

        {/* Coverage Meter Card */}
        <div className="flex items-center space-x-3 bg-emerald-50/70 border border-emerald-500/30 rounded-2xl p-3.5 px-4 shadow-lg">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-500 block">Case Coverage Meter</span>
            <span className="text-xs text-emerald-600 font-medium">
              {evidenceSummary.evaluated_checks} of {evidenceSummary.total_checks} requirements evaluated
            </span>
          </div>
          <div className="text-xl font-extrabold text-emerald-600 font-display">
            {evidenceSummary.coverage_meter_percentage}%
          </div>
        </div>
      </div>

      {/* Dependency Ordered Checklist */}
      <div className="space-y-3.5">
        {evidenceSummary.items.map((item) => (
          <div
            key={item.id}
            className="glass-panel rounded-2xl p-5 border border-emerald-200 hover:border-emerald-500/30 transition space-y-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50/70 text-slate-500">
                    {item.id} • {item.jurisdiction}
                  </span>
                  <span className="text-xs text-slate-500 font-medium">({item.expected_evidence_type})</span>
                </div>
                <h4 className="text-sm font-bold text-slate-900 mt-1">{item.requirement_name}</h4>
              </div>
              <div className="flex items-center space-x-2">
                {renderStatusPill(item.status)}
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              <strong className="text-slate-500 font-medium">Why it applies: </strong>
              {item.why_it_applies}
            </p>

            <div className="flex flex-wrap items-center justify-between pt-2 border-t border-emerald-200 gap-2 text-xs">
              <div className="flex items-center space-x-1.5 text-amber-700/90 font-medium">
                <ArrowRight className="w-3.5 h-3.5 text-amber-600" />
                <span>Next Action: {item.next_action}</span>
              </div>

              {/* Status transition dropdown */}
              <div className="flex items-center space-x-2">
                <span className="text-[11px] text-slate-500">Update Lifecycle:</span>
                <select
                  value={item.status}
                  onChange={(e) => onUpdateStatus(item.id, e.target.value)}
                  className="bg-emerald-50/70 border border-emerald-200 rounded-lg text-xs text-slate-700 px-2 py-1 focus:outline-none focus:border-emerald-500"
                >
                  <option value="Missing">Missing</option>
                  <option value="Uploaded">Uploaded</option>
                  <option value="Needs review">Needs review</option>
                  <option value="Accepted for this assessment">Accepted for assessment</option>
                </select>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
