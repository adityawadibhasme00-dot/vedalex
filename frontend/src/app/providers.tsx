'use client';
import { AuthProvider } from '../lib/AuthContext';
import { LangProvider } from '../lib/LangContext';
import { AccessibilityProvider } from '../lib/AccessibilityContext';
import RootSync from '../lib/RootSync';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <LangProvider>
        <AccessibilityProvider>
          <RootSync />
          {children}
        </AccessibilityProvider>
      </LangProvider>
    </AuthProvider>
  );
}