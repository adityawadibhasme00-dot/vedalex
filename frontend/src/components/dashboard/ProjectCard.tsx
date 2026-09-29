'use client';
import React from 'react';
import clsx from 'clsx';
import { useLang } from '../../lib/LangContext';
import { t } from '../../lib/i18n';

export type ProjectStatus = 'completed' | 'in_progress' | 'queued';

interface ProjectCardProps {
  title: string;
  agent: string;
  status: ProjectStatus;
  progress: number;
  date: string;
  href?: string;
}

const statusLabel: Record<ProjectStatus, { badge: string; labelKey: string }> = {
  completed: { badge: 'bg-green-50 text-gov-green', labelKey: 'rd_status_completed' },
  in_progress: { badge: 'bg-blue-50 text-gov-blue', labelKey: 'rd_status_in_progress' },
  queued: { badge: 'bg-amber-50 text-amber-700', labelKey: 'common_ready_to_run' },
};

export function ProjectCard({ title, agent, status, progress, date, href }: ProjectCardProps) {
  const { lang } = useLang();
  const card = (
    <div
      className={clsx(
        'block bg-white rounded-xl border border-gov-rule p-6 hover:shadow-md transition-shadow group',
        href && 'cursor-pointer',
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2">{title}</h3>
          <p className="text-sm text-gray-600">{agent}</p>
        </div>
        <span className={clsx('px-2 py-1 rounded-full text-xs font-medium flex-shrink-0', statusLabel[status].badge)}>
          {t(statusLabel[status].labelKey, lang)}
        </span>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-gray-600">{t('common_progress', lang)}</span>
          <span className="font-medium text-gray-900">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-full rounded-full transition-all duration-700',
              status === 'completed' && 'bg-gov-green',
              status === 'in_progress' && 'bg-gov-blue',
              status === 'queued' && 'bg-amber-500',
            )}
            style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
          />
        </div>
      </div>

      <div className="text-sm text-gray-500">{date}</div>
    </div>
  );

  if (href) {
    return (
      <a href={href} className="block">
        {card}
      </a>
    );
  }
  return card;
}