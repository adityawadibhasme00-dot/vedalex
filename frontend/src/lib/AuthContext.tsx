'use client';
import React, { createContext, useContext, useState, useEffect } from 'react';
import { loginUser, signupUser } from './api';

export interface User {
  name: string;
  email: string;
  role: 'Startup / MSME Founder' | 'Patent Agent' | 'Researcher' | 'Incubator Admin' | 'System Admin' | string;
  institution?: string;
  avatar?: string;
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

  useEffect(() => {
    const saved = localStorage.getItem('ipsakti_user');
    const savedToken = localStorage.getItem('ipsakti_token');
    if (saved) {
      try { setUser(JSON.parse(saved)); } catch {}
    }
    if (savedToken) setApiToken(savedToken);
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
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