'use client';
import React from 'react';
import { InnovationLabWorkspace } from '../../components/InnovationLabWorkspace';
import { useLang } from '../../lib/LangContext';
import { t } from '../../lib/i18n';

export default function InnovationLabPage() {
  const { lang } = useLang();
  return (
    <main className="flex-1 p-4 md:p-6 space-y-6 relative z-10 bg-[var(--bg-main)] min-h-screen">
      <div className="space-y-2 pb-4 border-b border-gov-rule">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-gov-navy font-display">{t('innovation_lab', lang)}</h1>
        <p className="text-gov-mute">{t('innovation_lab_sub', lang)}</p>
      </div>
      <InnovationLabWorkspace />
    </main>
  );
}