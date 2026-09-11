'use client';

import React, { useState } from 'react';
import { Network, ZoomIn, ZoomOut, RefreshCw, Filter, Search, Layers, BookOpen, FileText, CheckCircle2, Shield } from 'lucide-react';

interface GraphNode {
  id: string;
  label: string;
  category: 'ingredient' | 'patent' | 'paper' | 'regulation' | 'tkdl' | 'supplier';
  x: number;
  y: number;
  details: string;
  sourceAuthority?: string;
}

interface GraphEdge {
  from: string;
  to: string;
  label: string;
  color?: string;
}

export default function KnowledgeGraphView() {
  const [zoom, setZoom] = useState(1);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const nodes: GraphNode[] = [
    { id: 'n-ashwa', label: 'Withania somnifera (Ashwagandha)', category: 'ingredient', x: 220, y: 180, details: 'API Monograph API-VOL1-008. Adaptogenic root with withanolide A-D content.', sourceAuthority: 'Ayurvedic Pharmacopoeia of India' },
    { id: 'n-brahmi', label: 'Bacopa monnieri (Brahmi)', category: 'ingredient', x: 380, y: 160, details: 'API Monograph API-VOL2-014. Bacoside A/B active principles for cognitive calm.', sourceAuthority: 'Ayurvedic Pharmacopoeia of India' },
    { id: 'n-tkdl1', label: 'Charaka Samhita (Chikitsa 1)', category: 'tkdl', x: 180, y: 320, details: 'Classical reference on Medhya Rasayana and sleep revitalization (Nidrajanana).', sourceAuthority: 'CSIR / AYUSH TKDL Index' },
    { id: 'n-patent1', label: 'IN Patent App 202341098: Synergistic Sleep Ratio', category: 'patent', x: 500, y: 220, details: 'Pending patent claim on 1:1.2 withanolide-bacoside combination.', sourceAuthority: 'Indian Patent Office' },
    { id: 'n-paper1', label: 'Phytomedicine 2024: GABA-A Receptor Modulation', category: 'paper', x: 340, y: 300, details: 'Double-blind peer-reviewed study verifying sleep onset latency reduction.', sourceAuthority: 'PubMed / Peer-Reviewed' },
    { id: 'n-reg-fssai', label: 'FSSAI Ayurveda Aahara Reg 4', category: 'regulation', x: 120, y: 100, details: 'Positive list clearance under Schedule I for dietary botanical foods.', sourceAuthority: 'FSSAI Official Gazette 2022' },
    { id: 'n-reg-fda', label: 'US FDA 21 CFR 101.93 (DSHEA)', category: 'regulation', x: 480, y: 80, details: 'Permitted structure/function claim standard for dietary supplements.', sourceAuthority: 'US FDA Title 21' },
    { id: 'n-supp1', label: 'Organic India / Kerala Bio-Reserves', category: 'supplier', x: 100, y: 240, details: 'NABL Certified organic GAP (Good Agricultural Practices) source.', sourceAuthority: 'National Biodiversity Authority (NBA)' }
  ];

  const edges: GraphEdge[] = [
    { from: 'n-ashwa', to: 'n-tkdl1', label: 'Classical Prior Art', color: '#f59e0b' },
    { from: 'n-brahmi', to: 'n-tkdl1', label: 'Classical Prior Art', color: '#f59e0b' },
    { from: 'n-ashwa', to: 'n-paper1', label: 'Clinical Evidence', color: '#10b981' },
    { from: 'n-brahmi', to: 'n-paper1', label: 'Clinical Evidence', color: '#10b981' },
    { from: 'n-ashwa', to: 'n-patent1', label: 'Claimed In Form 1', color: '#38bdf8' },
    { from: 'n-brahmi', to: 'n-patent1', label: 'Claimed In Form 1', color: '#38bdf8' },
    { from: 'n-ashwa', to: 'n-reg-fssai', label: 'Schedule I Positive List', color: '#a855f7' },
    { from: 'n-ashwa', to: 'n-reg-fda', label: 'Old Dietary Ingredient', color: '#a855f7' },
    { from: 'n-ashwa', to: 'n-supp1', label: 'Traceable Sourcing Origin', color: '#14b8a6' }
  ];

  const categoryColors = {
    ingredient: 'bg-emerald-100 text-emerald-700 border-emerald-300',
    patent: 'bg-cyan-100 text-cyan-700 border-cyan-300',
    paper: 'bg-emerald-100 text-emerald-700 border-emerald-300',
    regulation: 'bg-violet-100 text-violet-700 border-violet-300',
    tkdl: 'bg-amber-100 text-amber-700 border-amber-300',
    supplier: 'bg-teal-100 text-teal-700 border-teal-300'
  };

  const filteredNodes = nodes.filter(n => {
    const matchesCategory = selectedCategory === 'all' || n.category === selectedCategory;
    const matchesSearch = n.label.toLowerCase().includes(searchQuery.toLowerCase()) || n.details.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-4">
      {/* Graph Toolbar */}
      <div className="glass-panel p-4 rounded-2xl border border-emerald-200 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <Network className="w-5 h-5 text-emerald-600" />
          <h3 className="text-base font-bold text-slate-900 font-display">
            Interactive Ayurveda Knowledge Graph Canvas
          </h3>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search graph entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-emerald-50/70 border border-emerald-200 rounded-lg pl-8 pr-2 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-emerald-50/70 border border-emerald-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-emerald-500"
          >
            <option value="all">All Categories</option>
            <option value="ingredient">Ingredients (API Monographs)</option>
            <option value="patent">Patents & Prior Art</option>
            <option value="paper">Peer-Reviewed Research</option>
            <option value="regulation">Statutory Regulations</option>
            <option value="tkdl">Traditional Knowledge (TKDL)</option>
            <option value="supplier">Certified Sourcing (NBA)</option>
          </select>

          <div className="flex items-center space-x-1 border border-emerald-200 rounded-lg p-0.5 bg-emerald-50/70">
            <button
              onClick={() => setZoom(Math.min(zoom + 0.15, 1.6))}
              className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-emerald-100"
              title="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoom(Math.max(zoom - 0.15, 0.6))}
              className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-emerald-100"
              title="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoom(1)}
              className="p-1 rounded text-slate-500 hover:text-slate-900 hover:bg-emerald-100"
              title="Reset view"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8 glass-panel rounded-2xl p-4 border border-emerald-200 relative h-[480px] overflow-hidden">
          {/* SVG Canvas with Interactive Nodes */}
          <div
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'top left',
              transition: 'transform 0.2s ease-out'
            }}
            className="w-[700px] h-[450px] relative"
          >
            {/* SVG Connecting Edges */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              {edges.map((edge, idx) => {
                const source = nodes.find(n => n.id === edge.from);
                const target = nodes.find(n => n.id === edge.to);
                if (!source || !target) return null;

                return (
                  <g key={idx}>
                    <line
                      x1={source.x + 60}
                      y1={source.y + 20}
                      x2={target.x + 60}
                      y2={target.y + 20}
                      stroke={edge.color || '#10b981'}
                      strokeWidth="1.5"
                      strokeDasharray="4 2"
                      opacity="0.6"
                    />
                  </g>
                );
              })}
            </svg>

            {/* Interactive Draggable-style Nodes */}
            {filteredNodes.map((node) => {
              const isSelected = selectedNode?.id === node.id;
              return (
                <div
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  style={{
                    position: 'absolute',
                    left: `${node.x}px`,
                    top: `${node.y}px`
                  }}
                  className={`p-2.5 rounded-xl border transition-all duration-200 cursor-pointer max-w-[150px] shadow-lg backdrop-blur-md ${
                    categoryColors[node.category]
                  } ${
                    isSelected ? 'ring-2 ring-slate-900 scale-110 z-30' : 'hover:scale-105 z-10'
                  }`}
                >
                  <div className="text-[10px] font-bold uppercase tracking-wider opacity-75">{node.category}</div>
                  <div className="text-xs font-bold truncate text-slate-900">{node.label}</div>
                </div>
              );
            })}
          </div>

          <div className="absolute bottom-3 left-3 text-[10px] text-slate-600 bg-emerald-50/70 px-2 py-1 rounded-md border border-emerald-200">
            Click any entity node to inspect evidence relationships & statutory metadata
          </div>
        </div>

        {/* Right Details Panel */}
        <div className="lg:col-span-4 glass-panel rounded-2xl p-5 border border-emerald-200 space-y-4 h-[480px] overflow-y-auto">
          {selectedNode ? (
            <div className="space-y-4">
              <div>
                <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded-full border ${categoryColors[selectedNode.category]}`}>
                  {selectedNode.category}
                </span>
                <h4 className="text-base font-bold text-slate-900 mt-1.5 leading-snug">{selectedNode.label}</h4>
                {selectedNode.sourceAuthority && (
                  <span className="text-xs text-emerald-600 font-semibold block mt-0.5">
                    Authority: {selectedNode.sourceAuthority}
                  </span>
                )}
              </div>

              <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-slate-600 leading-relaxed">
                {selectedNode.details}
              </div>

              {/* Connected Relationships */}
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-2">
                  Connected Graph Relationships:
                </span>
                <div className="space-y-2 text-xs">
                  {edges.filter(e => e.from === selectedNode.id || e.to === selectedNode.id).map((e, i) => {
                    const otherId = e.from === selectedNode.id ? e.to : e.from;
                    const otherNode = nodes.find(n => n.id === otherId);
                    return (
                      <div key={i} className="p-2.5 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-center justify-between">
                        <span className="text-slate-700 font-medium">{otherNode?.label}</span>
                        <span className="text-[10px] font-mono text-emerald-600">{e.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 space-y-2">
              <Network className="w-8 h-8 text-slate-500 animate-pulse" />
              <p className="text-xs">Select any node in the knowledge canvas to inspect its source provenance and prior-art connections.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
