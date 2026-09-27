import * as ui from '@/components/ui';

const barrel = ui as unknown as Record<string, unknown>;

const EXPECTED_EXPORTS = [
  'GlassCard',
  'Button',
  'Badge',
  'Skeleton',
  'StatCard',
  'Toast',
  'PageHeader',
  'ScoreRing',
  'SelectOrOther',
  'NavItem',
  'JurisdictionToggle',
];

describe('ui barrel', () => {
  test.each(EXPECTED_EXPORTS)('%s is re-exported as a defined component', (name) => {
    expect(barrel).toHaveProperty(name);
    expect(barrel[name]).toBeDefined();
    expect(barrel[name]).not.toBeNull();
    expect(typeof barrel[name]).toBe('function');
  });

  test('every named export resolves to a usable value', () => {
    const entries = Object.entries(barrel).filter(([name]) => name !== '__esModule');
    expect(entries.length).toBeGreaterThan(0);
    for (const [name, value] of entries) {
      expect({ [name]: value }).toEqual({ [name]: expect.anything() });
      expect(typeof value).toBe('function');
    }
  });

  test('the barrel exposes exactly the components it lists', () => {
    const exported = Object.keys(barrel)
      .filter((name) => name !== '__esModule' && name !== 'default')
      .sort();
    expect(exported).toEqual([...EXPECTED_EXPORTS].sort());
  });
});
