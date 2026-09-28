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
    <div className="min-h-screen bg-gov-wash flex flex-col">
      {/* Utility strip + tricolor */}
      <div className="bg-gov-navy h-8" />
      <div className="gov-strip" aria-hidden="true" />

      <div className="flex-1 flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          {/* Language Switcher + Back to Home */}
          <div className="flex items-center justify-center gap-3 mb-6">
            <button
              onClick={() => router.push('/')}
              className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors border border-gov-rule text-gov-blue hover:border-gov-blue hover:text-gov-navy bg-white"
            >
              <ArrowLeft className="w-4 h-4" />
              Home
            </button>
            <button
              onClick={() => setLangOpen(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors border border-gov-rule text-slate-600 hover:border-gov-blue hover:text-gov-blue bg-white"
            >
              <Globe className="w-4 h-4" />
              {langNative}
            </button>
          </div>

          {/* Card */}
          <div className="bg-white border border-gov-rule shadow-lg">
            {/* Header band */}
            <div className="bg-gov-navy border-b-4 border-amber-500 px-8 py-5 text-center">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-white mb-3">
                <Leaf className="w-8 h-8 text-gov-blue" />
              </div>
              <h1 className="text-xl font-bold text-white font-display">{t('app_title', lang)}</h1>
              <p className="text-xs text-blue-200 mt-0.5">{t('tagline', lang)}</p>
            </div>

            <div className="p-8">
              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Mode Toggle */}
                <div className="flex rounded-md overflow-hidden border border-gov-rule p-1 bg-gov-wash">
                  {(['login', 'signup'] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => { setMode(m); setError(''); }}
                      className={`flex-1 py-2 rounded text-xs font-bold transition ${
                        mode === m
                          ? 'bg-gov-blue text-white'
                          : 'text-gov-mute hover:text-gov-blue'
                      }`}
                    >
                      {m === 'login' ? t('sign_in', lang) : t('create_account', lang)}
                    </button>
                  ))}
                </div>

                {mode === 'signup' && (
                  <>
                    <div>
                      <label className="block text-xs font-semibold text-gov-ink mb-1.5">{t('full_name', lang)}</label>
                      <input
                        type="text"
                        value={name}
                        onChange={e => setName(e.target.value)}
                        required
                        className="w-full bg-white border border-gov-rule rounded-md px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-gov-blue focus:ring-1 focus:ring-gov-blue transition"
                        placeholder="Dr. Ananya Desai"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gov-ink mb-1.5">{t('institution', lang)}</label>
                      <input
                        type="text"
                        value={institution}
                        onChange={e => setInstitution(e.target.value)}
                        className="w-full bg-white border border-gov-rule rounded-md px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-gov-blue focus:ring-1 focus:ring-gov-blue transition"
                        placeholder="NIPER / Startup / University"
                      />
                    </div>
                  </>
                )}

                <div>
                  <label className="block text-xs font-semibold text-gov-ink mb-1.5">{t('email', lang)}</label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    className="w-full bg-white border border-gov-rule rounded-md px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-gov-blue focus:ring-1 focus:ring-gov-blue transition"
                    placeholder="your@email.in"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gov-ink mb-1.5">{t('password', lang)}</label>
                  <div className="relative">
                    <input
                      type={showPass ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      required
                      minLength={6}
                      className="w-full bg-white border border-gov-rule rounded-md px-4 py-3 pr-11 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-gov-blue focus:ring-1 focus:ring-gov-blue transition"
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPass(!showPass)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-gov-blue transition text-xs"
                    >
                      {showPass ? '🙈' : '👁️'}
                    </button>
                  </div>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-md px-4 py-3 text-xs text-red-600">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-3 rounded-md bg-gov-blue hover:bg-gov-navy text-white font-bold text-sm border border-gov-blueDk transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
                      className="text-xs text-gov-mute hover:text-gov-blue transition"
                    >
                      {t('forgot_password', lang)}
                    </button>
                  </div>
                )}
              </form>

              {/* Demo Credentials */}
              <div className="mt-6">
                <p className="text-center text-xs text-gov-mute mb-3 font-semibold uppercase tracking-wider">
                  {t('demo_credentials', lang)}
                </p>
                <div className="space-y-2">
                  {DEMO_ACCOUNTS.map(acc => (
                    <button
                      key={acc.email}
                      onClick={() => fillDemo(acc)}
                      className="w-full flex items-center justify-between px-4 py-2.5 rounded-md border border-gov-rule bg-gov-wash hover:bg-white hover:border-gov-blue transition group"
                    >
                      <div className="text-left">
                        <div className="text-xs font-semibold text-gov-ink group-hover:text-gov-navy">{acc.role}</div>
                        <div className="text-[10px] text-gov-mute">{acc.email}</div>
                      </div>
                      <span className="text-[10px] text-gov-blue font-semibold opacity-0 group-hover:opacity-100 transition">Use →</span>
                    </button>
                  ))}
                </div>
                <p className="text-center text-[10px] text-gov-mute mt-3">Password for all demo accounts: <code className="text-gov-blue font-bold">demo123</code></p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-[11px] text-gov-mute mt-6">
            IP-SAKTI v1.0 · DPDP Act 2023 Compliant · Data Residency: ap-south-1
          </p>
        </div>
      </div>

      <div className="gov-strip" aria-hidden="true" />
      {langOpen && <LanguageSwitcher isOpen={langOpen} onClose={() => setLangOpen(false)} />}
    </div>
  );
}