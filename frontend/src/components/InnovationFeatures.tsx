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

export default function InnovationFeatures() {
  const [activeTab, setActiveTab] = useState<'grants' | 'cost' | 'dna' | 'sustainability' | 'commercialization'>('dna');

  const grants = [
    { name: 'BIRAC BIG (Biotechnology Ignition Grant)', agency: 'Department of Biotechnology (DBT)', maxGrant: '₹50 Lakhs', eligibility: 'Early-stage Ayurveda biotech MSMEs & Researchers', matchScore: '94%' },
    { name: 'AYUSH Champions Scheme (Exports)', agency: 'Ministry of AYUSH', maxGrant: '₹1.5 Crores', eligibility: 'Ayurveda MSMEs targeting US FDA & Health Canada export', matchScore: '89%' },
    { name: 'DST NIDHI-PRAYAS (Proof of Concept)', agency: 'DST India', maxGrant: '₹10 Lakhs', eligibility: 'Formulation innovators converting ancient recipes into modern dosage forms', matchScore: '82%' }
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
          <span>Innovation DNA Score</span>
        </button>

        <button
          onClick={() => setActiveTab('grants')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 whitespace-nowrap ${
            activeTab === 'grants' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/40' : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Award className="w-3.5 h-3.5" />
          <span>AI Grant Matchmaker</span>
        </button>

        <button
          onClick={() => setActiveTab('cost')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 whitespace-nowrap ${
            activeTab === 'cost' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/40' : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Coins className="w-3.5 h-3.5" />
          <span>Patent & Filing Cost Estimator</span>
        </button>

        <button
          onClick={() => setActiveTab('sustainability')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 whitespace-nowrap ${
            activeTab === 'sustainability' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/40' : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <Leaf className="w-3.5 h-3.5" />
          <span>Sustainability & ABS Card</span>
        </button>
      </div>

      {/* DNA Score Card */}
      {activeTab === 'dna' && (
        <div className="glass-panel p-6 rounded-2xl border border-emerald-200 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">Comprehensive Assessment</span>
              <h4 className="text-xl font-bold text-slate-900 mt-0.5 font-display">Innovation DNA Composite Index</h4>
            </div>
            <div className="flex items-center space-x-3">
              <div className="text-right">
                <span className="text-xs text-slate-500 block font-medium">Overall DNA Score</span>
                <span className="text-2xl font-black text-emerald-600 font-display">88 / 100</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
              <span className="text-slate-500 font-medium block">1. Novelty & Non-Obviousness</span>
              <span className="text-lg font-bold text-emerald-600">82%</span>
              <div className="w-full bg-emerald-200 h-1 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full" style={{ width: '82%' }} />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
              <span className="text-slate-500 font-medium block">2. Regulatory Compliance</span>
              <span className="text-lg font-bold text-emerald-600">95%</span>
              <div className="w-full bg-emerald-200 h-1 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full" style={{ width: '95%' }} />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
              <span className="text-slate-500 font-medium block">3. Evidence Completeness</span>
              <span className="text-lg font-bold text-amber-600">76%</span>
              <div className="w-full bg-emerald-200 h-1 rounded-full overflow-hidden">
                <div className="bg-amber-500 h-full" style={{ width: '76%' }} />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
              <span className="text-slate-500 font-medium block">4. Export Market Readiness</span>
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
              <h4 className="text-base font-bold text-slate-900">AI Grant & Non-Dilutive Funding Matchmaker</h4>
              <p className="text-xs text-slate-500">Matched with Indian Government AYUSH, BIRAC, and DST funding schemes.</p>
            </div>
          </div>

          <div className="space-y-3">
            {grants.map((g, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="space-y-1 max-w-xl">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900 text-sm">{g.name}</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 text-[10px] font-mono border border-emerald-500/30">
                      {g.matchScore} Match
                    </span>
                  </div>
                  <span className="text-slate-500 block">{g.agency} • Eligibility: {g.eligibility}</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-500 block text-[10px] uppercase font-bold">Max Non-Dilutive Grant</span>
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
          <h4 className="text-base font-bold text-slate-900">Cross-Border Filing & Legal Cost Estimator</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
              <strong className="text-slate-900 block">India (IPO + FSSAI)</strong>
              <div className="text-xl font-bold text-emerald-600">₹28,500</div>
              <p className="text-slate-500">Includes Patent Form 1 (MSME 80% fee rebate), FSSAI Central License application, and NABL testing.</p>
            </div>
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
              <strong className="text-slate-900 block">United States (US FDA DSHEA)</strong>
              <div className="text-xl font-bold text-cyan-600">$2,400 USD</div>
              <p className="text-slate-500">Includes 21 CFR 111 cGMP safety review, label compliance audit, and 30-day FDA notification.</p>
            </div>
            <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
              <strong className="text-slate-900 block">Canada (Health Canada NHP)</strong>
              <div className="text-xl font-bold text-violet-600">$3,100 CAD</div>
              <p className="text-slate-500">Includes Class I electronic Product Licence Application (NPN) and Foreign Site Annex audit.</p>
            </div>
          </div>
        </div>
      )}

      {/* Sustainability */}
      {activeTab === 'sustainability' && (
        <div className="glass-panel p-6 rounded-2xl border border-emerald-200 space-y-4 text-xs">
          <h4 className="text-base font-bold text-slate-900">Ethical Sourcing & Ecological Sustainability Score</h4>
          <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-500/30 text-emerald-700 space-y-2">
            <strong className="block text-emerald-700">Zero CITES Endangered Species Contamination</strong>
            <p className="leading-relaxed">
              Formulation uses cultivated <em>Withania somnifera</em> (Ashwagandha) and <em>Bacopa monnieri</em> (Brahmi). Complies with National Biodiversity Authority Access and Benefit Sharing (ABS) equitable compensation guidelines.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
