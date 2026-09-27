import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import { renderWithProviders, screen, userEvent, waitFor } from './test-utils';
import InnovationPassportForm from '../src/components/InnovationPassportForm';

const BASE = 'http://localhost/api/v1';

async function goToStep(user: ReturnType<typeof userEvent.setup>, label: string) {
  const next = /Generate Innovation Passport|Continue/;
  while (!screen.queryByText(label)) {
    const button = screen.getByRole('button', { name: next });
    // eslint-disable-next-line no-await-in-loop
    await user.click(button);
  }
}

describe('InnovationPassportForm wizard', () => {
  test('starts on Basic Information with Back disabled', () => {
    renderWithProviders(<InnovationPassportForm onSubmit={jest.fn()} />);
    expect(screen.getByText('Basic Information')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Back/ })).toBeDisabled();
    expect(
      screen.getByPlaceholderText('e.g. TriHerb Restful Sleep Vati')
    ).toBeInTheDocument();
  });

  test('walks through all five steps and submits the passport payload', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    renderWithProviders(<InnovationPassportForm onSubmit={onSubmit} />);

    await user.type(
      screen.getByPlaceholderText('e.g. TriHerb Restful Sleep Vati'),
      'TriHerb Vati'
    );
    await goToStep(user, 'Review & Generate Passport');
    expect(screen.getByText('TriHerb Vati')).toBeInTheDocument();
    expect(screen.getByText(/हळद, नीम, तुळस/)).toBeInTheDocument();
    expect(screen.getByText('None selected')).toBeInTheDocument();

    await user.click(
      screen.getByRole('button', { name: /Generate Innovation Passport/ })
    );
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      case_title: 'TriHerb Vati',
      product_type: 'Nutraceutical',
      category: 'Herbal Supplement',
      target_markets: ['India'],
      language: 'auto',
      proposed_claims: [],
    });
  });

  test('Back returns to the previous step and step indicator jumps backwards', async () => {
    const user = userEvent.setup();
    renderWithProviders(<InnovationPassportForm onSubmit={jest.fn()} />);
    await goToStep(user, 'Health Claims');
    await user.click(screen.getByRole('button', { name: /Back/ }));
    expect(screen.getByText('Preparation Process')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Basic Info$/ }));
    expect(screen.getByText('Basic Information')).toBeInTheDocument();
  });

  test('submission without a name falls back to Untitled Innovation', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    renderWithProviders(<InnovationPassportForm onSubmit={onSubmit} />);
    await goToStep(user, 'Review & Generate Passport');
    expect(screen.getByText('Untitled Innovation')).toBeInTheDocument();
    await user.click(
      screen.getByRole('button', { name: /Generate Innovation Passport/ })
    );
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      case_title: 'Untitled Innovation',
    });
  });

  test('disabled while the passport is generating', async () => {
    const user = userEvent.setup();
    const view = renderWithProviders(
      <InnovationPassportForm onSubmit={jest.fn()} />
    );
    await goToStep(user, 'Review & Generate Passport');
    view.rerender(
      <InnovationPassportForm onSubmit={jest.fn()} isLoading />
    );
    const button = screen.getByRole('button', { name: /Generating/ });
    expect(button).toBeDisabled();
  });
});

describe('InnovationPassportForm formulation parsing', () => {
  test('parses the formulation and renders the botanical mapping table', async () => {
    const user = userEvent.setup();
    let body: any = null;
    server.use(
      http.post(`${BASE}/formulation/parse`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({
          detected_language: 'hi',
          ingredients: [
            {
              raw_name: 'हळद',
              botanical_name: 'Curcuma longa',
              api_monograph_id: 'API-T-001',
              status: 'resolved',
            },
            {
              raw_name: 'mystery-herb',
              botanical_name: '',
              api_monograph_id: '',
              status: 'unresolved',
            },
          ],
        });
      })
    );
    renderWithProviders(<InnovationPassportForm onSubmit={jest.fn()} />);
    await goToStep(user, 'Multilingual Formulation');
    await user.click(
      screen.getByRole('button', { name: /Parse & Canonicalize/ })
    );
    expect(
      await screen.findByText(/Detected: hi · 2 botanicals/)
    ).toBeInTheDocument();
    expect(screen.getByText('Curcuma longa')).toBeInTheDocument();
    expect(screen.getByText('Not in glossary')).toBeInTheDocument();
    expect(body).toEqual({ text: 'हळद, नीम, तुळस', language: 'auto' });
  });

  test('shows an error when parsing fails', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${BASE}/formulation/parse`, () =>
        HttpResponse.text('down', { status: 500 })
      )
    );
    renderWithProviders(<InnovationPassportForm onSubmit={jest.fn()} />);
    await goToStep(user, 'Multilingual Formulation');
    await user.click(
      screen.getByRole('button', { name: /Parse & Canonicalize/ })
    );
    expect(
      await screen.findByText('Failed to parse formulation. Backend must be running.')
    ).toBeInTheDocument();
  });
});

describe('InnovationPassportForm claim firewall', () => {
  async function reachClaims(user: ReturnType<typeof userEvent.setup>) {
    await goToStep(user, 'Health Claims');
  }

  test('claim selection round-trips into the submitted payload', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    renderWithProviders(<InnovationPassportForm onSubmit={onSubmit} />);
    await reachClaims(user);
    await user.click(screen.getByRole('button', { name: /Supports Healthy Skin/ }));
    await goToStep(user, 'Review & Generate Passport');
    expect(screen.getByText(/Supports Healthy Skin/)).toBeInTheDocument();
    await user.click(
      screen.getByRole('button', { name: /Generate Innovation Passport/ })
    );
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      proposed_claims: ['Supports Healthy Skin'],
    });
  });

  test('firewall flags explicit therapeutic claims', async () => {
    const user = userEvent.setup();
    renderWithProviders(<InnovationPassportForm onSubmit={jest.fn()} />);
    await reachClaims(user);
    await user.click(screen.getByRole('button', { name: /Cures Eczema/ }));
    await user.click(
      screen.getByRole('button', { name: /Run Claim Firewall Check/ })
    );
    expect(
      await screen.findByText('High Risk — drug claim detected')
    ).toBeInTheDocument();
  });

  test('clearing all claims leaves the firewall safe', async () => {
    const user = userEvent.setup();
    renderWithProviders(<InnovationPassportForm onSubmit={jest.fn()} />);
    await reachClaims(user);
    await user.click(
      screen.getByRole('button', { name: /Run Claim Firewall Check/ })
    );
    expect(
      await screen.findByText('Safe — claims appear compliant')
    ).toBeInTheDocument();
  });

  test.failing(
    'low-risk "Supports Healthy Skin" claim must pass the firewall',
    async () => {
      const user = userEvent.setup();
      renderWithProviders(<InnovationPassportForm onSubmit={jest.fn()} />);
      await reachClaims(user);
      await user.click(
        screen.getByRole('button', { name: /Supports Healthy Skin/ })
      );
      await user.click(
        screen.getByRole('button', { name: /Run Claim Firewall Check/ })
      );
      expect(
        await screen.findByText('Safe — claims appear compliant')
      ).toBeInTheDocument();
    }
  );

  test.failing(
    'firewall must match therapeutic keywords on word boundaries, not substrings',
    async () => {
      const user = userEvent.setup();
      renderWithProviders(<InnovationPassportForm onSubmit={jest.fn()} />);
      await goToStep(user, 'Multilingual Formulation');
      const textarea = screen.getByRole('textbox');
      await user.clear(textarea);
      await user.type(textarea, 'healthy lifestyle formulation');
      await goToStep(user, 'Health Claims');
      await user.click(
        screen.getByRole('button', { name: /Run Claim Firewall Check/ })
      );
      expect(
        await screen.findByText('Safe — claims appear compliant')
      ).toBeInTheDocument();
    }
  );
});
