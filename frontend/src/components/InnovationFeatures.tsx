'use client';

import React, { useState } from 'react';
import {
  TrendingUp,
  Award,
  DollarSign,
  Handshake,
  Dna,
  Leaf,
  CheckCircle2,
  ExternalLink,
  Coins
} from 'lucide-react';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

export default function InnovationFeatures() {
  const { lang } = useLang();
  const [activeTab, setActiveTab] = useState<'grants' | 'cost' | 'dna' | 'sustainability' | 'commercialization'>('dna');

  const grants = [
    { name: 'BIRAC BIG (Biotechnology Ignition Grant)', agency: 'Department of Biotechnology (DBT)', maxGrant: '₹50 Lakhs', eligibilityKey: 'feature_grant_eligibility_1', matchScore: '94%' },
    { name: 'AYUSH Champions Scheme (Exports)', agency: 'Ministry of AYUSH', maxGrant: '₹1.5 Crores', eligibilityKey: 'feature_grant_eligibility_2', matchScore: '89%' },
    { name: 'DST NIDHI-PRAYAS (Proof of Concept)', agency: 'DST India', maxGrant: '₹10 Lakhs', eligibilityKey: 'feature_grant_eligibility_3', matchScore: '82%' }
  ];

  return (
    <div className="space-y-6">
      {/* Navigation Tabs */}
      <div className="flex items-center space-x-2 overflow-x-auto glass-panel p-1.5 rounded-2xl border border-emerald-200">
        <button
          onClick={() => setActiveTab('dna')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 whitespace-nowrap ${
            activeTab === 'dna' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/40' : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Dna className="w-3.5 h-3.5" />
          <span>{t('feature_tab_dna', lang)}</span>
        </button>

        <button
          onClick={() => setActiveTab('grants')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 whitespace-nowrap ${
            activeTab === 'grants' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/40' : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Award className="w-3.5 h-3.5" />
          <span>{t('feature_tab_grants', lang)}</span>
        </button>

        <button
          onClick={() => setActiveTab('cost')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 whitespace-nowrap ${
            activeTab === 'cost' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/40' : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Coins className="w-3.5 h-3.5" />
          <span>{t('feature_tab_cost', lang)}</span>
        </button>

        <button
          onClick={() => setActiveTab('sustainability')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 whitespace-nowrap ${
            activeTab === 'sustainability' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/40' : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Leaf className="w-3.5 h-3.5" />
          <span>{t('feature_tab_sustainability', lang)}</span>
        </button>
      </div>

      {/* DNA Score Card */}
      {activeTab === 'dna' && (
        <div className="glass-panel p-6 rounded-2xl border border-emerald-200 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">{t('feature_comprehensive_assessment', lang)}</span>
              <h4 className="text-xl font-bold text-slate-900 mt-0.5 font-display">{t('feature_dna_composite_index', lang)}</h4>
            </div>
            <div className="flex items-center space-x-3">
              <div className="text-right">
                <span className="text-xs text-slate-500 block font-medium">{t('feature_overall_dna_score', lang)}</span>
                <span className="text-2xl font-black text-emerald-600 font-display">88 / 100</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
              <span className="text-slate-500 font-medium block">{t('feature_dna_novelty', lang)}</span>
              <span className="text-lg font-bold text-emerald-600">82%</span>
              <div className="w-full bg-emerald-200 h-1 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full" style={{ width: '82%' }} />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
              <span className="text-slate-500 font-medium block">{t('feature_dna_regulatory_compliance', lang)}</span>
              <span className="text-lg font-bold text-emerald-600">95%</span>
              <div className="w-full bg-emerald-200 h-1 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full" style={{ width: '95%' }} />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
              <span className="text-slate-500 font-medium block">{t('feature_dna_evidence_completeness', lang)}</span>
              <span className="text-lg font-bold text-amber-600">76%</span>
              <div className="w-full bg-emerald-200 h-1 rounded-full overflow-hidden">
                <div className="bg-amber-500 h-full" style={{ width: '76%' }} />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
              <span className="text-slate-500 font-medium block">{t('feature_dna_export_readiness', lang)}</span>
              <span className="text-lg font-bold text-emerald-600">90%</span>
              <div className="w-full bg-emerald-200 h-1 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full" style={{ width: '90%' }} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Grant Matchmaker */}
      {activeTab === 'grants' && (
        <div className="glass-panel p-6 rounded-2xl border border-emerald-200 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-emerald-200">
            <div>
              <h4 className="text-base font-bold text-slate-900">{t('feature_grant_matchmaker_title', lang)}</h4>
              <p className="text-xs text-slate-500">{t('feature_grant_matchmaker_subtitle', lang)}</p>
            </div>
          </div>

          <div className="space-y-3">
            {grants.map((g, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="space-y-1 max-w-xl">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900 text-sm">{g.name}</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 text-[10px] font-mono border border-emerald-500/30">
                      {g.matchScore} {t('feature_grant_match', lang)}
                    </span>
                  </div>
                  <span className="text-slate-500 block">{g.agency} • {t('feature_grant_eligibility', lang)} {t(g.eligibilityKey, lang)}</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-500 block text-[10px] uppercase font-bold">{t('feature_grant_max', lang)}</span>
                  <span className="text-base font-extrabold text-amber-600 font-display">{g.maxGrant}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cost Estimator */}
      {activeTab === 'cost' && (
        <div className="glass-panel p-6 rounded-2xl border border-emerald-200 space-y-4 text-xs">
          <h4 className="text-base font-bold text-slate-900">{t('feature_cost_estimator_title', lang)}</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
              <strong className="text-slate-900 block">{t('feature_cost_india', lang)}</strong>
              <div className="text-xl font-bold text-emerald-600">₹28,500</div>
              <p className="text-slate-500">{t('feature_cost_india_desc', lang)}</p>
            </div>
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
              <strong className="text-slate-900 block">{t('feature_cost_us', lang)}</strong>
              <div className="text-xl font-bold text-cyan-600">$2,400 USD</div>
              <p className="text-slate-500">{t('feature_cost_us_desc', lang)}</p>
            </div>
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
              <strong className="text-slate-900 block">{t('feature_cost_canada', lang)}</strong>
              <div className="text-xl font-bold text-violet-600">$3,100 CAD</div>
              <p className="text-slate-500">{t('feature_cost_canada_desc', lang)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Sustainability */}
      {activeTab === 'sustainability' && (
        <div className="glass-panel p-6 rounded-2xl border border-emerald-200 space-y-4 text-xs">
          <h4 className="text-base font-bold text-slate-900">{t('feature_sustain_title', lang)}</h4>
          <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-500/30 text-emerald-700 space-y-2">
            <strong className="block text-emerald-700">{t('feature_sustain_zero_cites', lang)}</strong>
            <p className="leading-relaxed">
              {t('feature_sustain_desc', lang)}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
