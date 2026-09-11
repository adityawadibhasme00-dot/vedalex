'use client';
import React from 'react';
import {
  ShieldAlert, Map, FileWarning, Route, Leaf, ClipboardList,
  FileDown, Scale, ArrowRight, Sparkles, RefreshCw, ShieldCheck, FlaskConical,
  Sprout, Layers, FileBadge, BookMarked,
} from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import TiltCard from './TiltCard';
import clsx from 'clsx';
import { HerbSprig, TulsiLeaf } from './BotanicalDecor';

export interface FeatureDef {
  id: string;
  title: string;
  description: string;
  category: string;
  categoryColor: 'red' | 'blue' | 'amber' | 'violet' | 'emerald' | 'cyan';
  icon: React.ReactNode;
  api: string;
  steps: string[];
}

const FEATURES: FeatureDef[] = [
  {
    id: 'disclosure',
    title: 'Patent Disclosure Sentinel',
    description: 'Detect risky public disclosures before patent filing.',
    category: 'Critical',
    categoryColor: 'red',
    icon: <ShieldAlert className="w-5 h-5" />,
    api: 'POST /upload/disclosure-check',
    steps: ['Upload PDF/PPT', 'Detect invention-revealing sentences', 'Generate risk score'],
  },
  {
    id: 'fto',
    title: 'Freedom-to-Operate Map',
    description: 'Check whether selling may infringe existing patents.',
    category: 'High Impact',
    categoryColor: 'blue',
    icon: <Map className="w-5 h-5" />,
    api: 'POST /fto/check',
    steps: ['Search patent metadata', 'Claim-level overlap', 'Risk summary'],
  },
  {
    id: 'label',
    title: 'Claim Firewall',
    description: 'Prevent risky marketing claims on your labels.',
    category: 'Compliance',
    categoryColor: 'amber',
    icon: <FileWarning className="w-5 h-5" />,
    api: 'POST /label/analyze',
    steps: ['Analyze labels', 'Safe wording', 'Flag risky statements'],
  },
  {
    id: 'roadmap',
    title: 'Regulatory Roadmap',
    description: 'Visual filing journey with blockers and milestones.',
    category: 'Roadmap',
    categoryColor: 'violet',
    icon: <Route className="w-5 h-5" />,
    api: 'GET /roadmap/{id}',
    steps: ['Prior Art', 'ABS', 'Patent', 'Evidence', 'Compliance', 'Market'],
  },
  {
    id: 'abs',
    title: 'Bio-Resource Ledger',
    description: 'Track ingredient lineage and ABS compliance.',
    category: 'Ayurveda',
    categoryColor: 'emerald',
    icon: <Leaf className="w-5 h-5" />,
    api: 'GET /abs/{id}',
    steps: ['Source state', 'Supplier', 'ABS status'],
  },
  {
    id: 'evidence-matrix',
    title: 'Evidence Matrix',
    description: 'Map claims to supporting evidence with strength indicators.',
    category: 'Evidence',
    categoryColor: 'cyan',
    icon: <ClipboardList className="w-5 h-5" />,
    api: 'GET /evidence/matrix/{id}',
    steps: ['Strong evidence', 'Missing evidence', 'Strength indicator'],
  },
  {
    id: 'claim-safety',
    title: 'Claim & Safety Intelligence',
    description: 'Test claims against evidence, regulations & pharmacovigilance signals.',
    category: 'Safety',
    categoryColor: 'red',
    icon: <ShieldCheck className="w-5 h-5" />,
    api: 'POST /intelligence/claim-safety/analyze',
    steps: ['Risk-score each claim', 'Compliant alternative wording', 'Ayush Suraksha signals'],
  },
  {
    id: 'evidence-quality',
    title: 'Evidence & Quality Intelligence',
    description: 'Research evidence ladder + pharmacopoeia quality readiness per ingredient.',
    category: 'Quality',
    categoryColor: 'cyan',
    icon: <FlaskConical className="w-5 h-5" />,
    api: 'GET /intelligence/evidence-quality/{id}',
    steps: ['Evidence support %', 'Quality readiness %', 'Heavy metals & markers'],
  },
  {
    id: 'bio-resource',
    title: 'Bio-Resource Intelligence Graph',
    description: 'Per-plant provenance, conservation, ABS, TK & IP posture for every botanical.',
    category: 'Ayurveda',
    categoryColor: 'emerald',
    icon: <Sprout className="w-5 h-5" />,
    api: 'GET /intelligence/bio-resource/{id}',
    steps: ['Names & plant parts', 'Provenance & geography', 'ABS / TK / IP posture'],
  },
  {
    id: 'product-classifier',
    title: 'Ayurveda Aahara Product Classifier',
    description: 'Proposes the likely regulatory class from product form, claims & process.',
    category: 'Classification',
    categoryColor: 'violet',
    icon: <Layers className="w-5 h-5" />,
    api: 'POST /intelligence/product-classify',
    steps: ['Form & dosage', 'Claims & process', 'Scored pathway + reasons'],
  },
  {
    id: 'export-readiness',
    title: 'Export / Market Readiness Engine',
    description: 'Gap comparison against India, US, EU & Canada requirement sets.',
    category: 'Export',
    categoryColor: 'blue',
    icon: <FileBadge className="w-5 h-5" />,
    api: 'GET /intelligence/export-readiness/{id}',
    steps: ['Market-by-market %', 'Gaps with actions', 'Recommended first market'],
  },
  {
    id: 'terminology-mapper',
    title: 'Terminology Mapper for RAG',
    description: 'Resolve any script/transliteration of a botanical to one canonical entity key.',
    category: 'RAG',
    categoryColor: 'amber',
    icon: <BookMarked className="w-5 h-5" />,
    api: 'POST /intelligence/terminology/map',
    steps: ['Matched via exact/fuzzy', 'Canonical ID + monograph', 'RAG metadata hint'],
  },
  {
    id: 'dossier',
    title: 'Dossier Export',
    description: 'Generate filing-ready documents and checklists.',
    category: 'Export',
    categoryColor: 'blue',
    icon: <FileDown className="w-5 h-5" />,
    api: 'POST /export/dossier',
    steps: ['PDF', 'DOCX', 'Checklist'],
  },
  {
    id: 'expert',
    title: 'Expert Review Workspace',
    description: 'Prepare complete cases for legal experts.',
    category: 'Expert Review',
    categoryColor: 'violet',
    icon: <Scale className="w-5 h-5" />,
    api: 'GET /expert/package/{id}',
    steps: ['Package all evidence', 'List unresolved risks', 'Export review bundle'],
  },
  {
    id: 'what-if',
    title: 'What-If Simulator',
    description: 'Mutate claims live and see reactive compliance diffs.',
    category: 'Simulation',
    categoryColor: 'amber',
    icon: <RefreshCw className="w-5 h-5" />,
    api: 'POST /what-if/simulate',
    steps: ['Mutate claim wording', 'Traverse dependency DAG', 'Risk diff & alert'],
  },
];

const categoryStyles: Record<string, string> = {
  red: 'bg-red-100 text-red-600 border-red-500/30',
  blue: 'bg-blue-100 text-blue-600 border-blue-500/30',
  amber: 'bg-amber-100 text-amber-600 border-amber-500/30',
  violet: 'bg-violet-100 text-violet-600 border-violet-500/30',
  emerald: 'bg-emerald-100 text-emerald-600 border-emerald-500/30',
  cyan: 'bg-cyan-100 text-cyan-600 border-cyan-500/30',
};

const iconStyles: Record<string, string> = {
  red: 'bg-red-100 text-red-600',
  blue: 'bg-blue-100 text-blue-600',
  amber: 'bg-amber-100 text-amber-600',
  violet: 'bg-violet-100 text-violet-600',
  emerald: 'bg-emerald-100 text-emerald-600',
  cyan: 'bg-cyan-100 text-cyan-600',
};

const glowMap: Record<string, 'red' | 'cyan' | 'gold' | 'purple' | 'emerald' | 'cyan'> = {
  red: 'red',
  blue: 'cyan',
  amber: 'gold',
  violet: 'purple',
  emerald: 'emerald',
  cyan: 'cyan',
};

interface FeatureHubProps {
  onOpen: (id: string) => void;
}

export function FeatureHub({ onOpen }: FeatureHubProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 flex-wrap">
        <HerbSprig className="w-6 h-6 text-emerald-500" />
        <Sparkles className="w-4 h-4 text-blue-600" />
        <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">Feature Hub</h2>
        <div className="flex-1 min-w-[40px] h-px bg-gradient-to-r from-emerald-300/70 to-transparent" />
        <TulsiLeaf className="w-5 h-5 text-amber-500 hidden sm:block" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {FEATURES.map((f) => (
          <TiltCard key={f.id} glowColor={glowMap[f.categoryColor]} className="!p-0" >
            <GlassCard
              hover
              padding="md"
              className="flex flex-col group animate-slide-up !h-full"
              onClick={() => onOpen(f.id)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center', iconStyles[f.categoryColor])}>
                  {f.icon}
                </div>
                <span className={clsx('text-[10px] font-semibold px-2 py-0.5 rounded-full border', categoryStyles[f.categoryColor])}>
                  {f.category}
                </span>
              </div>
              <h3 className="text-sm font-bold text-slate-900 font-display mb-1.5">{f.title}</h3>
              <p className="text-xs text-slate-500 mb-4 leading-relaxed">{f.description}</p>
              <div className="mt-auto space-y-1.5 mb-4">
                {f.steps.map((step, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px] text-slate-600">
                    <span className="w-1 h-1 rounded-full bg-slate-400" />
                    {step}
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-emerald-200">
                <code className="text-[10px] text-blue-600/70 font-mono">{f.api}</code>
                <span className="flex items-center gap-1 text-xs font-semibold text-blue-600 group-hover:text-blue-500 transition">
                  Open <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </GlassCard>
          </TiltCard>
        ))}
      </div>
    </div>
  );
}
