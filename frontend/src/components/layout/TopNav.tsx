'use client';
import React, { useState, type FormEvent } from 'react';
import {
  Leaf, Search, Bell, Menu, ShieldCheck, Wifi, WifiOff,
  Globe, Accessibility as AccessibilityIcon, LogOut, ChevronDown,
} from 'lucide-react';
import { useLang } from '../../lib/LangContext';
import { t, SUPPORTED_LANGUAGES } from '../../lib/i18n';
import LanguageSwitcher from '../LanguageSwitcher';
import AccessibilityPanel from '../AccessibilityPanel';

interface TopNavProps {
  isOnline: boolean;
  offlineDraftCount: number;
  userName?: string;
  userRole?: string;
  onMenuClick: () => void;
  onSearch: (query: string) => void;
  onLogout: () => void;
}

export function TopNav({
  isOnline,
  offlineDraftCount,
  userName,
  userRole,
  onMenuClick,
  onSearch,
  onLogout,
}: TopNavProps) {
  const { lang } = useLang();
  const [langOpen, setLangOpen] = useState(false);
  const [accessOpen, setAccessOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [profileOpen, setProfileOpen] = useState(false);

  const langLabel = SUPPORTED_LANGUAGES.find((l) => l.code === lang)?.nativeName || 'English';

  const submitSearch = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
      setQuery('');
    }
  };

  return (
    <>
      <nav className="h-16 bg-gov-blue border-b border-gov-navy fixed top-0 left-0 right-0 z-50 shadow-md">
        <div className="h-full px-3 md:px-4 flex items-center justify-between gap-3">
          {/* Left: mobile menu + logo + title */}
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              onClick={onMenuClick}
              className="lg:hidden p-1.5 rounded-lg hover:bg-white/10 text-white"
              aria-label={t('topnav_open_navigation', lang)}
              title={t('topnav_open_navigation', lang)}
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="w-9 h-9 md:w-10 md:h-10 rounded-lg bg-white flex items-center justify-center flex-shrink-0">
              <Leaf className="w-5 h-5 text-gov-blue" />
            </div>
            <div className="min-w-0">
              <h1 className="text-base md:text-xl font-semibold text-white font-display truncate leading-tight">
                IP-SAKTI Sahayak
              </h1>
              <p className="text-[10px] text-blue-200 hidden sm:block truncate">आयुर्वेद • आईपी सुरक्षा · RAG-grounded · DPDP compliant</p>
            </div>
          </div>

          {/* Center: Search */}
          <form onSubmit={submitSearch} className="hidden md:flex flex-1 justify-center mx-4 min-w-0">
            <div className="relative w-full max-w-2xl">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('topnav_search_placeholder', lang)}
                className="w-full pl-10 pr-4 py-2 border border-gov-navy rounded-md bg-white focus:ring-2 focus:ring-amber-400 focus:border-transparent outline-none text-sm text-gray-800 placeholder:text-gray-400"
              />
            </div>
          </form>

          {/* Right: status + controls + profile */}
          <div className="flex items-center gap-1.5 md:gap-2.5 flex-shrink-0">
            <span className="hidden xl:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-white/10 border border-white/25 text-[11px] text-blue-100">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-300" />
              DPDP Act 2023
            </span>

            <div className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] border ${isOnline ? 'bg-white/10 border-white/25 text-blue-100' : 'bg-amber-500/90 border-amber-700 text-white'}`}>
              {isOnline ? (
                <><Wifi className="w-3.5 h-3.5 text-amber-300" />{t('online', lang)}</>
              ) : (
                <><WifiOff className="w-3.5 h-3.5 text-white" />{t('offline', lang)} ({offlineDraftCount})</>
              )}
            </div>

            <button
              onClick={() => setAccessOpen(true)}
              className="hidden md:flex items-center gap-1.5 p-2 rounded-md bg-white/10 border border-white/25 text-white hover:bg-white/20 transition"
              aria-label={t('accessibility', lang)}
              title={t('accessibility', lang)}
            >
              <AccessibilityIcon className="w-4 h-4" />
            </button>

            <button
              onClick={() => setLangOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-white/10 border border-white/25 text-white hover:bg-white/20 transition"
              aria-label="Select Language"
              title={t('topnav_select_language', lang)}
            >
              <Globe className="w-4 h-4 text-amber-300" />
              <span className="text-sm font-medium hidden sm:inline">{langLabel}</span>
            </button>

            <button
              className="relative p-2 rounded-full hover:bg-white/10 text-white"
              aria-label={t('topnav_notifications', lang)}
              title={t('topnav_notifications', lang)}
            >
              <Bell className="h-5 w-5" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-amber-400 rounded-full ring-2 ring-gov-blue" />
            </button>

            {/* Profile chip */}
            <div className="relative">
              <button
                onClick={() => setProfileOpen((v) => !v)}
                className="flex items-center gap-2 pl-1.5 pr-2 py-1.5 rounded-md border border-white/25 hover:bg-white/10 transition"
                aria-label={t('topnav_profile', lang)}
              >
                <div className="h-8 w-8 bg-amber-400 rounded-full flex items-center justify-center text-gov-navy text-sm font-semibold">
                  {(userName || 'U')?.[0]?.toUpperCase()}
                </div>
                <span className="hidden lg:block text-sm font-medium text-white max-w-[110px] truncate">
                  {userName || 'User'}
                </span>
                <ChevronDown className="hidden lg:block h-3.5 w-3.5 text-blue-200" />
              </button>

              {profileOpen && (
                <div className="absolute right-0 top-[calc(100%+8px)] w-60 bg-white border border-gray-300 rounded-lg shadow-xl z-50 p-2">
                  <div className="px-3 py-2 border-b border-gray-200">
                    <div className="text-sm font-semibold text-gray-900 truncate">{userName || 'User'}</div>
                    <div className="text-xs text-gray-500 truncate">{userRole || 'Innovator'}</div>
                  </div>
                  <button
                    onClick={() => setProfileOpen(false)}
                    className="w-full text-left px-3 py-2 mt-1 rounded-md text-xs text-gray-600 hover:bg-gov-wash hover:text-gov-navy"
                  >
                    {t('topnav_working_dashboard', lang)}
                  </button>
                  <div className="mt-1 pt-2 border-t border-gray-200">
                    <button
                      onClick={() => { setProfileOpen(false); onLogout(); }}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-left text-xs font-medium text-red-600 hover:bg-red-50 transition"
                    >
                      <LogOut className="w-4 h-4" />
                      {t('sign_out', lang)}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      {langOpen && <LanguageSwitcher isOpen={langOpen} onClose={() => setLangOpen(false)} />}
      {accessOpen && <AccessibilityPanel isOpen={accessOpen} onClose={() => setAccessOpen(false)} />}
    </>
  );
}