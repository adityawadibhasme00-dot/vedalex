import { LangCode } from '../LangContext';

export type AreaDict = Record<string, Partial<Record<LangCode, string>> & { en: string }>;

export const LANGS: LangCode[] = ['en', 'hi', 'mr', 'ta', 'te', 'kn', 'bn', 'gu', 'ml', 'sa'];

export const EXAMPLE_KEY: AreaDict = {
  example_key: {
    en: 'English',
    hi: 'हिंदी',
    mr: 'मराठी',
    ta: 'தமிழ்',
    te: 'తెలుగు',
    kn: 'ಕನ್ನಡ',
    bn: 'বাংলা',
    gu: 'ગુજરાતી',
    ml: 'മലയാളം',
    sa: 'संस्कृतम्',
  },
};