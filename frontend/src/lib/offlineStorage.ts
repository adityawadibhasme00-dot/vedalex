import { InnovationPassport } from '../types';

const STORAGE_KEY = 'ipsakti_offline_drafts';

export function saveOfflineDraft(passport: InnovationPassport) {
  if (typeof window === 'undefined') return;
  try {
    const existing = getOfflineDrafts();
    const index = existing.findIndex(d => d.id === passport.id);
    if (index >= 0) {
      existing[index] = { ...passport, is_offline_draft: true, updated_at: new Date().toISOString() };
    } else {
      existing.push({ ...passport, is_offline_draft: true, updated_at: new Date().toISOString() });
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));
  } catch (e) {
    console.error('Failed to save offline draft', e);
  }
}

export function getOfflineDrafts(): InnovationPassport[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function clearOfflineDraft(id: string) {
  if (typeof window === 'undefined') return;
  const existing = getOfflineDrafts().filter(d => d.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));
}
