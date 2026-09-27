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
      <nav className="h-16 bg-white border-b border-gray-200 fixed top-0 left-0 right-0 z-50 shadow-sm">
        <div className="h-full px-3 md:px-4 flex items-center justify-between gap-3">
          {/* Left: mobile menu + logo + title */}
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              onClick={onMenuClick}
              className="lg:hidden p-1.5 rounded-lg hover:bg-emerald-50 text-slate-600"
              aria-label="Open navigation"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="w-9 h-9 md:w-10 md:h-10 rounded-lg bg-gradient-to-br from-emerald-600 to-emerald-700 flex items-center justify-center flex-shrink-0 shadow-md shadow-emerald-900/20">
              <Leaf className="w-5 h-5 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-base md:text-xl font-semibold text-emerald-800 font-display truncate leading-tight">
                IP-SAKTI Sahayak
              </h1>
              <p className="text-[10px] text-slate-500 hidden sm:block truncate">आयुर्वेद • आईपी सुरक्षा · RAG-grounded · DPDP compliant</p>
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
                placeholder="Search statutes, patents, regulations..."
                className="w-full pl-10 pr-4 py-2 border border-emerald-200 rounded-lg bg-gray-50 focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none text-sm text-gray-800 placeholder:text-gray-400"
              />
            </div>
          </form>

          {/* Right: status + controls + profile */}
          <div className="flex items-center gap-1.5 md:gap-2.5 flex-shrink-0">
            <span className="hidden xl:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-[11px] text-emerald-700">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              DPDP Act 2023
            </span>

            <div className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] border ${isOnline ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-amber-50 border-amber-200 text-amber-700'}`}>
              {isOnline ? (
                <><Wifi className="w-3.5 h-3.5 text-emerald-600" />{t('online', lang)}</>
              ) : (
                <><WifiOff className="w-3.5 h-3.5 text-amber-600" />{t('offline', lang)} ({offlineDraftCount})</>
              )}
            </div>

            <button
              onClick={() => setAccessOpen(true)}
              className="hidden md:flex items-center gap-1.5 p-2 rounded-xl bg-white border border-emerald-200 text-slate-600 hover:bg-emerald-50 transition"
              aria-label={t('accessibility', lang)}
              title={t('accessibility', lang)}
            >
              <AccessibilityIcon className="w-4 h-4" />
            </button>

            <button
              onClick={() => setLangOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-white border border-emerald-200 text-slate-700 hover:bg-emerald-50 transition"
              aria-label="Select Language"
              title="Select Language"
            >
              <Globe className="w-4 h-4 text-emerald-600" />
              <span className="text-sm font-medium hidden sm:inline">{langLabel}</span>
            </button>

            <button
              className="relative p-2 rounded-full hover:bg-gray-100 text-gray-600"
              aria-label="Notifications"
              title="Notifications"
            >
              <Bell className="h-5 w-5" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-red-500 rounded-full ring-2 ring-white" />
            </button>

            {/* Profile chip */}
            <div className="relative">
              <button
                onClick={() => setProfileOpen((v) => !v)}
                className="flex items-center gap-2 pl-1.5 pr-2 py-1.5 rounded-xl border border-gray-200 hover:bg-emerald-50 hover:border-emerald-200 transition"
                aria-label="Profile"
              >
                <div className="h-8 w-8 bg-emerald-600 rounded-full flex items-center justify-center text-white text-sm font-semibold">
                  {(userName || 'U')?.[0]?.toUpperCase()}
                </div>
                <span className="hidden lg:block text-sm font-medium text-gray-700 max-w-[110px] truncate">
                  {userName || 'User'}
                </span>
                <ChevronDown className="hidden lg:block h-3.5 w-3.5 text-gray-400" />
              </button>

              {profileOpen && (
                <div className="absolute right-0 top-[calc(100%+8px)] w-60 bg-white border border-gray-200 rounded-xl shadow-xl z-50 p-2">
                  <div className="px-3 py-2 border-b border-gray-100">
                    <div className="text-sm font-semibold text-gray-900 truncate">{userName || 'User'}</div>
                    <div className="text-xs text-gray-500 truncate">{userRole || 'Innovator'}</div>
                  </div>
                  <button
                    onClick={() => setProfileOpen(false)}
                    className="w-full text-left px-3 py-2 mt-1 rounded-lg text-xs text-gray-600 hover:bg-emerald-50 hover:text-emerald-800"
                  >
                    IP-SAKTI Sahayak — Government Working Dashboard
                  </button>
                  <div className="mt-1 pt-2 border-t border-gray-100">
                    <button
                      onClick={() => { setProfileOpen(false); onLogout(); }}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-xs font-medium text-red-600 hover:bg-red-50 transition"
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