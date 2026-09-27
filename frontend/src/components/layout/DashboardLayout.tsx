'use client';
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/AuthContext';
import { useLang } from '../../lib/LangContext';
import { innolabApi, InnolabAgent } from '../../lib/innolabApi';
import { TopNav } from './TopNav';
import { Sidebar } from './Sidebar';

interface DashboardLayoutProps {
  children: React.ReactNode;
  activeTab: string;
  onNavigate: (tab: string) => void;
  onSearch?: (query: string) => void;
  userName?: string;
  userRole?: string;
  labAgents?: InnolabAgent[];
  labAgentsLoaded?: boolean;
  isOnline?: boolean;
  offlineDraftCount?: number;
}

export function DashboardLayout({
  children,
  activeTab,
  onNavigate,
  onSearch,
  userName,
  userRole,
  labAgents: labAgentsProp,
  labAgentsLoaded: labAgentsLoadedProp,
  isOnline: isOnlineProp,
  offlineDraftCount,
}: DashboardLayoutProps) {
  const { user, logout } = useAuth();
  const { lang } = useLang();
  const router = useRouter();

  const [collapsed, setCollapsed] = useState(false);
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== 'undefined' ? navigator.onLine : true,
  );
  const [labAgents, setLabAgents] = useState<InnolabAgent[]>([]);
  const [labAgentsLoaded, setLabAgentsLoaded] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (isOnlineProp !== undefined) return;
    const onO = () => setIsOnline(true);
    const onF = () => setIsOnline(false);
    window.addEventListener('online', onO);
    window.addEventListener('offline', onF);
    return () => {
      window.removeEventListener('online', onO);
      window.removeEventListener('offline', onF);
    };
  }, [isOnlineProp]);

  useEffect(() => {
    if (labAgentsProp !== undefined) return;
    innolabApi.agents()
      .then((r) => { setLabAgents(r.agents); setLabAgentsLoaded(true); })
      .catch(() => setLabAgentsLoaded(true));
  }, [labAgentsProp]);

  const handleLogout = () => { logout(); router.push('/login'); };
  const handleHome = () => router.push('/');
  const handleOpenAgent = (slug: string) => router.push(`/innovation-lab/agents/${slug}`);

  const handleSearch = (query: string) => {
    if (onSearch) { onSearch(query); return; }
    router.push('/dashboard#copilot');
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('ipsakti:copilot-question', { detail: query }));
    }, 450);
  };

  return (
    <div className="min-h-screen flex font-sans relative text-slate-800">
      {/* Top Navigation Bar (fixed) */}
      <TopNav
        isOnline={isOnlineProp ?? isOnline}
        offlineDraftCount={offlineDraftCount ?? 0}
        userName={userName ?? user?.name}
        userRole={userRole ?? user?.role}
        onMenuClick={() => setMobileNavOpen(true)}
        onSearch={handleSearch}
        onLogout={handleLogout}
      />

      {/* Sidebar (fixed) */}
      <Sidebar
        activeTab={activeTab}
        onNavigate={onNavigate}
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((v) => !v)}
        isOnline={isOnlineProp ?? isOnline}
        offlineDraftCount={offlineDraftCount ?? 0}
        userName={userName ?? user?.name}
        userRole={userRole ?? user?.role}
        onLogout={handleLogout}
        labAgents={labAgentsProp ?? labAgents}
        labAgentsLoaded={labAgentsLoadedProp ?? labAgentsLoaded}
        onOpenAgent={handleOpenAgent}
        onHome={handleHome}
        lang={lang}
        mobileOpen={mobileNavOpen}
        onCloseMobile={() => setMobileNavOpen(false)}
      />

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ${collapsed ? 'lg:ml-[72px]' : 'lg:ml-64'} pt-16`}>
        {children}
      </div>
    </div>
  );
}