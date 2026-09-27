import {
  clearOfflineDraft,
  getOfflineDrafts,
  saveOfflineDraft,
} from '../src/lib/offlineStorage';
import type { InnovationPassport } from '../src/types';

function draft(id: string): InnovationPassport {
  return { id, title: `Draft ${id}` } as unknown as InnovationPassport;
}

beforeEach(() => {
  localStorage.clear();
});

describe('offlineStorage draft round-trip', () => {
  test('save then read returns the draft', () => {
    saveOfflineDraft(draft('d1'));
    const drafts = getOfflineDrafts();
    expect(drafts).toHaveLength(1);
    expect(drafts[0].id).toBe('d1');
    expect((drafts[0] as any).is_offline_draft).toBe(true);
    expect((drafts[0] as any).updated_at).toBeTruthy();
  });

  test('saving the same id twice updates instead of duplicating', () => {
    saveOfflineDraft(draft('d1'));
    saveOfflineDraft({ ...draft('d1'), title: 'Updated' } as InnovationPassport);
    const drafts = getOfflineDrafts();
    expect(drafts).toHaveLength(1);
    expect((drafts[0] as any).title).toBe('Updated');
  });

  test('clearOfflineDraft removes only the matching id', () => {
    saveOfflineDraft(draft('d1'));
    saveOfflineDraft(draft('d2'));
    clearOfflineDraft('d1');
    const drafts = getOfflineDrafts();
    expect(drafts.map((d) => d.id)).toEqual(['d2']);
  });

  test('clearOfflineDraft on unknown id is a no-op', () => {
    saveOfflineDraft(draft('d1'));
    clearOfflineDraft('missing');
    expect(getOfflineDrafts()).toHaveLength(1);
  });

  test('corrupt storage payload degrades to empty list', () => {
    localStorage.setItem('ipsakti_offline_drafts', '{broken');
    expect(getOfflineDrafts()).toEqual([]);
  });

  test('empty storage returns empty list', () => {
    expect(getOfflineDrafts()).toEqual([]);
  });
});

describe('offlineStorage user isolation', () => {
  test.failing(
    "drafts saved by user A are not visible after logout and user B's login",
    () => {
      saveOfflineDraft(draft('user-a-secret'));
      // session switch: AuthContext.logout() only clears ipsakti_user /
      // ipsakti_token; the offline draft store is not user-scoped, so user B
      // on the same browser inherits user A's drafts.
      expect(getOfflineDrafts()).toEqual([]);
    }
  );
});
