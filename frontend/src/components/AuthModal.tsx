'use client';

import React, { useState } from 'react';
import { User, Lock, Mail, Shield, CheckCircle2, X, KeyRound, Building, Sparkles } from 'lucide-react';
import { useLang } from '../lib/LangContext';
import { t } from '../lib/i18n';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoginSuccess: (user: { name: string; role: string; email: string }) => void;
}

export default function AuthModal({ isOpen, onClose, onLoginSuccess }: AuthModalProps) {
  const { lang } = useLang();
  const [mode, setMode] = useState<'login' | 'signup' | 'otp' | 'forgot'>('login');
  const [role, setRole] = useState('Startup / MSME Founder');
  const [email, setEmail] = useState('founder@ayurstartup.in');
  const [password, setPassword] = useState('••••••••••••');
  const [otp, setOtp] = useState('626108');
  const [name, setName] = useState('Dr. Rajesh Vaidya');
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      if (mode === 'signup') {
        setMode('otp');
      } else {
        onLoginSuccess({ name, role, email });
        onClose();
      }
    }, 600);
  };

  const roles = [
    { id: 'Researcher', titleKey: 'auth_role_researcher_title', descKey: 'auth_role_researcher_desc' },
    { id: 'Startup / MSME Founder', titleKey: 'auth_role_startup_title', descKey: 'auth_role_startup_desc' },
    { id: 'Commercial Manufacturer', titleKey: 'auth_role_manufacturer_title', descKey: 'auth_role_manufacturer_desc' },
    { id: 'Registered Patent Agent', titleKey: 'auth_role_agent_title', descKey: 'auth_role_agent_desc' },
    { id: 'Institutional Admin', titleKey: 'auth_role_admin_title', descKey: 'auth_role_admin_desc' }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="glass-panel max-w-md w-full rounded-2xl p-6 border border-emerald-500/30 shadow-2xl relative">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-emerald-50 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center space-x-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-amber-500 flex items-center justify-center text-white shadow-lg">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900 font-display">
              {mode === 'login' && t('auth_title_login', lang)}
              {mode === 'signup' && t('auth_title_signup', lang)}
              {mode === 'otp' && t('auth_title_otp', lang)}
              {mode === 'forgot' && t('auth_title_forgot', lang)}
            </h3>
            <p className="text-xs text-slate-500">{t('auth_subtitle', lang)}</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          {mode === 'signup' && (
            <div>
              <label className="text-slate-500 font-medium block mb-1">{t('auth_full_name_label', lang)}</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 text-slate-800 focus:outline-none focus:border-emerald-500"
                required
              />
            </div>
          )}

          {mode !== 'otp' && (
            <>
              <div>
                <label className="text-slate-500 font-medium block mb-1">{t('auth_select_role', lang)}</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 text-slate-800 focus:outline-none focus:border-emerald-500 cursor-pointer"
                >
                  {roles.map((r) => (
                    <option key={r.id} value={r.id} className="bg-white">
                      {t(r.titleKey, lang)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-500 font-medium block mb-1">{t('auth_email_label', lang)}</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 pl-9 text-slate-800 focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
              </div>

              {mode !== 'forgot' && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-slate-500 font-medium">{t('login_password', lang)}</label>
                    <button
                      type="button"
                      onClick={() => setMode('forgot')}
                      className="text-[11px] text-emerald-600 hover:underline"
                    >
                      {t('auth_forgot_short', lang)}
                    </button>
                  </div>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 pl-9 text-slate-800 focus:outline-none focus:border-emerald-500"
                      required
                    />
                  </div>
                </div>
              )}
            </>
          )}

          {mode === 'otp' && (
            <div>
              <label className="text-slate-500 font-medium block mb-1">{t('auth_otp_label', lang)}</label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  maxLength={6}
                  className="w-full bg-emerald-50/70 border border-emerald-200 rounded-xl p-2.5 pl-9 text-slate-800 text-center tracking-widest font-mono text-sm focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-1.5">
                {t('auth_otp_note', lang)} <strong className="text-emerald-600">626108</strong>
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 text-white font-semibold text-xs shadow-lg shadow-emerald-900/40 transition disabled:opacity-50 mt-2"
          >
            {isLoading ? t('auth_verifying', lang) : mode === 'login' ? t('auth_submit_login', lang) : mode === 'signup' ? t('auth_submit_signup', lang) : t('auth_submit_confirm', lang)}
          </button>
        </form>

        {/* Mode Toggle */}
        <div className="mt-4 pt-3 border-t border-emerald-200 text-center text-xs text-slate-500">
          {mode === 'login' ? (
            <span>
              {t('auth_new_innovator', lang)}{' '}
              <button onClick={() => setMode('signup')} className="text-emerald-600 font-semibold hover:underline">
                {t('create_account', lang)}
              </button>
            </span>
          ) : (
            <span>
              {t('auth_already_registered', lang)}{' '}
              <button onClick={() => setMode('login')} className="text-emerald-600 font-semibold hover:underline">
                {t('sign_in', lang)}
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
