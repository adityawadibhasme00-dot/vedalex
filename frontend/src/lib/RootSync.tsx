'use client';
import { useEffect } from 'react';
import { useLang } from './LangContext';

export default function RootSync() {
  const { lang } = useLang();

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  return null;
}