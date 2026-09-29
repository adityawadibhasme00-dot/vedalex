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
    'relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors group',
    active
      ? 'bg-gov-wash text-gov-navy font-semibold border border-gov-rule'
      : 'text-gray-700 hover:bg-gov-wash hover:text-gov-navy',
  );

  const content = (
    <>
      {active && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-gov-blue" />}
      <span className={clsx('flex-shrink-0', active ? 'text-gov-blue' : 'text-gray-500 group-hover:text-gov-blue')}>
        {icon}
      </span>
      {!collapsed && <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">{label}</span>}
      {collapsed && (
        <div className="absolute left-full ml-2 px-2 py-1 bg-white border border-gray-300 rounded-md text-xs text-gray-700 whitespace-nowrap opacity-0 group-hover:opacity-100 transition pointer-events-none z-50 shadow-md">
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