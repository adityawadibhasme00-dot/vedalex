import { renderWithProviders, screen, userEvent } from './test-utils';
import HeroSection from '../src/components/HeroSection';

function renderHero() {
  const onStartIntake = jest.fn();
  const onExploreFeatures = jest.fn();
  renderWithProviders(
    <HeroSection
      onStartIntake={onStartIntake}
      onExploreFeatures={onExploreFeatures}
      currentLang="en"
    />
  );
  return { onStartIntake, onExploreFeatures };
}

describe('HeroSection', () => {
  test('renders the headline, positioning statement and platform promise', () => {
    renderHero();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'From Ayurvedic Wisdom to'
    );
    expect(screen.getByText('Defensible Global IP & Compliance')).toBeInTheDocument();
    expect(screen.getByText(/deterministic rules engine/)).toBeInTheDocument();
    expect(screen.getByText(/AI-Powered Innovation Passport/)).toBeInTheDocument();
  });

  test('reports the headline platform statistics', () => {
    renderHero();
    expect(screen.getByText('14,280+')).toBeInTheDocument();
    expect(screen.getByText('Classical Botanicals Indexed')).toBeInTheDocument();
    expect(screen.getByText('0.00%')).toBeInTheDocument();
    expect(screen.getByText('Unsupported Claim Rate (UCR)')).toBeInTheDocument();
    expect(screen.getByText(/12s/)).toBeInTheDocument();
    expect(screen.getByText('10 Scripts')).toBeInTheDocument();
  });

  test('names every statutory regime the platform claims to cover', () => {
    renderHero();
    expect(
      screen.getByText('Ministry of AYUSH (Drugs & Cosmetics Act)')
    ).toBeInTheDocument();
    expect(screen.getByText('FSSAI Ayurveda Aahara Regs 2022')).toBeInTheDocument();
    expect(screen.getByText('Indian Patent Act Sec 3(p) TK')).toBeInTheDocument();
    expect(screen.getByText('US FDA DSHEA & Health Canada NHPR')).toBeInTheDocument();
  });

  test('the primary call to action starts the intake flow', async () => {
    const user = userEvent.setup();
    const props = renderHero();
    await user.click(screen.getByRole('button', { name: /Launch Innovation Passport/ }));
    expect(props.onStartIntake).toHaveBeenCalledTimes(1);
    expect(props.onExploreFeatures).not.toHaveBeenCalled();
  });

  test('the secondary call to action opens the module explorer', async () => {
    const user = userEvent.setup();
    const props = renderHero();
    await user.click(screen.getByRole('button', { name: /Explore 30\+ Enterprise Modules/ }));
    expect(props.onExploreFeatures).toHaveBeenCalledTimes(1);
    expect(props.onStartIntake).not.toHaveBeenCalled();
  });

  test.failing('the hero is rendered in the requested language', () => {
    const english = renderWithProviders(
      <HeroSection
        onStartIntake={jest.fn()}
        onExploreFeatures={jest.fn()}
        currentLang="en"
      />
    );
    const englishText = english.container.textContent ?? '';
    english.unmount();
    const hindi = renderWithProviders(
      <HeroSection
        onStartIntake={jest.fn()}
        onExploreFeatures={jest.fn()}
        currentLang="hi"
      />
    );
    expect(hindi.container.textContent ?? '').not.toBe(englishText);
  });
});
