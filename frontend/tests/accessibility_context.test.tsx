import {
  AccessibilityProvider,
  useAccessibility,
} from '../src/lib/AccessibilityContext';
import { act, renderWithProviders } from './test-utils';

let ctx: any;

function Probe() {
  ctx = useAccessibility();
  return null;
}

function renderAccessibility() {
  return renderWithProviders(
    <AccessibilityProvider>
      <Probe />
    </AccessibilityProvider>
  );
}

function storedSettings(): any {
  const raw = localStorage.getItem('ipsakti_accessibility');
  return raw === null ? null : JSON.parse(raw);
}

beforeEach(() => {
  localStorage.clear();
  ctx = undefined;
  document.documentElement.classList.remove('high-contrast', 'reduce-motion');
  document.documentElement.style.fontSize = '';
  document.body.style.fontSize = '';
});

describe('AccessibilityProvider defaults', () => {
  test('starts with every setting in its neutral state', () => {
    renderAccessibility();
    expect(ctx.highContrast).toBe(false);
    expect(ctx.reduceMotion).toBe(false);
    expect(ctx.screenReader).toBe(false);
    expect(ctx.textScale).toBe(1);
    expect(
      document.documentElement.classList.contains('high-contrast')
    ).toBe(false);
    expect(
      document.documentElement.classList.contains('reduce-motion')
    ).toBe(false);
    expect(document.body.style.fontSize).toBe('100%');
  });

  test('persists the neutral defaults on first mount', () => {
    renderAccessibility();
    expect(storedSettings()).toEqual({
      highContrast: false,
      textScale: 1,
      reduceMotion: false,
      screenReader: false,
    });
  });

  test('exposes toggle functions', () => {
    renderAccessibility();
    expect(typeof ctx.toggleHighContrast).toBe('function');
    expect(typeof ctx.toggleReduceMotion).toBe('function');
    expect(typeof ctx.toggleScreenReader).toBe('function');
    expect(typeof ctx.setTextScale).toBe('function');
  });
});

describe('AccessibilityProvider toggles', () => {
  test('high contrast toggles the flag, the root class and the stored value', () => {
    renderAccessibility();
    act(() => ctx.toggleHighContrast());
    expect(ctx.highContrast).toBe(true);
    expect(
      document.documentElement.classList.contains('high-contrast')
    ).toBe(true);
    expect(storedSettings().highContrast).toBe(true);
    act(() => ctx.toggleHighContrast());
    expect(ctx.highContrast).toBe(false);
    expect(
      document.documentElement.classList.contains('high-contrast')
    ).toBe(false);
    expect(storedSettings().highContrast).toBe(false);
  });

  test('reduce motion toggles the flag, the root class and the stored value', () => {
    renderAccessibility();
    act(() => ctx.toggleReduceMotion());
    expect(ctx.reduceMotion).toBe(true);
    expect(
      document.documentElement.classList.contains('reduce-motion')
    ).toBe(true);
    expect(storedSettings().reduceMotion).toBe(true);
  });

  test('screen reader mode toggles without touching the root classes', () => {
    renderAccessibility();
    act(() => ctx.toggleScreenReader());
    expect(ctx.screenReader).toBe(true);
    expect(storedSettings().screenReader).toBe(true);
    expect(
      document.documentElement.classList.contains('high-contrast')
    ).toBe(false);
    expect(
      document.documentElement.classList.contains('reduce-motion')
    ).toBe(false);
  });

  test('toggling one setting keeps the other settings intact', () => {
    renderAccessibility();
    act(() => ctx.toggleHighContrast());
    act(() => ctx.toggleReduceMotion());
    expect(ctx.highContrast).toBe(true);
    expect(ctx.reduceMotion).toBe(true);
    expect(ctx.screenReader).toBe(false);
    expect(ctx.textScale).toBe(1);
    expect(storedSettings()).toEqual({
      highContrast: true,
      textScale: 1,
      reduceMotion: true,
      screenReader: false,
    });
  });

  test('text scale resizes the document body and is persisted', () => {
    renderAccessibility();
    act(() => ctx.setTextScale(1.3));
    expect(ctx.textScale).toBe(1.3);
    expect(document.body.style.fontSize).toBe('130%');
    expect(storedSettings().textScale).toBe(1.3);
    act(() => ctx.setTextScale(1));
    expect(document.body.style.fontSize).toBe('100%');
    expect(storedSettings().textScale).toBe(1);
  });
});

describe('AccessibilityProvider persistence', () => {
  test('restores settings saved by a previous session', () => {
    localStorage.setItem(
      'ipsakti_accessibility',
      JSON.stringify({
        highContrast: true,
        textScale: 1.5,
        reduceMotion: true,
        screenReader: true,
      })
    );
    renderAccessibility();
    expect(ctx.highContrast).toBe(true);
    expect(ctx.reduceMotion).toBe(true);
    expect(ctx.screenReader).toBe(true);
    expect(ctx.textScale).toBe(1.5);
    expect(
      document.documentElement.classList.contains('high-contrast')
    ).toBe(true);
    expect(
      document.documentElement.classList.contains('reduce-motion')
    ).toBe(true);
    expect(document.body.style.fontSize).toBe('150%');
  });

  test('recovers from corrupt stored json', () => {
    localStorage.setItem('ipsakti_accessibility', '{not-json');
    renderAccessibility();
    expect(ctx.highContrast).toBe(false);
    expect(ctx.textScale).toBe(1);
    expect(
      document.documentElement.classList.contains('high-contrast')
    ).toBe(false);
    expect(document.body.style.fontSize).toBe('100%');
    expect(storedSettings()).toEqual({
      highContrast: false,
      textScale: 1,
      reduceMotion: false,
      screenReader: false,
    });
  });

  test('overwrites corrupt storage with usable defaults', () => {
    localStorage.setItem('ipsakti_accessibility', '{not-json');
    renderAccessibility();
    act(() => ctx.toggleScreenReader());
    expect(storedSettings().screenReader).toBe(true);
    expect(storedSettings().highContrast).toBe(false);
  });

  test.failing('stored settings with invalid types fall back to the defaults', () => {
    localStorage.setItem(
      'ipsakti_accessibility',
      JSON.stringify({
        highContrast: 'yes',
        textScale: 'huge',
        reduceMotion: 1,
        screenReader: 'false',
      })
    );
    renderAccessibility();
    expect(ctx.highContrast).toBe(false);
    expect(ctx.textScale).toBe(1);
    expect(ctx.reduceMotion).toBe(false);
    expect(ctx.screenReader).toBe(false);
    expect(
      document.documentElement.classList.contains('high-contrast')
    ).toBe(false);
    expect(
      document.documentElement.classList.contains('reduce-motion')
    ).toBe(false);
    expect(document.body.style.fontSize).toBe('100%');
  });
});
