'use client';
import React from 'react';
import { InnovationLabWorkspace } from '../../components/InnovationLabWorkspace';

export default function InnovationLabPage() {
  return (
    <main className="flex-1 p-4 md:p-6 space-y-6 relative z-10 bg-gray-50 min-h-screen">
      <div className="space-y-2">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">Innovation AI Lab</h1>
        <p className="text-slate-600">AI-assisted research, engineering, IP, scientific, and materials workflows</p>
      </div>
      <InnovationLabWorkspace />
    </main>
  );
}