'use client';
import React, { useEffect, useState } from 'react';
import {
  FileText, FlaskConical, BookOpen, Bot, Search, ClipboardCheck,
  ShieldCheck, Plus, ArrowRight, Sparkles, MessageSquare, Clock, CheckCircle, FileDown, Sprout, Scale,
} from 'lucide-react';
import { InnovationPassport } from '../types';
import { getPatentReadiness } from '../lib/api';
import { innolabApi, InnolabProject, InnolabAgent } from '../lib/innolabApi';
import { useLang } from '../lib/LangContext';
import { useAuth } from '../lib/AuthContext';
import { t } from '../lib/i18n';
import { GovStatCard } from './dashboard/GovStatCard';
import { ActionCard } from './dashboard/ActionCard';
import { ActivityItem } from './dashboard/ActivityItem';
import { ProjectCard, type ProjectStatus } from './dashboard/ProjectCard';

interface DashboardOverviewProps {
  passport: InnovationPassport | null;
  onNavigateTab: (tab: any) => void;
}

function mapProject(p: InnolabProject): { status: ProjectStatus; progress: number } {
  const s = (p.status || '').toLowerCase();
  if (s.includes('complete') || s.includes('done') || s.includes('success')) return { status: 'completed', progress: 100 };
  if (s.includes('run') || s.includes('progress') || s.includes('active') || s.includes('pending')) return { status: 'in_progress', progress: 56 };
  return { status: 'queued', progress: 0 };
}

export default function DashboardOverview({ passport, onNavigateTab }: DashboardOverviewProps) {
  const { lang } = useLang();
  const { user } = useAuth();
  const [projects, setProjects] = useState<InnolabProject[]>([]);
  const [agents, setAgents] = useState<InnolabAgent[]>([]);
  const [projectsLoaded, setProjectsLoaded] = useState(false);

  const [stats, setStats] = useState({
    passportActive: false,
    passportVersion: 1,
    patentReadiness: 0,
    documentsUploaded: 0,
    verifiedDocs: 0,
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

  useEffect(() => {
    innolabApi.listProjects()
      .then((ps) => { setProjects(ps); setProjectsLoaded(true); })
      .catch(() => setProjectsLoaded(true));
    innolabApi.agents()
      .then((r) => setAgents(r.agents))
      .catch(() => {});
  }, []);

  const readiness = stats.patentReadiness;
  const firstName = (user?.name || 'Innovator').split(' ')[0];

  const recentProjects = (() => {
    if (projects.length > 0) {
      return projects.slice(0, 4).map((p) => {
        const m = mapProject(p);
        return {
          title: p.name,
          agent: p.description || t('overview_lab_project', lang),
          status: m.status,
          progress: m.progress,
          date: p.created_at ? `${t('overview_created_prefix', lang)} ${new Date(p.created_at).toLocaleDateString()}` : t('overview_created_recently', lang),
          href: '/innovation-lab',
        };
      });
    }
    if (agents.length > 0) {
      return agents.slice(0, 4).map((a) => ({
        title: a.label,
        agent: `${a.category_label} · ${a.phase}`,
        status: 'queued' as ProjectStatus,
        progress: 0,
        date: t('overview_ready_to_run', lang),
        href: `/innovation-lab/agents/${a.slug}`,
      }));
    }
    if (passport) {
      return [{
        title: passport.case_title,
        agent: t('overview_passport_active_analysis', lang),
        status: 'in_progress' as ProjectStatus,
        progress: readiness,
        date: `${t('overview_version_prefix', lang)} v${passport.version || 1} · ${new Date(passport.updated_at || Date.now()).toLocaleDateString()}`,
        href: undefined as string | undefined,
      }];
    }
    return [];
  })();

  return (
    <div className="space-y-8 animate-slide-up">
      {/* ─── Welcome Section ───────────────────────────── */}
      <div className="bg-white rounded-xl border border-gov-rule p-6 md:p-8 relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-gov-blue/[0.06] blur-3xl" />
        <div className="absolute -bottom-24 -left-16 w-64 h-64 rounded-full bg-amber-500/[0.06] blur-3xl" />
        <div className="relative">
          <h1 className="text-2xl md:text-3xl font-bold text-gov-navy font-display tracking-tight mb-2">
            {t('welcome_back', lang)} <span className="text-gov-blue">{firstName}!</span>
          </h1>
          <p className="text-gray-600 mb-4">{t('overview_help_today', lang)}</p>
          <div className="flex flex-wrap items-center gap-2 mb-6">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gov-wash border border-gov-rule text-xs text-gov-green">
              <ShieldCheck className="w-3.5 h-3.5" /> {t('overview_rag_badge', lang)}
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-xs text-gov-blue">
              <Sparkles className="w-3.5 h-3.5" /> {t('overview_multi_badge', lang)}
            </span>
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => onNavigateTab('passport')}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gov-blue hover:bg-gov-navy text-white text-sm font-semibold rounded-md border border-gov-blueDk transition-colors"
            >
              <Plus className="w-4 h-4" /> {t('create_passport', lang)}
            </button>
            <button
              onClick={() => onNavigateTab('ipreg')}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-white hover:bg-gov-wash text-gray-700 border border-gov-rule text-sm font-semibold rounded-md transition-colors"
            >
              <ArrowRight className="w-4 h-4" /> {t('continue_analysis', lang)}
            </button>
          </div>
        </div>
      </div>

      {/* ─── Stats Cards ───────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        <GovStatCard
          icon={<FileText className="w-5 h-5" />}
          label={t('innovation_passport', lang)}
          value={stats.passportActive ? t('overview_stat_active', lang) : t('overview_stat_draft', lang)}
          change={t('overview_passport_version', lang).replace('{v}', String(stats.passportVersion))}
          trend="up"
        />
        <GovStatCard
          icon={<MessageSquare className="w-5 h-5" />}
          label={t('patent_readiness', lang)}
          value={`${readiness}%`}
          change={readiness >= 70 ? t('overview_readiness_filing', lang) : t('overview_readiness_gaps', lang)}
          trend={readiness >= 70 ? 'up' : 'down'}
        />
        <GovStatCard
          icon={<Clock className="w-5 h-5" />}
          label={t('overview_stat_evidence', lang)}
          value={`${stats.documentsUploaded}`}
          change={t('overview_evidence_counts', lang).replace('{v}', String(stats.verifiedDocs)).replace('{p}', String(stats.documentsUploaded - stats.verifiedDocs))}
          trend={stats.verifiedDocs >= (stats.documentsUploaded >= 3 ? 3 : stats.documentsUploaded) ? 'up' : 'down'}
        />
        <GovStatCard
          icon={<CheckCircle className="w-5 h-5" />}
          label={t('next_action', lang)}
          value={t('overview_stability_study', lang)}
          change={t('overview_required_before_filing', lang)}
          trend="up"
        />
      </div>

      {/* ─── Quick Actions ─────────────────────────────── */}
      <div>
        <h2 className="text-xl font-semibold text-gov-navy font-display mb-4">{t('overview_quick_actions', lang)}</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ActionCard
            icon={<Bot className="w-6 h-6" />}
            label={t('overview_ask_assistant', lang)}
            description={t('overview_ask_assistant_desc', lang)}
            color="emerald"
            onClick={() => onNavigateTab('copilot')}
          />
          <ActionCard
            icon={<FlaskConical className="w-6 h-6" />}
            label={t('overview_start_analysis', lang)}
            description={t('overview_start_analysis_desc', lang)}
            color="blue"
            onClick={() => onNavigateTab('innolab')}
          />
          <ActionCard
            icon={<BookOpen className="w-6 h-6" />}
            label={t('overview_browse_knowledge', lang)}
            description={t('overview_browse_knowledge_desc', lang)}
            color="amber"
            onClick={() => onNavigateTab('ipreg')}
          />
        </div>
      </div>

      {/* ─── Recent Activity ───────────────────────────── */}
      <div>
        <h2 className="text-xl font-semibold text-gov-navy font-display mb-4">{t('overview_recent_activity', lang)}</h2>
        <div className="bg-white rounded-xl border border-gov-rule overflow-hidden">
          {passport ? (
            <>
              <ActivityItem
                icon={<Search className="w-4 h-4" />}
                title={t('overview_formula_intake', lang)}
                description={passport.case_title}
                time={`${t('overview_just_now', lang)} · ${new Date(passport.created_at).toLocaleDateString()}`}
                status="completed"
              />
              <ActivityItem
                icon={<ClipboardCheck className="w-4 h-4" />}
                title={t('overview_patent_assessment', lang)}
                description={t('overview_target_markets', lang).replace('{n}', String(passport.target_markets?.length || 0)).replace('{r}', String(readiness))}
                time={t('overview_real_time', lang)}
                status={readiness > 0 ? 'completed' : 'in_progress'}
              />
              <ActivityItem
                icon={<Sprout className="w-4 h-4" />}
                title={t('overview_biores_review', lang)}
                description={t('overview_ingredients_mapped', lang).replace('{n}', String(passport.ingredients?.length || 0))}
                time={t('overview_on_demand', lang)}
                status="in_progress"
              />
            </>
          ) : (
            <>
              <ActivityItem
                icon={<Bot className="w-4 h-4" />}
                title={t('overview_assistant_ready', lang)}
                description={t('overview_assistant_ready_desc', lang)}
                time={t('overview_always_available', lang)}
                status="completed"
              />
              <ActivityItem
                icon={<Scale className="w-4 h-4" />}
                title={t('overview_kb_loaded', lang)}
                description={t('overview_kb_loaded_desc', lang)}
                time={t('overview_synced', lang)}
                status="completed"
              />
              <ActivityItem
                icon={<FileDown className="w-4 h-4" />}
                title={t('overview_no_dossier', lang)}
                description={t('overview_no_dossier_desc', lang)}
                time={t('overview_not_started', lang)}
                status="in_progress"
              />
            </>
          )}
        </div>
      </div>

      {/* ─── Recent Projects ───────────────────────────── */}
      {recentProjects.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-gov-navy font-display mb-4">
            {t('overview_recent_projects', lang)}
            <span className="ml-3 text-sm font-medium text-gray-500">{t('overview_running_in_lab', lang)}</span>
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {recentProjects.map((p, idx) => (
              <ProjectCard
                key={`${p.title}-${idx}`}
                title={p.title}
                agent={p.agent}
                status={p.status}
                progress={p.progress}
                date={p.date}
                href={p.href}
              />
            ))}
          </div>
          {!projectsLoaded && (
            <p className="text-sm text-gray-500 mt-3">{t('overview_loading_projects', lang)}</p>
          )}
        </div>
      )}
    </div>
  );
}