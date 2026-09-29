import { renderWithProviders, screen, userEvent } from './test-utils';
import InnovationPassportView from '../src/components/InnovationPassportView';
import type { InnovationPassport } from '../src/types';

const passport: InnovationPassport = {
  id: 'pass-12345678',
  version: 3,
  case_title: 'Ashwagandha Sleep Formulation',
  target_markets: ['India', 'Canada'],
  ingredients: [
    {
      raw_name: 'Ashwagandha',
      botanical_name: 'Withania somnifera',
      origin_status: 'user_confirmed',
      api_monograph_id: 'API-A-101',
      plant_part: 'root',
      quantity_percentage: 40,
    },
    {
      raw_name: 'Brahmi',
      botanical_name: '',
      origin_status: 'unknown',
      api_monograph_id: '',
      plant_part: 'whole plant',
      quantity_percentage: 20,
    },
  ],
  product_form: 'Tablet',
  dosage_form: '500 mg',
  proposed_claims: ['Supports restful sleep'],
  biological_resource_origin: 'Cultivated',
} as unknown as InnovationPassport;

function renderView(overrides: Partial<Parameters<typeof InnovationPassportView>[0]> = {}) {
  const onIntakeSubmit = jest.fn();
  const onSanitizeTest = jest.fn();
  renderWithProviders(
    <InnovationPassportView
      passport={null}
      onUpdatePassport={jest.fn()}
      onIntakeSubmit={onIntakeSubmit}
      onSanitizeTest={onSanitizeTest}
      isLoading={false}
      currentLang="en"
      {...overrides}
    />
  );
  return { onIntakeSubmit, onSanitizeTest };
}

describe('InnovationPassportView intake', () => {
  test('submits the current intake text', async () => {
    const user = userEvent.setup();
    const { onIntakeSubmit } = renderView();
    const textarea = screen.getByPlaceholderText(/Ashwagandha \+ Brahmi tablet/);
    await user.clear(textarea);
    await user.type(textarea, 'Neem + Turmeric, claim: supports immunity');
    await user.click(
      screen.getByRole('button', { name: /Parse Innovation Passport/ })
    );
    expect(onIntakeSubmit).toHaveBeenCalledWith(
      'Neem + Turmeric, claim: supports immunity'
    );
  });

  test('language presets replace the intake text', async () => {
    const user = userEvent.setup();
    const { onIntakeSubmit } = renderView();
    await user.click(screen.getByRole('button', { name: 'Preset: Sleep (EN)' }));
    await user.click(
      screen.getByRole('button', { name: /Parse Innovation Passport/ })
    );
    expect(onIntakeSubmit).toHaveBeenCalledWith(
      'Ashwagandha + Brahmi formulation, claim: supports healthy sleep, target markets: India, USA, Canada'
    );
  });

  test('intake is disabled while loading', () => {
    renderView({ isLoading: true });
    const button = screen.getByRole('button', { name: /Processing Intake/ });
    expect(button).toBeDisabled();
  });

  test('renders the adversarial sandbox extraction action', async () => {
    const user = userEvent.setup();
    const { onSanitizeTest } = renderView();
    await user.click(
      screen.getByRole('button', {
        name: /Run Sandboxed Extraction & Threat Neutralization/,
      })
    );
    expect(onSanitizeTest).toHaveBeenCalledTimes(1);
    expect(onSanitizeTest.mock.calls[0][0]).toContain(
      'Ignore all previous instructions'
    );
  });

  test('renders no structured passport without one', () => {
    renderView();
    expect(screen.queryByText(/Passport ID:/)).toBeNull();
    expect(
      screen.getByText('Multilingual Innovation Intake (Text / Voice / OCR)')
    ).toBeInTheDocument();
  });
});

describe('InnovationPassportView passport rendering', () => {
  test('renders passport header, markets and version', () => {
    renderView({ passport });
    expect(screen.getByText('Ashwagandha Sleep Formulation')).toBeInTheDocument();
    expect(screen.getByText(/Passport ID: pass-12345678/)).toBeInTheDocument();
    expect(screen.getByText('Version 3.0')).toBeInTheDocument();
    expect(screen.getByText('India')).toBeInTheDocument();
    expect(screen.getByText('Canada')).toBeInTheDocument();
  });

  test('renders ingredient matrix with origin badges and fallbacks', () => {
    renderView({ passport });
    expect(screen.getByText('Ashwagandha')).toBeInTheDocument();
    expect(screen.getByText('Withania somnifera')).toBeInTheDocument();
    expect(screen.getByText('User Confirmed')).toBeInTheDocument();
    expect(screen.getByText('Unknown / Missing')).toBeInTheDocument();
    expect(screen.getByText('Botanical name pending')).toBeInTheDocument();
    expect(screen.getByText('API-A-101')).toBeInTheDocument();
    expect(screen.getByText('Not mapped')).toBeInTheDocument();
    expect(screen.getByText(/root \(40%\)/)).toBeInTheDocument();
  });

  test('renders key facts without the removed scan-to-download panel', () => {
    renderView({ passport });
    expect(screen.getByText(/Tablet \(500 mg\)/)).toBeInTheDocument();
    expect(screen.getByText('Supports restful sleep')).toBeInTheDocument();
    expect(screen.getByText('Cultivated')).toBeInTheDocument();
    expect(screen.queryByText('Scan to download passport')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Download \.JSON/ })).not.toBeInTheDocument();
  });
});
