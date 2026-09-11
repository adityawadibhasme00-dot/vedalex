'use client';

import React, { useState } from 'react';
import {
  ShieldAlert,
  Users,
  Activity,
  ToggleLeft,
  ToggleRight,
  Database,
  FileCheck,
  Server,
  Lock,
  Sparkles
} from 'lucide-react';

export default function AdminDashboard() {
  const [featureFlags, setFeatureFlags] = useState({
    stitch3DAssistant: true,
    whatIfReactiveDAG: true,
    voiceBhashiniNLP: true,
    dpdpConsentHashing: true,
    autoSection3PScreening: true
  });

  const toggleFlag = (key: keyof typeof featureFlags) => {
    setFeatureFlags(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const auditLogs = [
    { timestamp: '2026-09-06 23:15:02', user: 'founder@ayurstartup.in', action: 'EXPORT_PASSPORT_PDF', hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' },
    { timestamp: '2026-09-06 23:12:44', user: 'rajesh.vaidya@ayurstartup.in', action: 'DPDP_CONSENT_CAPTURED', hash: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4' },
    { timestamp: '2026-09-06 23:08:19', user: 'dr.sharma@ayush-hub.gov.in', action: 'EXPERT_DISPATCH_DISPATCHED', hash: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb' }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel p-5 rounded-2xl border border-emerald-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Server className="w-5 h-5 text-emerald-600" />
            <h3 className="text-base font-bold text-slate-900 font-display">
              Enterprise System Administration & Security Hub
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time control plane for feature flags, AI agent execution telemetry, and DPDP cryptographic audit trails.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-600 border border-emerald-500/30 text-xs font-bold flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>FastAPI Monolith â€¢ All Systems Operational</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Feature Flags */}
        <div className="lg:col-span-6 glass-panel p-5 rounded-2xl border border-emerald-200 space-y-4 text-xs">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center space-x-1.5">
            <Sparkles className="w-4 h-4 text-amber-600" />
            <span>Dynamic Feature Flags (Zero Downtime Toggle)</span>
          </h4>

          <div className="space-y-2.5">
            <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
              <div>
                <strong className="text-slate-900 block">IP-SAKTI Assistant</strong>
                <span className="text-slate-500">Enables WebGL floating companion & mood state machine</span>
              </div>
              <button onClick={() => toggleFlag('stitch3DAssistant')}>
                {featureFlags.stitch3DAssistant ? (
                  <ToggleRight className="w-6 h-6 text-emerald-600" />
                ) : (
                  <ToggleLeft className="w-6 h-6 text-slate-400" />
                )}
              </button>
            </div>

            <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
              <div>
                <strong className="text-slate-900 block">Reactive What-If Simulation DAG</strong>
                <span className="text-slate-500">Enables live AST dependency node traversal</span>
              </div>
              <button onClick={() => toggleFlag('whatIfReactiveDAG')}>
                {featureFlags.whatIfReactiveDAG ? (
                  <ToggleRight className="w-6 h-6 text-emerald-600" />
                ) : (
                  <ToggleLeft className="w-6 h-6 text-slate-400" />
                )}
              </button>
            </div>

            <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
              <div>
                <strong className="text-slate-900 block">DPDP Act 2023 Consent Audit Hashes</strong>
                <span className="text-slate-500">Cryptographic logging of all external escalations</span>
              </div>
              <button onClick={() => toggleFlag('dpdpConsentHashing')}>
                {featureFlags.dpdpConsentHashing ? (
                  <ToggleRight className="w-6 h-6 text-emerald-600" />
                ) : (
                  <ToggleLeft className="w-6 h-6 text-slate-400" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Audit Logs */}
        <div className="lg:col-span-6 glass-panel p-5 rounded-2xl border border-emerald-200 space-y-4 text-xs">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center space-x-1.5">
            <Lock className="w-4 h-4 text-emerald-600" />
            <span>Cryptographic Consent & Access Audit Logs (SHA-256)</span>
          </h4>

          <div className="space-y-2">
            {auditLogs.map((log, idx) => (
              <div key={idx} className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1 font-mono text-[11px]">
                <div className="flex items-center justify-between text-slate-500">
                  <span>{log.timestamp}</span>
                  <span className="text-emerald-600 font-semibold">{log.action}</span>
                </div>
                <div className="text-slate-600 truncate">User: {log.user}</div>
                <div className="text-[10px] text-slate-500 truncate">SHA256: {log.hash}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
