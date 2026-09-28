'use client';
import React from 'react';
import { InnovationLabWorkspace } from '../../components/InnovationLabWorkspace';

export default function InnovationLabPage() {
  return (
    <main className="flex-1 p-4 md:p-6 space-y-6 relative z-10 bg-[var(--bg-main)] min-h-screen">
      <div className="space-y-2 pb-4 border-b border-gov-rule">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-gov-navy font-display">Innovation AI Lab</h1>
        <p className="text-gov-mute">AI-assisted research, engineering, IP, scientific, and materials workflows</p>
      </div>
      <InnovationLabWorkspace />
    </main>
  );
}