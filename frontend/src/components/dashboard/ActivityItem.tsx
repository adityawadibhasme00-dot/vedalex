'use client';
import React from 'react';
import clsx from 'clsx';
import { useLang } from '../../lib/LangContext';
import { t } from '../../lib/i18n';

interface ActivityItemProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  time: string;
  status: 'completed' | 'in_progress' | 'failed';
}

const statusStyles: Record<ActivityItemProps['status'], { badge: string; labelKey: string }> = {
  completed: { badge: 'bg-green-50 text-gov-green', labelKey: 'rd_status_completed' },
  in_progress: { badge: 'bg-blue-50 text-gov-blue', labelKey: 'rd_status_in_progress' },
  failed: { badge: 'bg-red-50 text-red-700', labelKey: 'common_failed' },
};

export function ActivityItem({ icon, title, description, time, status }: ActivityItemProps) {
  const { lang } = useLang();
  const s = statusStyles[status];
  return (
    <div className="flex items-start gap-4 p-4 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
      <div className="h-10 w-10 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
        <span className="text-gray-600">{icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-gray-900 truncate">{title}</h4>
        <p className="text-sm text-gray-600 mt-0.5 leading-snug">{description}</p>
      </div>
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 flex-shrink-0 sm:text-right">
        <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', s.badge)}>{t(s.labelKey, lang)}</span>
        <span className="text-sm text-gray-500">{time}</span>
      </div>
    </div>
  );
}