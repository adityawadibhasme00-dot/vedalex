'use client';
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface AccessibilitySettings {
  highContrast: boolean;
  textScale: number;
  reduceMotion: boolean;
  screenReader: boolean;
}

interface AccessibilityContextType extends AccessibilitySettings {
  toggleHighContrast: () => void;
  toggleReduceMotion: () => void;
  toggleScreenReader: () => void;
  setTextScale: (s: number) => void;
}

const AccessibilityContext = createContext<AccessibilityContextType>({
  highContrast: false,
  textScale: 1,
  reduceMotion: false,
  screenReader: false,
  toggleHighContrast: () => {},
  toggleReduceMotion: () => {},
  toggleScreenReader: () => {},
  setTextScale: () => {},
});

function readSettings(): AccessibilitySettings {
  if (typeof window === 'undefined') {
    return { highContrast: false, textScale: 1, reduceMotion: false, screenReader: false };
  }
  try {
    const raw = localStorage.getItem('ipsakti_accessibility');
    if (raw) return { highContrast: false, textScale: 1, reduceMotion: false, screenReader: false, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return { highContrast: false, textScale: 1, reduceMotion: false, screenReader: false };
}

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<AccessibilitySettings>(readSettings);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('high-contrast', settings.highContrast);
    root.classList.toggle('reduce-motion', settings.reduceMotion);
    root.style.fontSize = settings.textScale % 1 === 0 ? '' : '';
    document.body.style.fontSize = `${settings.textScale * 100}%`;
    try {
      localStorage.setItem('ipsakti_accessibility', JSON.stringify(settings));
    } catch { /* ignore */ }
  }, [settings]);

  const toggleHighContrast = useCallback(() => setSettings((s) => ({ ...s, highContrast: !s.highContrast })), []);
  const toggleReduceMotion = useCallback(() => setSettings((s) => ({ ...s, reduceMotion: !s.reduceMotion })), []);
  const toggleScreenReader = useCallback(() => setSettings((s) => ({ ...s, screenReader: !s.screenReader })), []);
  const setTextScale = useCallback((textScale: number) => setSettings((s) => ({ ...s, textScale })), []);

  return (
    <AccessibilityContext.Provider
      value={{ ...settings, toggleHighContrast, toggleReduceMotion, toggleScreenReader, setTextScale }}
    >
      {children}
    </AccessibilityContext.Provider>
  );
}

export const useAccessibility = () => useContext(AccessibilityContext);