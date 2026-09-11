'use client';

import React, { useEffect, useState } from 'react';
import { getInstitutionalAnalytics } from '../lib/api';
import { Building2, Users, AlertCircle, CheckCircle, BarChart3 } from 'lucide-react';

export default function InstitutionalView() {
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getInstitutionalAnalytics()
      .then(res => setData(res))
      .catch(err => console.error(err))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center border border-emerald-200">
        <p className="text-slate-500 text-xs">Loading institutional incubator cohort analytics...</p>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel rounded-2xl p-5 border border-emerald-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Building2 className="w-5 h-5 text-emerald-600" />
            <h3 className="text-base font-bold text-slate-900 font-display">{data.organization_name}</h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Section 7.4.1 Multi-Tenant Incubator Dashboard & Aggregated Cohort Compliance Intelligence.
          </p>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          <div className="p-2.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-center">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Active Cases</span>
            <span className="text-sm font-bold text-slate-900">{data.total_active_cases}</span>
          </div>
          <div className="p-2.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-center">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Pending Reviews</span>
            <span className="text-sm font-bold text-amber-600">{data.pending_expert_reviews}</span>
          </div>
          <div className="p-2.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-center">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Avg Coverage</span>
            <span className="text-sm font-bold text-emerald-600">{data.avg_coverage_meter}%</span>
          </div>
        </div>
      </div>

      {/* Cohort Gaps & Bottlenecks */}
      <div className="glass-panel rounded-2xl p-5 border border-emerald-200 space-y-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-amber-600 flex items-center space-x-1.5">
          <BarChart3 className="w-4 h-4" />
          <span>Top Systemic Compliance Bottlenecks Across Cohort</span>
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {data.top_cohort_gaps.map((gap: any, idx: number) => (
            <div key={idx} className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
              <div className="flex items-start justify-between">
                <h5 className="text-xs font-bold text-slate-900 leading-snug">{gap.gap_title}</h5>
                <span className="text-xs font-extrabold text-amber-600 ml-2">{gap.percentage}%</span>
              </div>
              <div className="w-full bg-emerald-200 h-1.5 rounded-full overflow-hidden">
                <div className="bg-amber-500 h-full" style={{ width: `${gap.percentage}%` }} />
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed pt-1 border-t border-emerald-200">
                <strong className="text-slate-700">Policy Action: </strong>{gap.recommended_workshop_action}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Startup Case Queue */}
      <div className="glass-panel rounded-2xl p-5 border border-emerald-200 space-y-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
          Incubator Case Queue & Triage Status
        </h4>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="border-b border-emerald-200 text-slate-500 uppercase text-[10px]">
              <tr>
                <th className="pb-2.5">Case / Startup</th>
                <th className="pb-2.5">Product Formulation</th>
                <th className="pb-2.5">Target Markets</th>
                <th className="pb-2.5">Coverage</th>
                <th className="pb-2.5">Assigned Reviewer</th>
                <th className="pb-2.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-emerald-200">
              {data.cases.map((c: any) => (
                <tr key={c.case_id} className="hover:bg-emerald-50/70 transition">
                  <td className="py-3">
                    <span className="font-semibold text-slate-900 block">{c.startup_name}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{c.case_id}</span>
                  </td>
                  <td className="py-3">{c.product_name}</td>
                  <td className="py-3">
                    <div className="flex space-x-1">
                      {c.target_markets.map((m: string) => (
                        <span key={m} className="px-1.5 py-0.5 rounded bg-emerald-100/60 text-[10px] text-slate-600">
                          {m}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3">
                    <span className="font-bold text-emerald-600">{c.coverage_meter}%</span>
                  </td>
                  <td className="py-3 text-slate-500">{c.assigned_reviewer}</td>
                  <td className="py-3">
                    <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-500/30 text-[10px] font-medium">
                      {c.current_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
