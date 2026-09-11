'use client';

import React from 'react';
import { Sparkles, ShieldCheck, ArrowRight, BookOpen, Layers, CheckCircle2, Award } from 'lucide-react';

interface HeroSectionProps {
  onStartIntake: () => void;
  onExploreFeatures: () => void;
  currentLang: string;
}

export default function HeroSection({
  onStartIntake,
  onExploreFeatures,
  currentLang
}: HeroSectionProps) {
  return (
    <div className="relative pt-6 pb-12 overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-5xl mx-auto text-center space-y-6 relative z-10 px-4">
        {/* Top Innovation Pill */}
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-white border border-emerald-200 text-xs text-emerald-700 shadow-xl backdrop-blur-xl animate-fade-in">
          <Sparkles className="w-3.5 h-3.5 text-amber-600 animate-spin" />
          <span className="font-semibold">AI-Powered Innovation Passport for Ayurveda IP & Global Regulations</span>
        </div>

        {/* Hero Title with Gradient */}
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 font-display leading-tight">
          From Ayurvedic Wisdom to <br />
          <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-amber-400 bg-clip-text text-transparent">
            Defensible Global IP & Compliance
          </span>
        </h1>

        {/* Subtitle */}
        <p className="text-sm sm:text-base text-slate-600 max-w-3xl mx-auto leading-relaxed font-sans">
          The first multi-jurisdiction decision-support platform with a <strong>deterministic rules engine</strong> underneath the LLM. Zero hallucinations, 100% source-traceable statutory citations across India (ASU / Aahara), USA (FDA DSHEA), and Canada (NHPR).
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3.5 pt-2">
          <button
            onClick={onStartIntake}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-sm shadow-xl shadow-emerald-900/40 flex items-center space-x-2 transition transform hover:-translate-y-0.5"
          >
            <span>Launch Innovation Passport</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={onExploreFeatures}
            className="px-6 py-3 rounded-xl glass-panel hover:bg-emerald-50 text-slate-700 font-semibold text-sm border border-emerald-200 flex items-center space-x-2 transition"
          >
            <Layers className="w-4 h-4 text-emerald-600" />
            <span>Explore 30+ Enterprise Modules</span>
          </button>
        </div>

        {/* Live Statistics Counters Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6 max-w-4xl mx-auto text-left">
          <div className="glass-panel p-4 rounded-xl border border-emerald-200">
            <span className="text-2xl font-extrabold text-emerald-600 font-display block">14,280+</span>
            <span className="text-xs text-slate-500">Classical Botanicals Indexed</span>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-emerald-200">
            <span className="text-2xl font-extrabold text-amber-600 font-display block">0.00%</span>
            <span className="text-xs text-slate-500">Unsupported Claim Rate (UCR)</span>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-emerald-200">
            <span className="text-2xl font-extrabold text-cyan-600 font-display block">&lt; 12s</span>
            <span className="text-xs text-slate-500">p95 Retrieval Latency SLO</span>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-emerald-200">
            <span className="text-2xl font-extrabold text-violet-600 font-display block">10 Scripts</span>
            <span className="text-xs text-slate-500">Indic NLP Multilingual Parity</span>
          </div>
        </div>

        {/* Trusted Statutory Regimes Banner */}
        <div className="pt-4 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500 border-t border-emerald-200">
          <span className="flex items-center space-x-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Ministry of AYUSH (Drugs & Cosmetics Act)</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>FSSAI Ayurveda Aahara Regs 2022</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Indian Patent Act Sec 3(p) TK</span>
          </span>
          <span className="flex items-center space-x-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>US FDA DSHEA & Health Canada NHPR</span>
          </span>
        </div>
      </div>
    </div>
  );
}
