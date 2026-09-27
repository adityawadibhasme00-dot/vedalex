import { AGENT_BLURBS } from '../src/lib/agentBlurbs';

const REGISTERED_SLUGS = [
  'triz',
  'quick_research',
  'find_solutions',
  'novelty_search',
  'fto_search',
  'design_fto',
  'patent_drafting',
  'invention_disclosure',
  'office_action_response',
  'essentiality_claim_chart',
  'tdoc_novelty_search',
  'document_analyzer',
  'lca_biotherapeutic',
  'lca_small_molecule',
  'sar_data_extraction',
  'antibody_target_predictor',
  'markush_drafting',
  'formulation',
  'materials_find_solutions',
];

describe('AGENT_BLURBS structure', () => {
  test('every registered agent slug has a non-empty blurb', () => {
    for (const slug of REGISTERED_SLUGS) {
      expect(AGENT_BLURBS[slug]).toBeDefined();
      expect(typeof AGENT_BLURBS[slug]).toBe('string');
      expect(AGENT_BLURBS[slug].trim()).not.toBe('');
      expect(AGENT_BLURBS[slug]).toBe(AGENT_BLURBS[slug].trim());
    }
  });

  test('the catalog contains no slug outside the registry', () => {
    const keys = Object.keys(AGENT_BLURBS);
    expect(keys).toHaveLength(REGISTERED_SLUGS.length);
    for (const key of keys) {
      expect(REGISTERED_SLUGS).toContain(key);
    }
  });

  test('every key is a snake_case slug', () => {
    for (const key of Object.keys(AGENT_BLURBS)) {
      expect(key).toMatch(/^[a-z][a-z0-9_]*$/);
    }
  });

  test('no two slugs share the same blurb text', () => {
    const values = Object.values(AGENT_BLURBS);
    expect(new Set(values).size).toBe(values.length);
  });

  test('blurbs are single line sentences', () => {
    for (const value of Object.values(AGENT_BLURBS)) {
      expect(value).not.toContain('\n');
      expect(value.endsWith('.')).toBe(true);
    }
  });

  test('blurbs stay within a short card sized length', () => {
    for (const value of Object.values(AGENT_BLURBS)) {
      expect(value.length).toBeLessThan(200);
    }
  });
});

describe('AGENT_BLURBS lookup', () => {
  test('known slugs resolve to their own blurb', () => {
    expect(AGENT_BLURBS['triz']).toMatch(/contradiction/i);
    expect(AGENT_BLURBS['novelty_search']).toMatch(/novelty search/i);
    expect(AGENT_BLURBS['fto_search']).toMatch(/infring/i);
    expect(AGENT_BLURBS['patent_drafting']).toMatch(/patent application/i);
  });

  test('an unknown slug yields undefined so callers can fall back', () => {
    const apiDescription = 'Description served by the agents endpoint';
    expect(AGENT_BLURBS['prior-art']).toBeUndefined();
    expect(AGENT_BLURBS['prior-art'] || apiDescription).toBe(apiDescription);
  });

  test('registered slugs never trigger the fallback branch', () => {
    for (const slug of REGISTERED_SLUGS) {
      expect(Boolean(AGENT_BLURBS[slug])).toBe(true);
      expect(AGENT_BLURBS[slug] || 'fallback').toBe(AGENT_BLURBS[slug]);
    }
  });

  test('lookup does not mutate the catalog', () => {
    const before = JSON.stringify(AGENT_BLURBS);
    AGENT_BLURBS['missing'];
    AGENT_BLURBS['prior-art'] || 'fallback';
    expect(JSON.stringify(AGENT_BLURBS)).toBe(before);
  });
});
