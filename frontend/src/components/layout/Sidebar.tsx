'use client';
import React from 'react';
import {
  LayoutDashboard, Bot, FlaskConical, FileText, Search, ClipboardList,
  Sprout, Layers, FileBadge, RefreshCw, FileDown, Settings,
  HelpCircle, LogOut, Home, ChevronsLeft, ChevronsRight, X,
} from 'lucide-react';
import { InnolabAgent } from '../../lib/innolabApi';
import { NavItem } from '../ui/NavItem';

interface SidebarNav {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const MAIN_NAV: SidebarNav[] = [
  { id: 'overview', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { id: 'copilot', label: 'AI Assistant', icon: <Bot className="w-5 h-5" /> },
  { id: 'innolab', label: 'Innovation Lab', icon: <FlaskConical className="w-5 h-5" /> },
];

const KNOWLEDGE_NAV: SidebarNav[] = [
  { id: 'passport', label: 'Innovation Passport', icon: <FileText className="w-5 h-5" /> },
  { id: 'ipreg', label: 'IP & Regulatory Base', icon: <Search className="w-5 h-5" /> },
  { id: 'evidence', label: 'Evidence & Compliance', icon: <ClipboardList className="w-5 h-5" /> },
  { id: 'biores', label: 'Bio-Resource Intelligence', icon: <Sprout className="w-5 h-5" /> },
  { id: 'classify', label: 'Product Classifier', icon: <Layers className="w-5 h-5" /> },
  { id: 'market', label: 'Market Readiness', icon: <FileBadge className="w-5 h-5" /> },
  { id: 'whatif', label: 'What-If Simulator', icon: <RefreshCw className="w-5 h-5" /> },
  { id: 'dossier', label: 'Dossier Export', icon: <FileDown className="w-5 h-5" /> },
];

interface SidebarProps {
  activeTab: string;
  onNavigate: (tab: string) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  isOnline: boolean;
  offlineDraftCount: number;
  userName?: string;
  userRole?: string;
  onLogout: () => void;
  labAgents: InnolabAgent[];
  labAgentsLoaded: boolean;
  onOpenAgent: (slug: string) => void;
  onHome: () => void;
  lang: string;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

function NavLink({
  item, active, collapsed, onClick,
}: {
  item: SidebarNav;
  active: boolean;
  collapsed: boolean;
  onClick: () => void;
}) {
  return (
    <NavItem
      icon={item.icon}
      label={item.label}
      active={active}
      collapsed={collapsed}
      onClick={onClick}
    />
  );
}

export function Sidebar({
  activeTab, onNavigate, collapsed, onToggleCollapsed,
  isOnline, offlineDraftCount, userName, userRole,
  onLogout, labAgents, labAgentsLoaded, onOpenAgent, onHome,
  lang, mobileOpen, onCloseMobile,
}: SidebarProps) {
  const renderNav = (collapsedMode: boolean) => (
    <nav className="flex-1 overflow-y-auto py-3 space-y-5 px-2.5 no-scrollbar">
      {/* Main */}
      <div>
        {!collapsedMode && (
          <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400">Main</p>
        )}
        <div className="space-y-0.5">
          <button
            onClick={onHome}
            title={collapsedMode ? 'Home' : undefined}
            className="relative w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors group text-gray-700 hover:bg-gov-wash hover:text-gov-navy"
          >
            <span className="flex-shrink-0 text-gray-500 group-hover:text-gov-blue"><Home className="w-5 h-5" /></span>
            {!collapsedMode && <span className="text-[13px] font-medium">{'Home'}</span>}
          </button>
          {MAIN_NAV.map((item) => (
            <NavLink
              key={item.id}
              item={item}
              active={activeTab === item.id}
              collapsed={collapsedMode}
              onClick={() => onNavigate(item.id)}
            />
          ))}
        </div>
      </div>

      {/* Knowledge */}
      <div>
        {!collapsedMode && (
          <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400">Knowledge &amp; Analysis</p>
        )}
        <div className="space-y-0.5">
          {KNOWLEDGE_NAV.map((item) => (
            <NavLink
              key={item.id}
              item={item}
              active={activeTab === item.id}
              collapsed={collapsedMode}
              onClick={() => onNavigate(item.id)}
            />
          ))}
        </div>
      </div>

      {/* Lab agents quick links */}
      {!collapsedMode && labAgentsLoaded && labAgents.length > 0 && (
        <div>
          <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gov-blue">Lab Agents</p>
          <div className="space-y-0.5">
            {labAgents.slice(0, 6).map((a) => (
              <button
                key={a.slug}
                onClick={() => onOpenAgent(a.slug)}
                className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md text-left text-xs text-gray-600 hover:bg-gov-wash hover:text-gov-navy transition group"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-gov-blue flex-shrink-0" />
                <span className="truncate">{a.label}</span>
              </button>
            ))}
            {labAgents.length > 6 && (
              <button
                onClick={() => onNavigate('innolab')}
                className="w-full text-left px-3 py-1 text-[11px] text-gov-blue hover:text-gov-navy"
              >
                + {labAgents.length - 6} more in the lab
              </button>
            )}
          </div>
        </div>
      )}

      {/* User */}
      <div className="pt-1 border-t border-gray-100">
        <NavLink
          item={{ id: 'settings', label: 'Profile & Settings', icon: <Settings className="w-5 h-5" /> }}
          active={activeTab === 'settings'}
          collapsed={collapsedMode}
          onClick={() => onNavigate('settings')}
        />
        <a
          href="mailto:support@ipsakti.gov.in"
          title={collapsedMode ? 'Help & Support' : undefined}
          className="relative w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors group text-gray-700 hover:bg-gov-wash hover:text-gov-navy"
        >
          <span className="flex-shrink-0 text-gray-500 group-hover:text-gov-blue"><HelpCircle className="w-5 h-5" /></span>
          {!collapsedMode && <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">Help &amp; Support</span>}
        </a>
      </div>
    </nav>
  );

  const footer = (collapsedMode: boolean) => (
    <div className="border-t border-gray-100 p-3 space-y-2">
      {!collapsedMode && (
        <div className={`flex items-center gap-2 px-2 py-1 text-[11px] ${isOnline ? 'text-gov-green' : 'text-amber-600'}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-gov-green' : 'bg-amber-500'}`} />
          {isOnline ? 'Online' : `Offline (${offlineDraftCount} drafts)`}
        </div>
      )}
      <div className="flex items-center gap-2.5 px-2">
        <div className="w-8 h-8 rounded-md bg-gov-blue flex items-center justify-center flex-shrink-0 text-white font-bold text-xs">
          {(userName || 'U')?.[0]?.toUpperCase()}
        </div>
        {!collapsedMode && (
          <div className="flex-1 overflow-hidden">
            <div className="text-xs font-semibold text-gray-900 truncate">{userName || 'User'}</div>
            <div className="text-[10px] text-gray-500 truncate">{userRole || 'Innovator'}</div>
          </div>
        )}
      </div>
      <button
        onClick={onLogout}
        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-red-600 hover:bg-red-50 hover:text-red-700 transition"
      >
        <LogOut className="w-4 h-4 flex-shrink-0" />
        {!collapsedMode && <span>Sign Out</span>}
      </button>
    </div>
  );

  return (
    <>
      {/* ─── Desktop sidebar ─────────────────────────────── */}
      <aside className={`
        fixed left-0 top-16 bottom-0 z-40 hidden lg:flex flex-col
        bg-white border-r border-gray-200
        transition-all duration-300 ease-in-out
        ${collapsed ? 'w-[72px]' : 'w-64'}
      `}>
        <div className="flex items-center justify-between h-12 px-3 border-b border-gray-100">
          {!collapsed && (
            <span className="text-[13px] font-semibold text-gov-navy font-display px-1">Navigation</span>
          )}
          <button
            onClick={onToggleCollapsed}
            className="p-1.5 rounded-lg text-gray-500 hover:bg-gov-wash hover:text-gov-blue transition mx-auto"
            title={collapsed ? 'Expand' : 'Collapse'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronsRight className="w-4 h-4" /> : <ChevronsLeft className="w-4 h-4" />}
          </button>
        </div>
        {renderNav(collapsed)}
        {footer(collapsed)}
      </aside>

      {/* ─── Mobile drawer ───────────────────────────────── */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-[60]" onClick={onCloseMobile}>
          <div className="absolute inset-0 bg-gov-navy/50" />
          <div
            className="absolute left-0 top-0 bottom-0 w-64 bg-white border-r border-gray-200 p-3 flex flex-col animate-fade-in-left"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-1 pb-3 border-b border-gray-100">
              <span className="text-sm font-bold text-gov-navy font-display">IP-SAKTI Sahayak</span>
              <button onClick={onCloseMobile} className="text-gray-500 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            {renderNav(false)}
            {footer(false)}
          </div>
        </div>
      )}
    </>
  );
}