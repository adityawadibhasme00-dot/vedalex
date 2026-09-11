'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  Route, Loader2, AlertTriangle, CheckCircle2, Clock, Circle,
  MapPin, ArrowRight, Sparkles, CircleDashed,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { Badge } from './ui/Badge';
import { getRoadmap } from '../lib/api';
import { RoadmapData } from '../types';

const statusView: Record<string, { badge: 'success' | 'warning' | 'info' | 'neutral'; icon: React.ReactNode; bar: string; ring: string }> = {
  completed: { badge: 'success', icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />, bar: 'bg-emerald-500', ring: 'border-emerald-300' },
  in_progress: { badge: 'warning', icon: <Clock className="w-5 h-5 text-amber-600" />, bar: 'bg-amber-500', ring: 'border-amber-300' },
  pending: { badge: 'info', icon: <CircleDashed className="w-5 h-5 text-blue-600" />, bar: 'bg-blue-400', ring: 'border-blue-200' },
  not_started: { badge: 'neutral', icon: <Circle className="w-5 h-5 text-slate-400" />, bar: 'bg-slate-300', ring: 'border-slate-200' },
};

export function RoadmapView({ passportId }: { passportId?: string }) {
  const [data, setData] = useState<RoadmapData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!passportId) return;
    setLoading(true);
    setError('');
    try {
      const res = await getRoadmap(passportId);
      setData(res);
    } catch (e: any) {
      setError(e.message || 'Failed to load roadmap');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [passportId]);

  useEffect(() => { load(); }, [load]);

  if (!passportId) {
    return (
      <GlassCard padding="lg">
        <div className="flex items-center gap-3 text-sm text-slate-600">
          <Route className="w-5 h-5 text-emerald-600" />
          Create an Innovation Passport first to generate the Regulatory Roadmap.
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-4">
      <GlassCard padding="md">
        <div className="flex items-center gap-2 mb-1">
          <Route className="w-5 h-5 text-emerald-600" />
          <h3 className="text-sm font-bold text-slate-900 font-display">Regulatory Roadmap</h3>
          {data && <Badge variant="info" className="ml-auto">Phase {data.current_phase} of {data.total_phases}</Badge>}
        </div>
        <p className="text-xs text-slate-500">The filing journey from prior art to market launch, computed for this passport.</p>
        {error && <p className="mt-2 text-xs text-red-600 flex items-center gap-1"><AlertTriangle className="w-3.5 h-3.5" /> {error}</p>}
      </GlassCard>

      {loading && (
        <GlassCard padding="lg"><div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-emerald-600" /></div></GlassCard>
      )}

      {data && (
        <>
          <GlassCard padding="sm" className="border-emerald-300">
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-700">
              <MapPin className="w-4 h-4 text-emerald-600" />
              <span><span className="font-semibold">Estimated completion:</span> {data.estimated_completion}</span>
              <span className="hidden sm:inline text-slate-300">|</span>
              <ArrowRight className="hidden sm:block w-4 h-4 text-emerald-600" />
              <span><span className="font-semibold">Next action:</span> {data.next_action}</span>
            </div>
          </GlassCard>

          <div className="relative">
            <div className="absolute left-[18px] top-4 bottom-4 w-0.5 bg-emerald-200 md:left-1/2 md:-translate-x-px" />
            <div className="space-y-4">
              {data.phases.map((phase) => {
                const ui = statusView[phase.status] || statusView.not_started;
                const isCurrent = phase.phase === data.current_phase;
                return (
                  <div key={phase.phase} className={`relative flex gap-4 items-start md:w-1/2 ${phase.phase % 2 === 0 ? 'md:ml-auto md:pl-10' : 'md:pr-10 md:flex-row-reverse'} `}>
                    <div className={`flex-shrink-0 w-9 h-9 rounded-full bg-white border-2 flex items-center justify-center z-10 ${ui.ring}`}>
                      {phase.phase}
                    </div>
                    <GlassCard padding="md" className={`flex-1 ${ui.ring} ${isCurrent ? 'border-emerald-500 shadow-glow-emerald' : ''}`}>
                      <div className="flex items-center justify-between gap-2 flex-wrap mb-1">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full">{ui.icon}</span>
                          <h4 className="text-sm font-bold text-slate-900 font-display">{phase.title}</h4>
                          {isCurrent && <Badge variant="warning" dot>Current</Badge>}
                        </div>
                        <Badge variant={ui.badge}>{phase.status.replace(/_/g, ' ')}</Badge>
                      </div>
                      <p className="text-xs text-slate-600">{phase.description}</p>
                      <div className="text-[11px] text-slate-400 mt-1"><Clock className="w-3 h-3 inline mr-1" />{phase.duration}</div>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {phase.requirements.map((r, i) => <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-50 text-slate-600 border border-slate-200">{r}</span>)}
                      </div>
                      <div className="mt-2 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                        <div className={`h-full rounded-full ${ui.bar}`} style={{ width: phase.status === 'completed' ? '100%' : phase.status === 'in_progress' ? '55%' : '12%' }} />
                      </div>
                    </GlassCard>
                  </div>
                );
              })}
            </div>
          </div>

          <GlassCard padding="md">
            <h3 className="text-sm font-bold text-slate-900 font-display mb-2 flex items-center gap-2"><Sparkles className="w-4 h-4 text-violet-600" /> Filing tip</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Roadmap phases reflect standard Ayurveda/IP filing flows. Re-run each intelligence engine on this passport to close gaps
              before the Evidence Collection and Compliance Submission phases.
            </p>
          </GlassCard>
        </>
      )}
    </div>
  );
}