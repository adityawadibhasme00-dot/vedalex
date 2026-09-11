'use client';
import React, { createContext, useContext, useState, useEffect } from 'react';

export type LangCode = 'en' | 'hi' | 'mr' | 'ta' | 'te' | 'kn' | 'bn' | 'gu' | 'ml' | 'sa';

interface LangContextType {
  lang: LangCode;
  setLang: (l: LangCode) => void;
}

const LangContext = createContext<LangContextType>({ lang: 'en', setLang: () => {} });

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<LangCode>('en');

  useEffect(() => {
    const saved = localStorage.getItem('ipsakti_lang') as LangCode | null;
    if (saved) setLangState(saved);
  }, []);

  const setLang = (l: LangCode) => {
    setLangState(l);
    localStorage.setItem('ipsakti_lang', l);
  };

  return <LangContext.Provider value={{ lang, setLang }}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);
