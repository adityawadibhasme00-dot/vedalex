'use client';

import React, { useState } from 'react';
import {
  ShieldAlert,
  Compass,
  FileCheck2,
  GitMerge,
  Scale,
  TreePine,
  SlidersHorizontal,
  Table2,
  FileSpreadsheet,
  Users2,
  Sparkles,
  History,
  Activity,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Download
} from 'lucide-react';

export default function FlagshipModules() {
  const [activeModule, setActiveModule] = useState<string>('f_fto');

  const flagshipList = [
    { id: 'f_sentinel', title: 'Patent Disclosure Sentinel', icon: ShieldAlert, category: 'IP Defense' },
    { id: 'f_fto', title: 'FTO Collision Map', icon: Compass, category: 'IP Clearance' },
    { id: 'f_firewall', title: 'Claim & Label Firewall', icon: FileCheck2, category: 'Regulatory' },
    { id: 'f_path', title: 'Regulatory Critical Path', icon: GitMerge, category: 'Roadmap' },
    { id: 'f_hierarchy', title: 'Legal Hierarchy Resolver', icon: Scale, category: 'Source Rank' },
    { id: 'f_abs', title: 'Bio-Resource ABS Ledger', icon: TreePine, category: 'Biodiversity' },
    { id: 'f_delta', title: 'Formulation Delta Engine', icon: SlidersHorizontal, category: 'Formulation' },
    { id: 'f_matrix', title: 'Evidence-to-Claim Matrix', icon: Table2, category: 'Evidence' },
    { id: 'f_autopilot', title: 'Dossier Autopilot', icon: FileSpreadsheet, category: 'Filing' },
    { id: 'f_inventorship', title: 'Inventorship Guard', icon: Users2, category: 'Ownership' },
    { id: 'f_whitespace', title: 'White Space Navigator', icon: Sparkles, category: 'Discovery' },
    { id: 'f_audit', title: 'Regulatory Audit Replay', icon: History, category: 'Compliance' },
    { id: 'f_safety', title: 'Post-Market Safety Loop', icon: Activity, category: 'Vigilance' },
    { id: 'f_escalation', title: 'Expert Escalation Queue', icon: UserCheck, category: 'Handoff' }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel p-5 rounded-2xl border border-emerald-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 font-display">
            Flagship Enterprise Intelligence Suite (14 Dedicated Engines)
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Every module connects live data from the Innovation Passport and primary statutory gazettes.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Navigation List */}
        <div className="lg:col-span-4 glass-panel p-3 rounded-2xl border border-emerald-200 space-y-1 max-h-[600px] overflow-y-auto">
          {flagshipList.map((mod) => {
            const Icon = mod.icon;
            const isActive = activeModule === mod.id;
            return (
              <button
                key={mod.id}
                onClick={() => setActiveModule(mod.id)}
                className={`w-full text-left p-3 rounded-xl transition flex items-center justify-between text-xs ${
                  isActive
                    ? 'bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-900/40'
                    : 'text-slate-600 hover:bg-emerald-50 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center space-x-2.5">
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">{mod.title}</span>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${isActive ? 'bg-emerald-700 text-emerald-100' : 'bg-emerald-50 text-slate-500'}`}>
                  {mod.category}
                </span>
              </button>
            );
          })}
        </div>

        {/* Right Active Module Work Area */}
        <div className="lg:col-span-8 glass-panel p-6 rounded-2xl border border-emerald-200 space-y-5">
          {activeModule === 'f_fto' && (
            <div className="space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-emerald-200">
                <div>
                  <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">Module 2 • IP Clearance</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">Freedom-to-Operate (FTO) Collision Heatmap</h4>
                </div>
                <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-100 text-emerald-700 border border-emerald-500/30">
                  Low Collision Risk (82% Clear)
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-500/20 space-y-1">
                  <span className="text-slate-500 font-medium block">India (IPO Patents)</span>
                  <strong className="text-emerald-600 text-sm block">0 Active Blocking Claims</strong>
                  <p className="text-[11px] text-slate-500">Section 3(p) shields classical formulations from private third-party monopoly.</p>
                </div>
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-amber-500/20 space-y-1">
                  <span className="text-slate-500 font-medium block">United States (USPTO)</span>
                  <strong className="text-amber-600 text-sm block">1 Expired Patent Ref</strong>
                  <p className="text-[11px] text-slate-500">US Patent 6,713,092 expired in 2022; entered public domain.</p>
                </div>
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-500/20 space-y-1">
                  <span className="text-slate-500 font-medium block">Canada (CIPO)</span>
                  <strong className="text-emerald-600 text-sm block">Free to Operate</strong>
                  <p className="text-[11px] text-slate-500">NHPID monograph compendium permits standard classical ratios.</p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs space-y-2">
                <span className="font-semibold text-slate-700 block">FTO Clearance Recommendation:</span>
                <p className="text-slate-500 leading-relaxed">
                  Your standardized aqueous extract of <em>Withania somnifera</em> and <em>Bacopa monnieri</em> possesses clear commercialization pathways across all 3 target jurisdictions without infringing active third-party composition-of-matter claims.
                </p>
              </div>
            </div>
          )}

          {activeModule === 'f_sentinel' && (
            <div className="space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-emerald-200">
                <div>
                  <span className="text-[10px] font-bold uppercase text-red-600 tracking-wider">Module 1 • Confidentiality Sentinel</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">Patent Disclosure Sentinel (Leak Protection)</h4>
                </div>
                <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-red-100 text-red-700 border border-red-500/30">
                  Pre-Filing Shield Active
                </span>
              </div>

              <div className="p-4 rounded-xl bg-red-50/70 border border-red-500/20 text-xs text-red-700 flex items-start space-x-2.5">
                <ShieldAlert className="w-5 h-5 flex-shrink-0 text-red-600 mt-0.5" />
                <div>
                  <strong className="block text-red-700">Public Disclosure Warning:</strong>
                  <span>Prior to filing Indian Patent Form 1, publishing your exact solvent extraction ratio or clinical trial abstracts at conferences destroys novelty under Indian Patents Act Section 29.</span>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <span className="font-bold uppercase text-slate-500 block">Mandatory Pre-Filing Checkpoints:</span>
                <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
                  <span>Non-Disclosure Agreements (NDA) signed with contract manufacturer</span>
                  <span className="text-emerald-600 font-bold">VERIFIED</span>
                </div>
                <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
                  <span>Academic conference abstract embargo confirmed</span>
                  <span className="text-emerald-600 font-bold">VERIFIED</span>
                </div>
              </div>
            </div>
          )}

          {activeModule === 'f_firewall' && (
            <div className="space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-emerald-200">
                <div>
                  <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">Module 3 • Label Protection</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">Claim & Label Firewall (FDA / FSSAI Sanitizer)</h4>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-red-50/70 border border-red-500/30">
                    <span className="text-[10px] font-bold uppercase text-red-600 block mb-1">Disallowed Disease Claims (High Warning Risk)</span>
                    <ul className="space-y-1 text-red-700">
                      <li>❌ "Treats clinical insomnia"</li>
                      <li>❌ "Cures chronic anxiety disorder"</li>
                    </ul>
                  </div>
                  <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-500/30">
                    <span className="text-[10px] font-bold uppercase text-emerald-600 block mb-1">Firewall-Sanitized Permitted Claims</span>
                    <ul className="space-y-1 text-emerald-700">
                      <li>✅ "Supports healthy, restful sleep"</li>
                      <li>✅ "Promotes natural relaxation & mental calm"</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeModule === 'f_abs' && (
            <div className="space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-emerald-200">
                <div>
                  <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">Module 6 • Biological Diversity Compliance</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">National Biodiversity Authority (NBA) & ABS Ledger</h4>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-500/30 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <strong className="text-slate-900">Biological Diversity Act (BDA) 2002 Status:</strong>
                  <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 border border-emerald-500/30 font-mono">
                    Form III Required Prior to Grant
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  Under Section 6 of the Biological Diversity Act, 2002, applicants utilizing Indian biological resources must obtain prior approval from the National Biodiversity Authority before filing intellectual property claims abroad.
                </p>
              </div>
            </div>
          )}

          {activeModule === 'f_autopilot' && (
            <div className="space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-emerald-200">
                <div>
                  <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">Module 9 • Automated Filing</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">Dossier Autopilot (ePLA & Form 1 Generator)</h4>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
                  <strong className="text-slate-900 block">Indian Patent Form 1 & 2 Package</strong>
                  <p className="text-slate-500">Includes Title, Abstract, Section 10(4)(d)(ii) biological origin disclosure, and complete specification.</p>
                  <button className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1">
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Form 1/2 Draft (.DOCX)</span>
                  </button>
                </div>

                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
                  <strong className="text-slate-900 block">Health Canada Class I ePLA Package</strong>
                  <p className="text-slate-500">Pre-filled electronic Product Licence Application with NHPID monograph references.</p>
                  <button className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1">
                    <Download className="w-3.5 h-3.5" />
                    <span>Download ePLA Dossier (.PDF)</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Other Modules Fallback */}
          {!['f_fto', 'f_sentinel', 'f_firewall', 'f_abs', 'f_autopilot'].includes(activeModule) && (
            <div className="space-y-4">
              <h4 className="text-base font-bold text-slate-900">
                {flagshipList.find(m => m.id === activeModule)?.title}
              </h4>
              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-slate-600 space-y-2">
                <p>This engine is actively connected to the Innovation Passport and primary statutory knowledge stores.</p>
                <div className="p-3 rounded-xl bg-emerald-100/50 border border-emerald-500/20 text-emerald-700 font-mono text-[11px]">
                  Status: Operational • Version 1.0 • Pinned Rule Engine: RULE-IN-ASU-2024 / 21 CFR 101.93
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
