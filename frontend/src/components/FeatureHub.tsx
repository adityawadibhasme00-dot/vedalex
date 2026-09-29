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
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

export interface FeatureDef {
  id: string;
  titleKey: string;
  descKey: string;
  categoryKey: string;
  categoryColor: 'red' | 'blue' | 'amber' | 'violet' | 'emerald' | 'cyan';
  icon: React.ReactNode;
  api: string;
  stepKeys: string[];
}

const FEATURES: FeatureDef[] = [
  {
    id: 'disclosure',
    titleKey: 'fh_disclosure_title',
    descKey: 'fh_disclosure_desc',
    categoryKey: 'feature_cat_critical',
    categoryColor: 'red',
    icon: <ShieldAlert className="w-5 h-5" />,
    api: 'POST /upload/disclosure-check',
    stepKeys: ['fh_disclosure_s1', 'fh_disclosure_s2', 'fh_disclosure_s3'],
  },
  {
    id: 'fto',
    titleKey: 'fh_fto_title',
    descKey: 'fh_fto_desc',
    categoryKey: 'feature_cat_high_impact',
    categoryColor: 'blue',
    icon: <Map className="w-5 h-5" />,
    api: 'POST /fto/check',
    stepKeys: ['fh_fto_s1', 'fh_fto_s2', 'fh_fto_s3'],
  },
  {
    id: 'label',
    titleKey: 'fh_label_title',
    descKey: 'fh_label_desc',
    categoryKey: 'feature_cat_compliance',
    categoryColor: 'amber',
    icon: <FileWarning className="w-5 h-5" />,
    api: 'POST /label/analyze',
    stepKeys: ['fh_label_s1', 'fh_label_s2', 'fh_label_s3'],
  },
  {
    id: 'roadmap',
    titleKey: 'regulatory_roadmap',
    descKey: 'fh_roadmap_desc',
    categoryKey: 'feature_cat_roadmap',
    categoryColor: 'violet',
    icon: <Route className="w-5 h-5" />,
    api: 'GET /roadmap/{id}',
    stepKeys: ['fh_roadmap_s1', 'fh_roadmap_s2', 'fh_roadmap_s3', 'fh_roadmap_s4', 'fh_roadmap_s5', 'fh_roadmap_s6'],
  },
  {
    id: 'whitespace',
    titleKey: 'fh_whitespace_title',
    descKey: 'fh_whitespace_desc',
    categoryKey: 'feature_cat_discovery',
    categoryColor: 'emerald',
    icon: <Sparkles className="w-5 h-5" />,
    api: 'GET /whitespace/{id}',
    stepKeys: ['fh_whitespace_s1', 'fh_whitespace_s2', 'fh_whitespace_s3'],
  },
  {
    id: 'abs',
    titleKey: 'fh_abs_title',
    descKey: 'fh_abs_desc',
    categoryKey: 'feature_cat_ayurveda',
    categoryColor: 'emerald',
    icon: <Leaf className="w-5 h-5" />,
    api: 'GET /abs/{id}',
    stepKeys: ['fh_abs_s1', 'fh_abs_s2', 'fh_abs_s3'],
  },
  {
    id: 'evidence-matrix',
    titleKey: 'evidence_matrix',
    descKey: 'fh_evidence_matrix_desc',
    categoryKey: 'feature_cat_evidence',
    categoryColor: 'cyan',
    icon: <ClipboardList className="w-5 h-5" />,
    api: 'GET /evidence/matrix/{id}',
    stepKeys: ['fh_evidence_matrix_s1', 'fh_evidence_matrix_s2', 'fh_evidence_matrix_s3'],
  },
  {
    id: 'claim-safety',
    titleKey: 'claim_safety_intelligence',
    descKey: 'fh_claim_safety_desc',
    categoryKey: 'feature_cat_safety',
    categoryColor: 'red',
    icon: <ShieldCheck className="w-5 h-5" />,
    api: 'POST /intelligence/claim-safety/analyze',
    stepKeys: ['fh_claim_safety_s1', 'fh_claim_safety_s2', 'fh_claim_safety_s3'],
  },
  {
    id: 'evidence-quality',
    titleKey: 'evidence_quality_intelligence',
    descKey: 'fh_evidence_quality_desc',
    categoryKey: 'feature_cat_quality',
    categoryColor: 'cyan',
    icon: <FlaskConical className="w-5 h-5" />,
    api: 'GET /intelligence/evidence-quality/{id}',
    stepKeys: ['fh_evidence_quality_s1', 'fh_evidence_quality_s2', 'fh_evidence_quality_s3'],
  },
  {
    id: 'bio-resource',
    titleKey: 'bio_resource_intelligence',
    descKey: 'fh_bio_resource_desc',
    categoryKey: 'feature_cat_ayurveda',
    categoryColor: 'emerald',
    icon: <Sprout className="w-5 h-5" />,
    api: 'GET /intelligence/bio-resource/{id}',
    stepKeys: ['fh_bio_resource_s1', 'fh_bio_resource_s2', 'fh_bio_resource_s3'],
  },
  {
    id: 'product-classifier',
    titleKey: 'product_classifier',
    descKey: 'fh_product_classifier_desc',
    categoryKey: 'feature_cat_classification',
    categoryColor: 'violet',
    icon: <Layers className="w-5 h-5" />,
    api: 'POST /intelligence/product-classify',
    stepKeys: ['fh_product_classifier_s1', 'fh_product_classifier_s2', 'fh_product_classifier_s3'],
  },
  {
    id: 'export-readiness',
    titleKey: 'export_readiness',
    descKey: 'fh_export_readiness_desc',
    categoryKey: 'feature_cat_export',
    categoryColor: 'blue',
    icon: <FileBadge className="w-5 h-5" />,
    api: 'GET /intelligence/export-readiness/{id}',
    stepKeys: ['fh_export_readiness_s1', 'fh_export_readiness_s2', 'fh_export_readiness_s3'],
  },
  {
    id: 'terminology-mapper',
    titleKey: 'terminology_mapper',
    descKey: 'fh_terminology_mapper_desc',
    categoryKey: 'feature_cat_rag',
    categoryColor: 'amber',
    icon: <BookMarked className="w-5 h-5" />,
    api: 'POST /intelligence/terminology/map',
    stepKeys: ['fh_terminology_mapper_s1', 'fh_terminology_mapper_s2', 'fh_terminology_mapper_s3'],
  },
  {
    id: 'dossier',
    titleKey: 'dossier_export',
    descKey: 'fh_dossier_desc',
    categoryKey: 'feature_cat_export',
    categoryColor: 'blue',
    icon: <FileDown className="w-5 h-5" />,
    api: 'POST /export/dossier',
    stepKeys: ['fh_dossier_s1', 'fh_dossier_s2', 'fh_dossier_s3'],
  },
  {
    id: 'expert',
    titleKey: 'fh_expert_title',
    descKey: 'fh_expert_desc',
    categoryKey: 'feature_cat_expert_review',
    categoryColor: 'violet',
    icon: <Scale className="w-5 h-5" />,
    api: 'GET /expert/package/{id}',
    stepKeys: ['fh_expert_s1', 'fh_expert_s2', 'fh_expert_s3'],
  },
  {
    id: 'what-if',
    titleKey: 'what_if',
    descKey: 'fh_what_if_desc',
    categoryKey: 'feature_cat_simulation',
    categoryColor: 'amber',
    icon: <RefreshCw className="w-5 h-5" />,
    api: 'POST /what-if/simulate',
    stepKeys: ['fh_what_if_s1', 'fh_what_if_s2', 'fh_what_if_s3'],
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
  const { lang } = useLang();
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 flex-wrap">
        <HerbSprig className="w-6 h-6 text-emerald-500" />
        <Sparkles className="w-4 h-4 text-blue-600" />
        <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">{t('feature_hub_title', lang)}</h2>
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
                  {t(f.categoryKey, lang)}
                </span>
              </div>
              <h3 className="text-sm font-bold text-slate-900 font-display mb-1.5">{t(f.titleKey, lang)}</h3>
              <p className="text-xs text-slate-500 mb-4 leading-relaxed">{t(f.descKey, lang)}</p>
              <div className="mt-auto space-y-1.5 mb-4">
                {f.stepKeys.map((step, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px] text-slate-600">
                    <span className="w-1 h-1 rounded-full bg-slate-400" />
                    {t(step, lang)}
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-emerald-200">
                <code className="text-[10px] text-blue-600/70 font-mono">{f.api}</code>
                <span className="flex items-center gap-1 text-xs font-semibold text-blue-600 group-hover:text-blue-500 transition">
                  {t('feature_hub_open', lang)} <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </GlassCard>
          </TiltCard>
        ))}
      </div>
    </div>
  );
}
