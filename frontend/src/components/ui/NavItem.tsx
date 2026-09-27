'use client';
import React from 'react';
import clsx from 'clsx';

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  href?: string;
  onClick?: () => void;
  active?: boolean;
  collapsed?: boolean;
}

export function NavItem({ icon, label, href, onClick, active = false, collapsed = false }: NavItemProps) {
  const className = clsx(
    'relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-colors group',
    active
      ? 'bg-emerald-50 text-emerald-800 font-semibold'
      : 'text-gray-700 hover:bg-gray-100 hover:text-emerald-800',
  );

  const content = (
    <>
      {active && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-full bg-gradient-to-b from-emerald-500 to-teal-500" />}
      <span className={clsx('flex-shrink-0', active ? 'text-emerald-600' : 'text-gray-500 group-hover:text-emerald-600')}>
        {icon}
      </span>
      {!collapsed && <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">{label}</span>}
      {collapsed && (
        <div className="absolute left-full ml-2 px-2 py-1 bg-white border border-emerald-200 rounded-lg text-xs text-gray-700 whitespace-nowrap opacity-0 group-hover:opacity-100 transition pointer-events-none z-50 shadow-xl">
          {label}
        </div>
      )}
    </>
  );

  if (href) {
    return (
      <a href={href} onClick={onClick} className={clsx(className, 'w-full')} title={collapsed ? label : undefined}>
        {content}
      </a>
    );
  }

  return (
    <button onClick={onClick} className={clsx(className, 'w-full')} title={collapsed ? label : undefined}>
      {content}
    </button>
  );
}