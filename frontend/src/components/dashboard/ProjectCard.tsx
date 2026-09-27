'use client';
import React from 'react';
import clsx from 'clsx';

export type ProjectStatus = 'completed' | 'in_progress' | 'queued';

interface ProjectCardProps {
  title: string;
  agent: string;
  status: ProjectStatus;
  progress: number;
  date: string;
  href?: string;
}

const statusLabel: Record<ProjectStatus, { badge: string; text: string }> = {
  completed: { badge: 'bg-emerald-100 text-emerald-700', text: 'Completed' },
  in_progress: { badge: 'bg-blue-100 text-blue-700', text: 'In Progress' },
  queued: { badge: 'bg-amber-100 text-amber-700', text: 'Ready to Run' },
};

export function ProjectCard({ title, agent, status, progress, date, href }: ProjectCardProps) {
  const card = (
    <div
      className={clsx(
        'block bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-lg hover:-translate-y-0.5 transition-all group',
        href && 'cursor-pointer',
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2">{title}</h3>
          <p className="text-sm text-gray-600">{agent}</p>
        </div>
        <span className={clsx('px-2 py-1 rounded-full text-xs font-medium flex-shrink-0', statusLabel[status].badge)}>
          {statusLabel[status].text}
        </span>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-gray-600">Progress</span>
          <span className="font-medium text-gray-900">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-full bg-emerald-600 rounded-full transition-all duration-700',
              status === 'completed' && 'bg-emerald-600',
              status === 'in_progress' && 'bg-blue-600',
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