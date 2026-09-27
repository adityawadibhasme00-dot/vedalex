import type { ComponentType } from 'react';
import { renderWithProviders, screen } from './test-utils';
import {
  TulsiLeaf,
  HerbSprig,
  TurmericRoot,
  MortarPestle,
  HerbGarland,
  AyurvedaSeal,
} from '../src/components/BotanicalDecor';

const decorations: Array<{
  name: string;
  Component: ComponentType<{ className?: string }>;
  viewBox: string;
}> = [
  { name: 'TulsiLeaf', Component: TulsiLeaf, viewBox: '0 0 64 64' },
  { name: 'HerbSprig', Component: HerbSprig, viewBox: '0 0 64 64' },
  { name: 'TurmericRoot', Component: TurmericRoot, viewBox: '0 0 64 64' },
  { name: 'MortarPestle', Component: MortarPestle, viewBox: '0 0 64 64' },
  { name: 'HerbGarland', Component: HerbGarland, viewBox: '0 0 64 64' },
  { name: 'AyurvedaSeal', Component: AyurvedaSeal, viewBox: '0 0 96 96' },
];

function svgOf(node: Element): SVGSVGElement {
  const svg = node.querySelector('svg');
  if (!svg) throw new Error('expected an svg element');
  return svg as unknown as SVGSVGElement;
}

describe('BotanicalDecor', () => {
  test.each(decorations)('$name draws a decorative, hidden svg', ({ Component, viewBox }) => {
    const { container } = renderWithProviders(<Component />);
    const svg = svgOf(container);
    expect(svg).toHaveAttribute('viewBox', viewBox);
    expect(svg).toHaveAttribute('aria-hidden', 'true');
    expect(svg).toHaveAttribute('focusable', 'false');
    expect(svg.querySelectorAll('path, rect, circle, text').length).toBeGreaterThan(0);
  });

  test('every decoration forwards its className to the svg', () => {
    for (const { Component } of decorations) {
      const { container, unmount } = renderWithProviders(<Component className="w-8 h-8" />);
      expect(svgOf(container)).toHaveClass('w-8', 'h-8');
      unmount();
    }
  });

  test('TulsiLeaf renders a filled leaf with its veins', () => {
    const { container } = renderWithProviders(<TulsiLeaf />);
    expect(svgOf(container).querySelectorAll('path')).toHaveLength(3);
  });

  test('HerbSprig renders a stem, five leaves and a bud', () => {
    const { container } = renderWithProviders(<HerbSprig />);
    const svg = svgOf(container);
    expect(svg.querySelectorAll('path')).toHaveLength(6);
    expect(svg.querySelectorAll('circle')).toHaveLength(1);
  });

  test('TurmericRoot renders its finger roots around a bulb', () => {
    const { container } = renderWithProviders(<TurmericRoot />);
    const svg = svgOf(container);
    expect(svg.querySelectorAll('rect')).toHaveLength(4);
    expect(svg.querySelectorAll('circle')).toHaveLength(2);
  });

  test('MortarPestle renders the bowl, base and pestle', () => {
    const { container } = renderWithProviders(<MortarPestle />);
    const svg = svgOf(container);
    expect(svg.querySelectorAll('path')).toHaveLength(5);
    expect(svg.querySelectorAll('circle')).toHaveLength(0);
  });

  test('HerbGarland renders a garland of five leaves', () => {
    const { container } = renderWithProviders(<HerbGarland />);
    const svg = svgOf(container);
    expect(svg.querySelectorAll('path')).toHaveLength(6);
    expect(svg.querySelectorAll('circle')).toHaveLength(1);
  });

  test('AyurvedaSeal renders its seal text and rings', () => {
    const { container } = renderWithProviders(<AyurvedaSeal />);
    const svg = svgOf(container);
    expect(svg.querySelectorAll('circle')).toHaveLength(2);
    expect(screen.getByText('आयुर्वेद')).toBeInTheDocument();
  });
});
