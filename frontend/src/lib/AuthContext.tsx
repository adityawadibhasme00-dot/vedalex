'use client';
import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { loginUser, signupUser, getProfile, type AuthProfile } from './api';

export interface User {
  id?: string;
  name: string;
  email: string;
  role: 'Startup / MSME Founder' | 'Patent Agent' | 'Researcher' | 'Incubator Admin' | 'System Admin' | string;
  institution?: string;
  avatar?: string;
}

/**
 * Layer the authoritative server profile over the locally cached one. Fields the
 * server omits fall back to the cache so a partial response never blanks the UI.
 */
function mergeProfile(profile: AuthProfile, cached: User | null): User {
  return {
    ...cached,
    id: profile.id ?? cached?.id,
    name: profile.name || cached?.name || '',
    email: profile.email || cached?.email || '',
    role: profile.role || cached?.role || '',
    institution: profile.institution ?? cached?.institution
  };
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signup: (name: string, email: string, password: string, role?: string, institution?: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  isLoading: boolean;
  apiToken: string | null;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: async () => ({ success: false }),
  signup: async () => ({ success: false }),
  logout: () => {},
  isLoading: false,
  apiToken: null,
});

// Demo users (offline fallback when backend unavailable)
const DEMO_USERS: Record<string, { password: string; user: User }> = {
  'founder@ayurstartup.in': {
    password: 'demo123',
    user: { name: 'Dr. Rajesh Vaidya', email: 'founder@ayurstartup.in', role: 'Startup / MSME Founder' },
  },
  'agent@ipoffice.in': {
    password: 'demo123',
    user: { name: 'Adv. Priya Sharma', email: 'agent@ipoffice.in', role: 'Patent Agent' },
  },
  'admin@incubator.in': {
    password: 'demo123',
    user: { name: 'Prof. A. Kumar', email: 'admin@incubator.in', role: 'Incubator Admin' },
  },
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [apiToken, setApiToken] = useState<string | null>(null);
  // Guards the background revalidation against landing after the user signed out.
  const sessionActive = useRef(true);

  useEffect(() => {
    const saved = localStorage.getItem('ipsakti_user');
    const savedToken = localStorage.getItem('ipsakti_token');
    let cached: User | null = null;
    if (saved) {
      try { cached = JSON.parse(saved); } catch {}
    }
    if (cached) setUser(cached);
    if (savedToken) setApiToken(savedToken);
    setIsLoading(false);

    if (!savedToken) return;

    // Revalidate in the background so the displayed profile name is the current
    // server value rather than a stale localStorage copy. Failures are ignored on
    // purpose: the session is offline-first, and the backend regenerates its JWT
    // secret on restart, so a 401 here must not discard the cached profile.
    getProfile(savedToken)
      .then((profile) => {
        if (!sessionActive.current) return;
        const next = mergeProfile(profile, cached);
        setUser(next);
        localStorage.setItem('ipsakti_user', JSON.stringify(next));
      })
      .catch(() => {});
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    sessionActive.current = true;
    setIsLoading(true);
    try {
      const res = await loginUser(email, password);
      setUser(res.user);
      setApiToken(res.access_token);
      localStorage.setItem('ipsakti_user', JSON.stringify(res.user));
      localStorage.setItem('ipsakti_token', res.access_token);
      setIsLoading(false);
      return { success: true };
    } catch (err: any) {
      // Fallback to demo users when backend offline
      const record = DEMO_USERS[email.toLowerCase()];
      if (record && record.password === password) {
        setUser(record.user);
        localStorage.setItem('ipsakti_user', JSON.stringify(record.user));
        setIsLoading(false);
        return { success: true };
      }
      setIsLoading(false);
      return { success: false, error: err?.message || 'Invalid credentials' };
    }
  };

  const signup = async (name: string, email: string, password: string, role?: string, institution?: string): Promise<{ success: boolean; error?: string }> => {
    sessionActive.current = true;
    setIsLoading(true);
    try {
      const res = await signupUser(name, email, password, role, institution);
      setUser(res.user);
      setApiToken(res.access_token);
      localStorage.setItem('ipsakti_user', JSON.stringify(res.user));
      localStorage.setItem('ipsakti_token', res.access_token);
      setIsLoading(false);
      return { success: true };
    } catch (err: any) {
      setIsLoading(false);
      return { success: false, error: err?.message || 'Signup failed' };
    }
  };

  const logout = () => {
    sessionActive.current = false;
    setUser(null);
    setApiToken(null);
    localStorage.removeItem('ipsakti_user');
    localStorage.removeItem('ipsakti_token');
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, logout, isLoading, apiToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);