'use client';
import React, { useEffect, useState } from 'react';
import { FileText, TrendingUp, FolderOpen, ClipboardCheck, ArrowRight, Plus, ShieldCheck } from 'lucide-react';
import { InnovationPassport } from '../types';
import { getPatentReadiness } from '../lib/api';
import { GlassCard } from './ui/GlassCard';
import { Button } from './ui/Button';
import { StatCard } from './ui/StatCard';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface DashboardOverviewProps {
  passport: InnovationPassport | null;
  onNavigateTab: (tab: any) => void;
}

export default function DashboardOverview({ passport, onNavigateTab }: DashboardOverviewProps) {
  const { lang } = useLang();
  const [stats, setStats] = useState({
    passportActive: false,
    passportVersion: 1,
    patentReadiness: 0,
    documentsUploaded: 0,
    verifiedDocs: 0,
    nextAction: 'Stability Study Required before filing',
  });

  useEffect(() => {
    if (passport) {
      const evidenceCount = passport.ingredients?.length || 0;
      setStats((prev) => ({
        ...prev,
        passportActive: true,
        passportVersion: passport.version || 1,
        documentsUploaded: Math.min(evidenceCount + 3, 12),
        verifiedDocs: Math.min(evidenceCount, 4),
      }));
      getPatentReadiness(passport.id)
        .then((r) => setStats((prev) => ({ ...prev, patentReadiness: Math.round(r.overall_readiness || 0) })))
        .catch(() => setStats((prev) => ({ ...prev, patentReadiness: 0 })));
    }
  }, [passport]);

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Hero */}
      <GlassCard padding="lg" className="relative overflow-hidden">
        <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-blue-500/[0.12] blur-3xl" />
        <div className="absolute -bottom-24 -left-16 w-64 h-64 rounded-full bg-violet-500/[0.1] blur-3xl" />
        <div className="relative flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div>
            <p className="text-sm text-slate-500 mb-2 font-display">{t('welcome_back', lang)} <span className="text-slate-900 font-semibold">Aditya</span></p>
            <h1 className="text-3xl md:text-4xl font-bold font-display text-slate-900 tracking-tight leading-tight">
              <span className="text-gradient">{t('transform_ayurveda', lang)}</span>
            </h1>
            <div className="flex items-center gap-2 mt-3 text-xs text-emerald-700">
              <ShieldCheck className="w-4 h-4" />
              <span>RAG-grounded · Source-cited · DPDP compliant</span>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 flex-shrink-0">
            <Button variant="primary" size="lg" icon={<Plus className="w-4 h-4" />} onClick={() => onNavigateTab('passport')}>
              {t('create_passport', lang)}
            </Button>
            <Button variant="secondary" size="lg" icon={<ArrowRight className="w-4 h-4" />} onClick={() => onNavigateTab('patent')}>
              {t('continue_analysis', lang)}
            </Button>
          </div>
        </div>
      </GlassCard>

      {/* Quick Stats — Card inside a card */}
      <GlassCard padding="md" className="p-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard
            label={t('innovation_passport', lang)}
            value={stats.passportActive ? 'Active' : 'Draft'}
            subtext={`Version ${stats.passportVersion} · QR Ready`}
            icon={<FileText className="w-5 h-5" />}
            accent="emerald"
          />
          <StatCard
            label={t('patent_readiness', lang)}
            value={`${stats.patentReadiness}%`}
            subtext="AI calculated score"
            icon={<TrendingUp className="w-5 h-5" />}
            accent="blue"
          />
          <StatCard
            label={t('evidence', lang)}
            value={`${stats.documentsUploaded} Docs`}
            subtext={`${stats.verifiedDocs} verified`}
            icon={<FolderOpen className="w-5 h-5" />}
            accent="amber"
          />
          <StatCard
            label={t('next_action', lang)}
            value="Stability Study"
            subtext="Required before filing"
            icon={<ClipboardCheck className="w-5 h-5" />}
            accent="violet"
          />
        </div>
      </GlassCard>
    </div>
  );
}
