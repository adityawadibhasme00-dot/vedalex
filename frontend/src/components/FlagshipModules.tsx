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
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

export default function FlagshipModules() {
  const { lang } = useLang();
  const [activeModule, setActiveModule] = useState<string>('f_fto');

  const flagshipList = [
    { id: 'f_sentinel', titleKey: 'module_sentinel_title', icon: ShieldAlert, categoryKey: 'module_cat_ip_defense' },
    { id: 'f_fto', titleKey: 'module_fto_title_short', icon: Compass, categoryKey: 'module_cat_ip_clearance' },
    { id: 'f_firewall', titleKey: 'module_firewall_title_short', icon: FileCheck2, categoryKey: 'module_cat_regulatory' },
    { id: 'f_path', titleKey: 'module_path_title', icon: GitMerge, categoryKey: 'module_cat_roadmap' },
    { id: 'f_hierarchy', titleKey: 'module_hierarchy_title', icon: Scale, categoryKey: 'module_cat_source_rank' },
    { id: 'f_abs', titleKey: 'module_abs_title_short', icon: TreePine, categoryKey: 'module_cat_biodiversity' },
    { id: 'f_delta', titleKey: 'module_delta_title', icon: SlidersHorizontal, categoryKey: 'module_cat_formulation' },
    { id: 'f_matrix', titleKey: 'evidence_matrix', icon: Table2, categoryKey: 'module_cat_evidence' },
    { id: 'f_autopilot', titleKey: 'module_autopilot_title_short', icon: FileSpreadsheet, categoryKey: 'module_cat_filing' },
    { id: 'f_inventorship', titleKey: 'module_inventorship_title', icon: Users2, categoryKey: 'module_cat_ownership' },
    { id: 'f_whitespace', titleKey: 'module_whitespace_title', icon: Sparkles, categoryKey: 'module_cat_discovery' },
    { id: 'f_audit', titleKey: 'module_audit_title', icon: History, categoryKey: 'module_cat_compliance' },
    { id: 'f_safety', titleKey: 'module_safety_title', icon: Activity, categoryKey: 'module_cat_vigilance' },
    { id: 'f_escalation', titleKey: 'module_escalation_title', icon: UserCheck, categoryKey: 'module_cat_handoff' }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel p-5 rounded-2xl border border-emerald-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 font-display">
            {t('module_suite_title', lang)}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {t('module_suite_subtitle', lang)}
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
                  <span className="truncate">{t(mod.titleKey, lang)}</span>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${isActive ? 'bg-emerald-700 text-emerald-100' : 'bg-emerald-50 text-slate-500'}`}>
                  {t(mod.categoryKey, lang)}
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
                  <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">{t('module_fto_badge', lang)}</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">{t('module_fto_heading', lang)}</h4>
                </div>
                <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-100 text-emerald-700 border border-emerald-500/30">
                  {t('module_fto_risk_badge', lang)}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-500/20 space-y-1">
                  <span className="text-slate-500 font-medium block">{t('module_fto_india_label', lang)}</span>
                  <strong className="text-emerald-600 text-sm block">{t('module_fto_india_value', lang)}</strong>
                  <p className="text-[11px] text-slate-500">{t('module_fto_india_desc', lang)}</p>
                </div>
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-amber-500/20 space-y-1">
                  <span className="text-slate-500 font-medium block">{t('module_fto_us_label', lang)}</span>
                  <strong className="text-amber-600 text-sm block">{t('module_fto_us_value', lang)}</strong>
                  <p className="text-[11px] text-slate-500">{t('module_fto_us_desc', lang)}</p>
                </div>
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-500/20 space-y-1">
                  <span className="text-slate-500 font-medium block">{t('module_fto_ca_label', lang)}</span>
                  <strong className="text-emerald-600 text-sm block">{t('module_fto_ca_value', lang)}</strong>
                  <p className="text-[11px] text-slate-500">{t('module_fto_ca_desc', lang)}</p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs space-y-2">
                <span className="font-semibold text-slate-700 block">{t('module_fto_recommendation_label', lang)}</span>
                <p className="text-slate-500 leading-relaxed">
                  {t('module_fto_recommendation', lang)}
                </p>
              </div>
            </div>
          )}

          {activeModule === 'f_sentinel' && (
            <div className="space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-emerald-200">
                <div>
                  <span className="text-[10px] font-bold uppercase text-red-600 tracking-wider">{t('module_sentinel_badge', lang)}</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">{t('module_sentinel_heading', lang)}</h4>
                </div>
                <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-red-100 text-red-700 border border-red-500/30">
                  {t('module_sentinel_shield', lang)}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-red-50/70 border border-red-500/20 text-xs text-red-700 flex items-start space-x-2.5">
                <ShieldAlert className="w-5 h-5 flex-shrink-0 text-red-600 mt-0.5" />
                <div>
                  <strong className="block text-red-700">{t('module_sentinel_warning_label', lang)}</strong>
                  <span>{t('module_sentinel_warning_body', lang)}</span>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <span className="font-bold uppercase text-slate-500 block">{t('module_sentinel_checkpoints', lang)}</span>
                <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
                  <span>{t('module_sentinel_nda', lang)}</span>
                  <span className="text-emerald-600 font-bold">{t('module_verified', lang)}</span>
                </div>
                <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
                  <span>{t('module_sentinel_embargo', lang)}</span>
                  <span className="text-emerald-600 font-bold">{t('module_verified', lang)}</span>
                </div>
              </div>
            </div>
          )}

          {activeModule === 'f_firewall' && (
            <div className="space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-emerald-200">
                <div>
                  <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">{t('module_firewall_badge', lang)}</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">{t('module_firewall_heading', lang)}</h4>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-red-50/70 border border-red-500/30">
                    <span className="text-[10px] font-bold uppercase text-red-600 block mb-1">{t('module_firewall_disallowed', lang)}</span>
                    <ul className="space-y-1 text-red-700">
                      <li>{t('module_firewall_bad_1', lang)}</li>
                      <li>{t('module_firewall_bad_2', lang)}</li>
                    </ul>
                  </div>
                  <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-500/30">
                    <span className="text-[10px] font-bold uppercase text-emerald-600 block mb-1">{t('module_firewall_permitted', lang)}</span>
                    <ul className="space-y-1 text-emerald-700">
                      <li>{t('module_firewall_ok_1', lang)}</li>
                      <li>{t('module_firewall_ok_2', lang)}</li>
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
                  <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">{t('module_abs_badge', lang)}</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">{t('module_abs_heading', lang)}</h4>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-500/30 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <strong className="text-slate-900">{t('module_abs_status_label', lang)}</strong>
                  <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 border border-emerald-500/30 font-mono">
                    {t('module_abs_status_value', lang)}
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  {t('module_abs_desc', lang)}
                </p>
              </div>
            </div>
          )}

          {activeModule === 'f_autopilot' && (
            <div className="space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-emerald-200">
                <div>
                  <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">{t('module_autopilot_badge', lang)}</span>
                  <h4 className="text-lg font-bold text-slate-900 mt-0.5">{t('module_autopilot_heading', lang)}</h4>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
                  <strong className="text-slate-900 block">{t('module_autopilot_india', lang)}</strong>
                  <p className="text-slate-500">{t('module_autopilot_india_desc', lang)}</p>
                  <button className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1">
                    <Download className="w-3.5 h-3.5" />
                    <span>{t('module_autopilot_india_cta', lang)}</span>
                  </button>
                </div>

                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
                  <strong className="text-slate-900 block">{t('module_autopilot_canada', lang)}</strong>
                  <p className="text-slate-500">{t('module_autopilot_canada_desc', lang)}</p>
                  <button className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1">
                    <Download className="w-3.5 h-3.5" />
                    <span>{t('module_autopilot_canada_cta', lang)}</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Other Modules Fallback */}
          {!['f_fto', 'f_sentinel', 'f_firewall', 'f_abs', 'f_autopilot'].includes(activeModule) && (
            <div className="space-y-4">
              <h4 className="text-base font-bold text-slate-900">
                {t(flagshipList.find(m => m.id === activeModule)?.titleKey || '', lang)}
              </h4>
              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-slate-600 space-y-2">
                <p>{t('module_generic_desc', lang)}</p>
                <div className="p-3 rounded-xl bg-emerald-100/50 border border-emerald-500/20 text-emerald-700 font-mono text-[11px]">
                  {t('module_generic_status', lang)}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
