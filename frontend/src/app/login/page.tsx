'use client';
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/AuthContext';
import { useLang } from '../../lib/LangContext';
import LanguageSwitcher from '../../components/LanguageSwitcher';
import { t } from '../../lib/i18n';
import { Globe, ArrowLeft, Leaf } from 'lucide-react';

const DEMO_ACCOUNTS = [
  { email: 'founder@ayurstartup.in', role: 'Startup / MSME Founder' },
  { email: 'agent@ipoffice.in', role: 'Patent Agent' },
  { email: 'admin@incubator.in', role: 'Incubator Admin' },
];

export default function LoginPage() {
  const { lang, setLang } = useLang();
  const { login, signup, isLoading } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [institution, setInstitution] = useState('');
  const [error, setError] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const langNative = { en: 'English', hi: 'हिन्दी', mr: 'मराठी', ta: 'தமிழ்', te: 'తెలుగు', kn: 'ಕನ್ನಡ', bn: 'বাংলা', gu: 'ગુજરાતી', ml: 'മലയാളം', sa: 'संस्कृतम्' }[lang] || 'English';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (mode === 'login') {
      const res = await login(email, password);
      if (res.success) {
        router.push('/dashboard');
      } else {
        setError(res.error || t('invalid_credentials', lang));
      }
    } else {
      const res = await signup(name, email, password, 'researcher', institution);
      if (res.success) {
        router.push('/dashboard');
      } else {
        setError(res.error || 'Signup failed');
      }
    }
  };

  const fillDemo = (acc: typeof DEMO_ACCOUNTS[0]) => {
    setMode('login');
    setEmail(acc.email);
    setPassword('demo123');
    setError('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden" style={{ background: 'var(--bg-main)' }}>
      {/* Animated gradient blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full opacity-25 animate-blob" style={{ background: 'radial-gradient(circle, #10b981, transparent 70%)' }} />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full opacity-20 animate-blob" style={{ background: 'radial-gradient(circle, #f59e0b, transparent 70%)', animationDelay: '2s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-10" style={{ background: 'radial-gradient(circle, #10b981, transparent 70%)' }} />
      </div>

      <div className="relative z-10 w-full max-w-md px-4">
        {/* Language Switcher + Back to Home */}
        <div className="flex items-center justify-center gap-3 mb-6">
          <button
            onClick={() => router.push('/')}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all border border-emerald-200 text-emerald-700 hover:border-emerald-400 hover:text-emerald-900 bg-white/70"
          >
            <ArrowLeft className="w-4 h-4" />
            Home
          </button>
          <button
            onClick={() => setLangOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all border border-emerald-200 text-slate-600 hover:border-emerald-400 hover:text-emerald-700 bg-white/70"
          >
            <Globe className="w-4 h-4" />
            {langNative}
          </button>
        </div>

        {/* Card */}
        <div className="bg-white/85 backdrop-blur-xl rounded-3xl p-8 shadow-2xl border border-emerald-200">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-lg shadow-emerald-900/30 mb-4">
              <Leaf className="w-9 h-9 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-emerald-900 font-display">{t('app_title', lang)}</h1>
            <p className="text-sm text-slate-500 mt-1">{t('tagline', lang)}</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Mode Toggle */}
            <div className="flex rounded-xl overflow-hidden border border-emerald-200 p-1 bg-emerald-50">
              {(['login', 'signup'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => { setMode(m); setError(''); }}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold transition ${
                    mode === m
                      ? 'bg-emerald-700 text-white shadow'
                      : 'text-slate-500 hover:text-emerald-800'
                  }`}
                >
                  {m === 'login' ? t('sign_in', lang) : t('create_account', lang)}
                </button>
              ))}
            </div>

            {mode === 'signup' && (
              <>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5">{t('full_name', lang)}</label>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    required
                    className="w-full bg-emerald-50/50 border border-emerald-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-300 transition"
                    placeholder="Dr. Ananya Desai"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5">{t('institution', lang)}</label>
                  <input
                    type="text"
                    value={institution}
                    onChange={e => setInstitution(e.target.value)}
                    className="w-full bg-emerald-50/50 border border-emerald-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-300 transition"
                    placeholder="NIPER / Startup / University"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">{t('email', lang)}</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full bg-emerald-50/50 border border-emerald-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-300 transition"
                placeholder="your@email.in"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">{t('password', lang)}</label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full bg-emerald-50/50 border border-emerald-200 rounded-xl px-4 py-3 pr-11 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-300 transition"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-emerald-600 transition text-xs"
                >
                  {showPass ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-xs text-red-600">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-700 to-emerald-600 hover:from-emerald-600 hover:to-emerald-500 text-white font-bold text-sm shadow-lg shadow-emerald-900/30 transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
              ) : null}
              {mode === 'login' ? t('sign_in', lang) : t('create_account', lang)}
            </button>

            {mode === 'login' && (
              <div className="text-center">
                <button
                  type="button"
                  onClick={() => alert('Password reset instructions would be sent to your email')}
                  className="text-xs text-slate-500 hover:text-emerald-700 transition"
                >
                  {t('forgot_password', lang)}
                </button>
              </div>
            )}
          </form>

          {/* Demo Credentials */}
          <div className="mt-6">
            <p className="text-center text-xs text-slate-500 mb-3 font-semibold uppercase tracking-wider">
              {t('demo_credentials', lang)}
            </p>
            <div className="space-y-2">
              {DEMO_ACCOUNTS.map(acc => (
                <button
                  key={acc.email}
                  onClick={() => fillDemo(acc)}
                  className="w-full flex items-center justify-between px-4 py-2.5 rounded-xl border border-emerald-200 bg-emerald-50/40 hover:bg-emerald-50 hover:border-emerald-300 transition group"
                >
                  <div className="text-left">
                    <div className="text-xs font-semibold text-slate-700 group-hover:text-emerald-900">{acc.role}</div>
                    <div className="text-[10px] text-slate-500">{acc.email}</div>
                  </div>
                  <span className="text-[10px] text-emerald-600 font-semibold opacity-0 group-hover:opacity-100 transition">Use →</span>
                </button>
              ))}
            </div>
            <p className="text-center text-[10px] text-slate-500 mt-3">Password for all demo accounts: <code className="text-emerald-700 font-bold">demo123</code></p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-[11px] text-slate-500 mt-6">
          IP-SAKTI v1.0 · DPDP Act 2023 Compliant · Data Residency: ap-south-1
        </p>
      </div>

      {langOpen && <LanguageSwitcher isOpen={langOpen} onClose={() => setLangOpen(false)} />}
    </div>
  );
}