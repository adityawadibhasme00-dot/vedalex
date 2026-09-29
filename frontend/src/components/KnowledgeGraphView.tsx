'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Network, ZoomIn, ZoomOut, RefreshCw, Filter, Search, Layers, BookOpen,
  FileText, ShieldCheck, Loader2, AlertTriangle, Sparkles, ExternalLink,
} from 'lucide-react';
import {
  KnowledgeGraphNode,
  KnowledgeGraphEdge,
  InnovationKnowledgeGraphResponse,
} from '../types';
import { getInnovationGraph, getPassportInnovationGraph } from '../lib/api';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface DemoInnovation {
  id: string;
  label: string;
  hint: string;
  ingredients: string[];
}

const DEMO_INNOVATIONS: DemoInnovation[] = [
  { id: 'ashwagandha', label: 'Ashwagandha', hint: 'kg_hint_single', ingredients: ['Ashwagandha'] },
  { id: 'brahmi', label: 'Brahmi', hint: 'kg_hint_single', ingredients: ['Brahmi'] },
  { id: 'neem', label: 'Neem', hint: 'kg_hint_single', ingredients: ['Neem'] },
  { id: 'guduchi', label: 'Guduchi', hint: 'kg_hint_single', ingredients: ['Guduchi'] },
  { id: 'triphala', label: 'Triphala', hint: 'kg_hint_poly', ingredients: ['Triphala'] },
  { id: 'custom', label: 'Custom Polyherbal', hint: 'kg_hint_type', ingredients: [] },
];

const CATEGORY_STYLE: Record<string, { chip: string; color: string }> = {
  ingredient: { chip: 'bg-emerald-100 text-emerald-700 border-emerald-300', color: '#16a34a' },
  botanical: { chip: 'bg-lime-100 text-lime-700 border-lime-300', color: '#65a30d' },
  monograph: { chip: 'bg-violet-100 text-violet-700 border-violet-300', color: '#7c3aed' },
  regulation: { chip: 'bg-amber-100 text-amber-700 border-amber-300', color: '#d97706' },
  authority: { chip: 'bg-blue-100 text-blue-700 border-blue-300', color: '#2563eb' },
  jurisdiction: { chip: 'bg-sky-100 text-sky-700 border-sky-300', color: '#0ea5e9' },
  tkdl: { chip: 'bg-orange-100 text-orange-700 border-orange-300', color: '#f59e0b' },
  patent: { chip: 'bg-cyan-100 text-cyan-700 border-cyan-300', color: '#0284c7' },
  paper: { chip: 'bg-emerald-100 text-emerald-700 border-emerald-300', color: '#10b981' },
  safety: { chip: 'bg-red-100 text-red-700 border-red-300', color: '#ef4444' },
  supplier: { chip: 'bg-teal-100 text-teal-700 border-teal-300', color: '#14b8a6' },
  source: { chip: 'bg-slate-100 text-slate-700 border-slate-300', color: '#64748b' },
};

const CATEGORY_LABELS: Record<string, string> = {
  ingredient: 'kg_cat_ingredient',
  botanical: 'kg_cat_botanical',
  monograph: 'kg_cat_monograph',
  regulation: 'kg_cat_regulation',
  authority: 'kg_cat_authority',
  jurisdiction: 'kg_cat_jurisdiction',
  tkdl: 'kg_cat_tkdl',
  patent: 'kg_cat_patent',
  paper: 'kg_cat_paper',
  safety: 'kg_cat_safety',
  supplier: 'kg_cat_supplier',
  source: 'kg_cat_source',
};

const CURATED_COLLECTIONS = [
  'regulations', 'patents', 'biodiversity',
  'traditional_knowledge', 'quality_standards', 'safety',
];

function nodeStyle(category: string) {
  return CATEGORY_STYLE[category] || CATEGORY_STYLE.source;
}

export default function KnowledgeGraphView({ passportId }: { passportId?: string }) {
  const { lang } = useLang();
  const [demoId, setDemoId] = useState<string>(passportId ? 'passport' : 'ashwagandha');
  const [customText, setCustomText] = useState('Ashwagandha, Brahmi');
  const [graph, setGraph] = useState<InnovationKnowledgeGraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [zoom, setZoom] = useState(1);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedNode, setSelectedNode] = useState<KnowledgeGraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError('');
    setGraph(null);
    setSelectedNode(null);
    try {
      let data: InnovationKnowledgeGraphResponse;
      if (demoId === 'passport' && passportId) {
        data = await getPassportInnovationGraph(passportId);
      } else {
        const demo = DEMO_INNOVATIONS.find((d) => d.id === demoId);
        let ingredients = demo?.ingredients || [];
        if (demoId === 'custom') {
          ingredients = customText.split(',').map((s) => s.trim()).filter(Boolean);
        }
        if (ingredients.length === 0) {
          throw new Error(t('kg_enter_ingredient', lang));
        }
        data = await getInnovationGraph({
          ingredients,
          innovation_title: ingredients.length > 1 ? customText : demo?.label,
          passport_id: passportId && demoId !== 'passport' ? passportId : undefined,
        });
      }
      setGraph(data);
    } catch (e: any) {
      setError(e?.message || t('kg_load_failed', lang));
    } finally {
      setLoading(false);
    }
  }, [demoId, passportId, customText]);

  useEffect(() => {
    loadGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demoId, passportId]);

  const currentKind = (() => {
    const raw = graph?.selected_innovation.kind ||
      (graph ? 'Single Herb' : (demoId === 'triphala' || demoId === 'custom' ? 'Polyherbal Formulation' : 'Single Herb'));
    if (/poly/i.test(raw)) return t('kg_kind_poly', lang);
    if (/single/i.test(raw)) return t('kg_kind_single', lang);
    return raw;
  })();

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];

  const filteredNodes = nodes.filter((n) => {
    const matchesCategory = selectedCategory === 'all' || n.category === selectedCategory;
    const needle = searchQuery.trim().toLowerCase();
    const matchesSearch =
      !needle ||
      n.label.toLowerCase().includes(needle) ||
      (n.details || '').toLowerCase().includes(needle) ||
      (n.sourceAuthority || '').toLowerCase().includes(needle);
    return matchesCategory && matchesSearch;
  });

  const worldHeight = Math.max(450, ...nodes.map((n) => n.y + 96));

  return (
    <div className="space-y-4">
      {/* Selected Innovation header */}
      <div className="glass-panel p-4 rounded-2xl border border-emerald-200 flex items-start gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          <Network className="w-5 h-5 text-emerald-600" />
          <div>
            <h3 className="text-base font-bold text-slate-900 font-display">
              {t('kg_title', lang)}
            </h3>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="px-2 py-0.5 rounded-full border border-emerald-300 bg-emerald-50 text-[10px] font-bold text-emerald-700">
                {t('kg_selected_chip', lang)}
              </span>
              {graph && (
                <span className="px-2 py-0.5 rounded-full border border-teal-300 bg-teal-50 text-[10px] font-bold text-teal-700">
                  {graph.selected_innovation.title} — {currentKind}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Innovation selector */}
      <div className="glass-panel p-4 rounded-2xl border border-emerald-200">
        <div className="flex items-center gap-2 mb-2.5">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <span className="text-xs font-bold text-slate-800">
            {t('kg_selector_label', lang)}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {passportId && (
            <button
              type="button"
              onClick={() => setDemoId('passport')}
              className={`px-3 py-1.5 rounded-xl border text-[11px] font-semibold transition ${
                demoId === 'passport'
                  ? 'bg-emerald-600 text-white border-emerald-600 shadow'
                  : 'bg-emerald-50/70 border-emerald-200 text-slate-600 hover:border-emerald-400'
              }`}
            >
              {t('kg_from_passport', lang)}
            </button>
          )}
          {DEMO_INNOVATIONS.map((demo) => (
            <button
              key={demo.id}
              type="button"
              onClick={() => setDemoId(demo.id)}
              className={`px-3 py-1.5 rounded-xl border text-[11px] font-semibold transition ${
                demoId === demo.id
                  ? 'bg-emerald-600 text-white border-emerald-600 shadow'
                  : 'bg-emerald-50/70 border-emerald-200 text-slate-600 hover:border-emerald-400'
              }`}
            >
              {demo.label}
              <span
                className={`ml-1.5 text-[9px] font-normal ${
                  demoId === demo.id ? 'text-white/70' : 'text-slate-400'
                }`}
              >
                {t(demo.hint, lang)}
              </span>
            </button>
          ))}
          {demoId === 'custom' && (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={customText}
                onChange={(e) => setCustomText(e.target.value)}
                placeholder={t('kg_custom_placeholder', lang)}
                className="bg-white border border-emerald-200 rounded-xl px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-emerald-500 min-w-[220px]"
              />
              <button
                type="button"
                onClick={loadGraph}
                className="px-3 py-1.5 rounded-xl bg-emerald-600 text-white text-[11px] font-bold hover:bg-emerald-700 transition"
              >
                {t('kg_render', lang)}
              </button>
            </div>
          )}
        </div>
      </div>

      {loading && (
        <div className="glass-panel rounded-2xl p-10 border border-emerald-200 flex items-center justify-center text-slate-500 gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-emerald-600" />
          <span className="text-xs">{t('kg_loading', lang)}</span>
        </div>
      )}

      {!loading && error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <div className="text-xs text-red-700 space-y-2">
            <div className="font-bold">{t('kg_compose_failed', lang)}</div>
            <div>{error}</div>
            <button
              type="button"
              onClick={loadGraph}
              className="px-3 py-1 rounded-lg bg-red-600 text-white text-[11px] font-bold hover:bg-red-700"
            >
              {t('kg_retry', lang)}
            </button>
          </div>
        </div>
      )}

      {!loading && !error && graph && !graph.evidence_found && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <div className="text-xs text-amber-800 space-y-1">
            <div className="font-bold">{t('kg_guard_title', lang)}</div>
            <div>{graph.evidence_note || t('kg_no_evidence', lang)}</div>
            <div className="text-[10px] text-amber-700/70">
              {t('kg_zero_retrieved', lang)}
            </div>
          </div>
        </div>
      )}

      {!loading && !error && graph && graph.nodes.length > 0 && (
        <>
          {/* Graph Toolbar */}
          <div className="glass-panel p-4 rounded-2xl border border-emerald-200 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <div className="flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  {t('kg_curated_label', lang)}
                </span>
              </div>
              <div className="flex flex-wrap gap-1">
                {CURATED_COLLECTIONS.filter((c) => graph.collections_used.includes(c)).map((c) => (
                  <span key={c} className="px-1.5 py-0.5 rounded-md bg-emerald-100 border border-emerald-300 text-[9px] font-mono text-emerald-700">
                    {c}
                  </span>
                ))}
                {graph.collections_used.filter((c) => !CURATED_COLLECTIONS.includes(c)).length > 0 && (
                  <span className="px-1.5 py-0.5 rounded-md bg-slate-100 border border-slate-300 text-[9px] font-mono text-slate-500">
                    +registry
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder={t('kg_search_placeholder', lang)}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-emerald-50/70 border border-emerald-200 rounded-lg pl-8 pr-2 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="flex items-center gap-1">
                <Filter className="w-3.5 h-3.5 text-slate-500" />
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="bg-emerald-50/70 border border-emerald-200 rounded-lg px-2 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-emerald-500"
                >
                  <option value="all">{t('kg_all_categories', lang)}</option>
                  {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>{t(label, lang)}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center space-x-1 border border-emerald-200 rounded-lg p-0.5 bg-emerald-50/70">
                <button
                  onClick={() => setZoom(Math.min(zoom + 0.15, 1.6))}
                  className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-emerald-100"
                  title={t('kg_zoom_in', lang)}
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoom(Math.max(zoom - 0.15, 0.6))}
                  className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-emerald-100"
                  title={t('kg_zoom_out', lang)}
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoom(1)}
                  className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-emerald-100"
                  title={t('kg_reset_view', lang)}
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Main Canvas + Details */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-8 glass-panel rounded-2xl p-4 border border-emerald-200 relative overflow-auto max-h-[560px]">
              <div style={{ transform: `scale(${zoom})`, transformOrigin: 'top left', transition: 'transform 0.2s ease-out' }} className="relative" >
                <div className="w-[700px]" style={{ height: worldHeight }}>
                  <svg className="absolute inset-0 w-full h-full pointer-events-none">
                    {edges.map((edge, idx) => {
                      const source = nodes.find((n) => n.id === edge.from);
                      const target = nodes.find((n) => n.id === edge.to);
                      if (!source || !target) return null;
                      return (
                        <g key={idx}>
                          <line
                            x1={source.x + 72}
                            y1={source.y + 30}
                            x2={target.x + 72}
                            y2={target.y + 30}
                            stroke={edge.color || '#10b981'}
                            strokeWidth="1.5"
                            strokeDasharray="4 2"
                            opacity="0.55"
                          />
                        </g>
                      );
                    })}
                  </svg>

                  {filteredNodes.map((node) => {
                    const isSelected = selectedNode?.id === node.id;
                    const style = nodeStyle(node.category);
                    return (
                      <div
                        key={node.id}
                        onClick={() => setSelectedNode(node)}
                        style={{ position: 'absolute', left: `${node.x}px`, top: `${node.y}px` }}
                        className={`w-[148px] h-[60px] p-2.5 rounded-xl border transition-all duration-200 cursor-pointer shadow-lg backdrop-blur-md flex flex-col justify-center ${style.chip} ${
                          isSelected ? 'ring-2 ring-slate-900 scale-110 z-30' : 'hover:scale-105 z-10'
                        }`}
                      >
                        <div className="text-[10px] font-bold uppercase tracking-wider opacity-75">{node.category}</div>
                        <div className="text-xs font-bold truncate text-slate-900">{node.label}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="sticky bottom-2 left-2 w-fit mt-2 text-[10px] text-slate-600 bg-emerald-50/70 px-2 py-1 rounded-md border border-emerald-200">
                {t('kg_click_node', lang)}
              </div>
            </div>

            {/* Right Details Panel */}
            <div className="lg:col-span-4 glass-panel rounded-2xl p-5 border border-emerald-200 space-y-4 max-h-[560px] overflow-y-auto">
              {selectedNode ? (
                <div className="space-y-4">
                  <div>
                    <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded-full border ${nodeStyle(selectedNode.category).chip}`}>
                      {selectedNode.category}
                    </span>
                    <h4 className="text-base font-bold text-slate-900 mt-1.5 leading-snug">{selectedNode.label}</h4>
                    {selectedNode.sourceAuthority && (
                      <span className="text-xs text-emerald-600 font-semibold block mt-0.5">
                        {t('kg_authority', lang)} {selectedNode.sourceAuthority}
                      </span>
                    )}
                    {selectedNode.collection && (
                      <span className="text-[10px] font-mono text-slate-500 block mt-0.5">
                        {t('kg_from_collection', lang)} {selectedNode.collection}
                      </span>
                    )}
                    {selectedNode.sourceUrl && (
                      <a
                        href={selectedNode.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1 inline-flex items-center gap-1 text-[11px] font-bold text-blue-600 hover:underline"
                      >
                        {t('kg_open_source', lang)} <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>

                  <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-slate-600 leading-relaxed">
                    {selectedNode.details || t('kg_no_details', lang)}
                  </div>

                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-2">
                      {t('kg_connected', lang)}
                    </span>
                    <div className="space-y-2 text-xs">
                      {edges
                        .filter((e) => e.from === selectedNode.id || e.to === selectedNode.id)
                        .map((e, i) => {
                          const otherId = e.from === selectedNode.id ? e.to : e.from;
                          const otherNode = nodes.find((n) => n.id === otherId);
                          return (
                            <div
                              key={i}
                              className="p-2.5 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between gap-2"
                            >
                              <span className="text-slate-700 font-medium truncate">{otherNode?.label}</span>
                              <span className="text-[10px] font-mono text-emerald-600 flex-shrink-0">{e.label}</span>
                            </div>
                          );
                        })}
                      {edges.filter((e) => e.from === selectedNode.id || e.to === selectedNode.id).length === 0 && (
                        <div className="text-[10px] text-slate-400">
                          {t('kg_no_relationships', lang)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 space-y-2">
                  <Network className="w-8 h-8 text-slate-500 animate-pulse" />
                  <p className="text-xs">
                    {t('kg_select_node', lang)}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Judge line / honesty note */}
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-4 text-xs text-slate-600 leading-relaxed flex items-start gap-2.5">
            <BookOpen className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-slate-700 block mb-0.5">{t('kg_how_built', lang)}</span>
              {t('kg_judge_1', lang)}
              <span className="block mt-1 text-[10px] text-slate-400">{graph.disclaimer}</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}