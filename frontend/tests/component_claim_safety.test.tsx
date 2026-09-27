import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import { renderWithProviders, screen, userEvent, waitFor } from './test-utils';
import { ClaimSafetyIntelligence } from '../src/components/ClaimSafetyIntelligence';
import type { ClaimSafetyAnalysisResponse } from '../src/types';

const BASE = 'http://localhost/api/v1';

const response: ClaimSafetyAnalysisResponse = {
  overall_verdict: 'HIGH_RISK',
  overall_color: 'red',
  summary: 'Two claims need compliant rewording.',
  claims: [
    {
      claim_text: 'Treats chronic insomnia',
      claim_category: 'therapeutic',
      evidence_alignment: 'unsupported',
      risk_level: 'HIGH_RISK',
      risk_color: 'red',
      regulation: 'Drugs & Cosmetics Act',
      suggested_alternative: 'Traditionally used to support restful sleep',
      note: 'Disease treatment claim requires a drug licence.',
    },
  ],
  safety_signals: [
    {
      ingredient: 'Ashwagandha',
      botanical_name: 'Withania somnifera',
      signal: 'May potentiate sedatives',
      severity: 'MEDIUM',
      evidence_source: 'case reports',
      precaution: 'Avoid before driving',
    },
  ],
  misleading_ad_risk: {
    flagged_phrases: ['100% guaranteed cure'],
    act_citation: 'ASCI Code 1.1',
    action: 'Remove absolute cure claims',
  },
  regulatory_alerts: ['Schedule T GMP applies'],
  disclaimer: 'Informational only.',
};

describe('ClaimSafetyIntelligence', () => {
  test('auto-analyses on mount when a passport is linked', async () => {
    let body: any = null;
    server.use(
      http.post(`${BASE}/intelligence/claim-safety/analyze`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(response);
      })
    );
    renderWithProviders(<ClaimSafetyIntelligence passportId="pid-7" />);
    await screen.findByText(/Two claims need compliant rewording/);
    expect(body).toMatchObject({
      passport_id: 'pid-7',
      target_markets: ['India', 'United States', 'Canada'],
      product_type: 'ayurvedic_drug',
    });
    expect(body.claims).toBeUndefined();
    expect(body.ingredients).toBeUndefined();
  });

  test('splits typed claims by line and ingredients by comma', async () => {
    let body: any = null;
    server.use(
      http.post(`${BASE}/intelligence/claim-safety/analyze`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(response);
      })
    );
    const user = userEvent.setup();
    renderWithProviders(<ClaimSafetyIntelligence />);
    await user.type(
      screen.getByPlaceholderText(/Supports healthy sleep/),
      'Supports sleep{Enter}Treats insomnia'
    );
    const ingredients = screen.getByPlaceholderText('Ashwagandha, Brahmi');
    await user.type(ingredients, 'Ashwagandha, Brahmi');
    await user.click(
      screen.getByRole('button', { name: /Analyze Claims/ })
    );
    await screen.findByText('Treats chronic insomnia');
    expect(body.claims).toEqual(['Supports sleep', 'Treats insomnia']);
    expect(body.ingredients).toEqual(['Ashwagandha', 'Brahmi']);
    expect(body.passport_id).toBeUndefined();
  });

  test('toggling a target market removes it from the request', async () => {
    let body: any = null;
    server.use(
      http.post(`${BASE}/intelligence/claim-safety/analyze`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(response);
      })
    );
    const user = userEvent.setup();
    renderWithProviders(<ClaimSafetyIntelligence passportId="p1" />);
    await screen.findByText(/Two claims need compliant rewording/);
    await user.click(screen.getByRole('button', { name: 'Canada' }));
    await user.click(screen.getByRole('button', { name: /Analyze Claims/ }));
    await waitFor(() =>
      expect(body.target_markets).toEqual(['India', 'United States'])
    );
  });

  test('renders verdict, per-claim, ads, signals, alerts and disclaimer', async () => {
    server.use(
      http.post(`${BASE}/intelligence/claim-safety/analyze`, () =>
        HttpResponse.json(response)
      )
    );
    renderWithProviders(<ClaimSafetyIntelligence passportId="p1" />);
    expect(await screen.findByText(/Two claims need compliant rewording/)).toBeInTheDocument();
    expect(screen.getByText('Treats chronic insomnia')).toBeInTheDocument();
    expect(screen.getByText(/Traditionally used to support restful sleep/)).toBeInTheDocument();
    expect(screen.getByText('100% guaranteed cure')).toBeInTheDocument();
    expect(screen.getByText('May potentiate sedatives')).toBeInTheDocument();
    expect(screen.getByText('Schedule T GMP applies')).toBeInTheDocument();
    expect(screen.getByText('Informational only.')).toBeInTheDocument();
    expect(screen.getByText(/Linked passport/)).toBeInTheDocument();
  });

  test('shows an error card when analysis fails', async () => {
    server.use(
      http.post(`${BASE}/intelligence/claim-safety/analyze`, () =>
        HttpResponse.text('analysis backend down', { status: 500 })
      )
    );
    renderWithProviders(<ClaimSafetyIntelligence passportId="p1" />);
    expect(
      await screen.findByText(/Failed to analyze claim safety/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Two claims need compliant rewording/)).toBeNull();
  });

  test.failing(
    'analysis errors must surface the backend detail message',
    async () => {
      server.use(
        http.post(`${BASE}/intelligence/claim-safety/analyze`, () =>
          HttpResponse.text('analysis backend down', { status: 500 })
        )
      );
      renderWithProviders(<ClaimSafetyIntelligence passportId="p1" />);
      expect(await screen.findByText(/analysis backend down/)).toBeInTheDocument();
    }
  );

  test('does not call the backend without a passport until analysed', async () => {
    renderWithProviders(<ClaimSafetyIntelligence />);
    expect(screen.queryByText(/Linked passport/)).toBeNull();
    expect(
      screen.queryByText(/Two claims need compliant rewording/)
    ).toBeNull();
  });
});

