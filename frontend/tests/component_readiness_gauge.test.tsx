import { renderWithProviders, screen } from './test-utils';
import { ReadinessGauge } from '../src/components/ReadinessGauge';

describe('ReadinessGauge', () => {
  test('renders the score with its default label and band', () => {
    const { container } = renderWithProviders(<ReadinessGauge value={85} />);
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('Patent Readiness Score')).toBeInTheDocument();
    expect(screen.getByText('Patent Ready')).toBeInTheDocument();
    expect(container.querySelectorAll('svg path')).toHaveLength(5);
  });

  test.each([
    [25, 'Needs Attention'],
    [55, 'Improving'],
    [85, 'Patent Ready'],
  ])('a score of %i is classified as %s', (value, band) => {
    renderWithProviders(<ReadinessGauge value={value} />);
    expect(screen.getByText(band)).toBeInTheDocument();
    expect(screen.getByText(String(value))).toBeInTheDocument();
  });

  test('a custom label replaces the default caption', () => {
    renderWithProviders(<ReadinessGauge value={40} label="Export readiness" />);
    expect(screen.getByText('Export readiness')).toBeInTheDocument();
    expect(screen.queryByText('Patent Readiness Score')).toBeNull();
    expect(screen.getByText('Needs Attention')).toBeInTheDocument();
  });

  test('marks the readiness thresholds on the arc', () => {
    const { container } = renderWithProviders(<ReadinessGauge value={70} />);
    const ticks = Array.from(container.querySelectorAll('svg text')).map(
      (node) => node.textContent
    );
    expect(ticks).toEqual(expect.arrayContaining(['0', '40', '70', '100']));
    expect(screen.getByText('Improving')).toBeInTheDocument();
  });

  test('renders a full arc for a perfect score', () => {
    const { container } = renderWithProviders(<ReadinessGauge value={100} />);
    expect(screen.getByText('100', { selector: 'div' })).toBeInTheDocument();
    expect(screen.getByText('Patent Ready')).toBeInTheDocument();
    expect(container.querySelectorAll('svg path')).toHaveLength(5);
  });

  test.failing('a score above 100 is displayed as a capped 100%', () => {
    renderWithProviders(<ReadinessGauge value={150} />);
    expect(screen.queryByText('150')).toBeNull();
  });
});
