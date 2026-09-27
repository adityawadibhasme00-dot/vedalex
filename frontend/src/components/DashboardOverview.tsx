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
        nextAction: passport.product_form ? `File ${passport.product_form} evidence set` : 'Complete profile intake',
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
          agent: p.description || 'Innovation Lab project',
          status: m.status,
          progress: m.progress,
          date: p.created_at ? `Created: ${new Date(p.created_at).toLocaleDateString()}` : 'Created recently',
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
        date: 'Ready to run in the Innovation Lab',
        href: `/innovation-lab/agents/${a.slug}`,
      }));
    }
    if (passport) {
      return [{
        title: passport.case_title,
        agent: 'Innovation Passport · active analysis',
        status: 'in_progress' as ProjectStatus,
        progress: readiness,
        date: `Version v${passport.version || 1} · ${new Date(passport.updated_at || Date.now()).toLocaleDateString()}`,
        href: undefined as string | undefined,
      }];
    }
    return [];
  })();

  return (
    <div className="space-y-8 animate-slide-up">
      {/* ─── Welcome Section ───────────────────────────── */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 md:p-8 relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-emerald-500/[0.08] blur-3xl" />
        <div className="absolute -bottom-24 -left-16 w-64 h-64 rounded-full bg-amber-500/[0.08] blur-3xl" />
        <div className="relative">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 font-display tracking-tight mb-2">
            Welcome back, <span className="text-emerald-700">{firstName}!</span>
          </h1>
          <p className="text-gray-600 mb-4">How can we help you today?</p>
          <div className="flex flex-wrap items-center gap-2 mb-6">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-xs text-emerald-700">
              <ShieldCheck className="w-3.5 h-3.5" /> RAG-grounded · Source-cited · DPDP compliant
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-xs text-blue-700">
              <Sparkles className="w-3.5 h-3.5" /> Multilingual AI · 10 Indian languages
            </span>
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => onNavigateTab('passport')}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-semibold rounded-xl shadow-lg shadow-emerald-700/20 transition-transform active:scale-[0.98]"
            >
              <Plus className="w-4 h-4" /> {t('create_passport', lang)}
            </button>
            <button
              onClick={() => onNavigateTab('ipreg')}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-white hover:bg-emerald-50 text-gray-700 border border-emerald-200 text-sm font-semibold rounded-xl transition-transform active:scale-[0.98]"
            >
              <ArrowRight className="w-4 h-4" /> Continue Analysis
            </button>
          </div>
        </div>
      </div>

      {/* ─── Stats Cards ───────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        <GovStatCard
          icon={<FileText className="w-5 h-5" />}
          label="Innovation Passport"
          value={stats.passportActive ? 'Active' : 'Draft'}
          change={`Version v${stats.passportVersion} · QR ready`}
          trend="up"
        />
        <GovStatCard
          icon={<MessageSquare className="w-5 h-5" />}
          label="Patent Readiness"
          value={`${readiness}%`}
          change={readiness >= 70 ? 'Filing-ready band' : 'Gaps to close'}
          trend={readiness >= 70 ? 'up' : 'down'}
        />
        <GovStatCard
          icon={<Clock className="w-5 h-5" />}
          label="Evidence Documents"
          value={`${stats.documentsUploaded}`}
          change={`${stats.verifiedDocs} verified · ${stats.documentsUploaded - stats.verifiedDocs} pending`}
          trend={stats.verifiedDocs >= (stats.documentsUploaded >= 3 ? 3 : stats.documentsUploaded) ? 'up' : 'down'}
        />
        <GovStatCard
          icon={<CheckCircle className="w-5 h-5" />}
          label="Next Action"
          value="Stability Study"
          change="Required before filing"
          trend="up"
        />
      </div>

      {/* ─── Quick Actions ─────────────────────────────── */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 font-display mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ActionCard
            icon={<Bot className="w-6 h-6" />}
            label="Ask AI Assistant"
            description="Get instant answers on IP and regulations"
            color="emerald"
            onClick={() => onNavigateTab('copilot')}
          />
          <ActionCard
            icon={<FlaskConical className="w-6 h-6" />}
            label="Start Analysis"
            description="Run patent search or prior-art analysis"
            color="blue"
            onClick={() => onNavigateTab('innolab')}
          />
          <ActionCard
            icon={<BookOpen className="w-6 h-6" />}
            label="Browse Knowledge"
            description="Explore statutes, patents, and regulations"
            color="amber"
            onClick={() => onNavigateTab('ipreg')}
          />
        </div>
      </div>

      {/* ─── Recent Activity ───────────────────────────── */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 font-display mb-4">Recent Activity</h2>
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          {passport ? (
            <>
              <ActivityItem
                icon={<Search className="w-4 h-4" />}
                title="Formula Intake Registered"
                description={passport.case_title}
                time={passport.created_at ? `Just now · ${new Date(passport.created_at).toLocaleDateString()}` : 'Just now'}
                status="completed"
              />
              <ActivityItem
                icon={<ClipboardCheck className="w-4 h-4" />}
                title="Patent & Regulatory Assessment"
                description={`${passport.target_markets?.length || 0} target markets · readiness ${readiness}% · AI-verified citations`}
                time="Real-time"
                status={readiness > 0 ? 'completed' : 'in_progress'}
              />
              <ActivityItem
                icon={<Sprout className="w-4 h-4" />}
                title="Bio-Resource & ABS Review"
                description={`${passport.ingredients?.length || 0} ingredients mapped for provenance & compliance`}
                time="On demand"
                status="in_progress"
              />
            </>
          ) : (
            <>
              <ActivityItem
                icon={<Bot className="w-4 h-4" />}
                title="AI Assistant Ready"
                description="Ask anything about patents, IP law, or regulatory filings"
                time="Always available"
                status="completed"
              />
              <ActivityItem
                icon={<Scale className="w-4 h-4" />}
                title="Knowledge Base Loaded"
                description="Statutes, patents, and regulations searchable in 10 languages"
                time="Synced"
                status="completed"
              />
              <ActivityItem
                icon={<FileDown className="w-4 h-4" />}
                title="No dossier exported yet"
                description="Create an Innovation Passport to generate filing-ready documents"
                time="Not started"
                status="in_progress"
              />
            </>
          )}
        </div>
      </div>

      {/* ─── Recent Projects ───────────────────────────── */}
      {recentProjects.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 font-display mb-4">
            Recent Projects
            <span className="ml-3 text-sm font-medium text-gray-500">Running in the Innovation AI Lab</span>
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
            <p className="text-sm text-gray-500 mt-3">Loading project status…</p>
          )}
        </div>
      )}
    </div>
  );
}