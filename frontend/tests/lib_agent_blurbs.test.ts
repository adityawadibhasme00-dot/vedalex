import { AGENT_BLURB_KEYS } from '../src/lib/agentBlurbs';
import { DICTIONARY, SUPPORTED_LANGUAGES } from '../src/lib/i18n';

const CATALOG_SLUGS = Object.keys(AGENT_BLURB_KEYS);

describe('AGENT_BLURB_KEYS structure', () => {
  test('catalog is non-empty', () => {
    expect(CATALOG_SLUGS.length).toBeGreaterThan(0);
  });

  test('every slug is a snake_case identifier', () => {
    for (const slug of CATALOG_SLUGS) {
      expect(slug).toMatch(/^[a-z][a-z0-9_]*$/);
    }
  });

  test('every slug points at an ab_ dictionary key', () => {
    for (const slug of CATALOG_SLUGS) {
      expect(AGENT_BLURB_KEYS[slug]).toMatch(/^ab_[a-z0-9_]+$/);
    }
  });

  test('every referenced dictionary key exists', () => {
    for (const slug of CATALOG_SLUGS) {
      expect(DICTIONARY[AGENT_BLURB_KEYS[slug]]).toBeDefined();
    }
  });

  test('no two slugs share the same dictionary key', () => {
    const values = Object.values(AGENT_BLURB_KEYS);
    expect(new Set(values).size).toBe(values.length);
  });

  test('an unknown slug yields undefined so callers can fall back', () => {
    const apiDescription = 'Description served by the agents endpoint';
    expect(AGENT_BLURB_KEYS['prior-art']).toBeUndefined();
    expect(AGENT_BLURB_KEYS['prior-art'] || apiDescription).toBe(apiDescription);
  });

  test('lookup does not mutate the catalog', () => {
    const before = JSON.stringify(AGENT_BLURB_KEYS);
    AGENT_BLURB_KEYS['missing'];
    AGENT_BLURB_KEYS['prior-art'] || 'fallback';
    expect(JSON.stringify(AGENT_BLURB_KEYS)).toBe(before);
  });
});

describe('agent blurb translations', () => {
  test('every language has a non-empty blurb for every agent', () => {
    for (const slug of CATALOG_SLUGS) {
      const entry = DICTIONARY[AGENT_BLURB_KEYS[slug]];
      for (const { code } of SUPPORTED_LANGUAGES) {
        const value = entry[code];
        expect(typeof value).toBe('string');
        expect(value.trim()).not.toBe('');
        expect(value).toBe(value.trim());
      }
    }
  });

  test('blurbs stay within a short card sized length', () => {
    for (const slug of CATALOG_SLUGS) {
      const entry = DICTIONARY[AGENT_BLURB_KEYS[slug]];
      for (const { code } of SUPPORTED_LANGUAGES) {
        expect(entry[code].length).toBeLessThan(260);
      }
    }
  });
});
