import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import { renderWithProviders, screen, userEvent, waitFor, act } from './test-utils';
import AICopilot from '../src/components/AICopilot';

jest.mock('../src/hooks/useVoiceAssistant', () => ({
  useVoiceAssistant: () => ({
    supported: false,
    isListening: false,
    interim: '',
    error: null,
    synthSupported: false,
    speak: jest.fn(),
    cancelSpeech: jest.fn(),
    startListening: jest.fn(),
    stopListening: jest.fn(),
    clearError: jest.fn(),
  }),
}));

Element.prototype.scrollIntoView = jest.fn();

const BASE = 'http://localhost/api/v1';

const statsPayload = {
  rag_types: ['hybrid', 'production'],
  default_rag_type: 'hybrid',
  config: { default: 'hybrid', cache_ttl: 60, rate_limit: 120 },
  per_type: { hybrid: { available: true, default: true }, production: { available: true } },
};

const longContent =
  'Ashwagandha root extract is described in the Ayurvedic Pharmacopoeia of India with recommended dosage and processing controls that must be matched by the applicant.';

function mountHandlers() {
  server.use(
    http.get(`${BASE}/chat/suggested-questions`, () => HttpResponse.json({ questions: [] })),
    http.get(`${BASE}/rag/search/stats`, () => HttpResponse.json(statsPayload))
  );
}

async function sendQuestion(user: ReturnType<typeof userEvent.setup>, text: string) {
  const input = screen.getByPlaceholderText(/ask about patentability/);
  await user.type(input, `${text}{Enter}`);
}

beforeEach(() => {
  window.localStorage.removeItem('ipsakti:rag-engine');
});

describe('AICopilot core flow', () => {
  test('renders header, disclaimer, default source panel and engine stats', async () => {
    mountHandlers();
    renderWithProviders(<AICopilot />);
    expect(
      screen.getByText('Jurisdiction-Aware AI Copilot')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/AI Copilot provides informational guidance/)
    ).toBeInTheDocument();
    expect(
      await screen.findByText('Ayurvedic Pharmacopoeia of India')
    ).toBeInTheDocument();
    expect(await screen.findByText('Can I patent this?')).toBeInTheDocument();
    expect(await screen.findByText(/Engines:/)).toBeInTheDocument();
    expect(screen.getByText(/default: hybrid · TTL 60s/)).toBeInTheDocument();
  });

  test('sends a question and renders the grounded answer with confidence', async () => {
    mountHandlers();
    const user = userEvent.setup();
    let body: any = null;
    server.use(
      http.post(`${BASE}/chat/query`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({
          answer: 'Yes — novelty and inventive step are required.',
          sources: [],
          confidence: 0.8,
        });
      })
    );
    renderWithProviders(<AICopilot />);
    await sendQuestion(user, 'Can I patent this?');
    expect(await screen.findByText('Can I patent this?')).toBeInTheDocument();
    expect(
      await screen.findByText('Yes — novelty and inventive step are required.')
    ).toBeInTheDocument();
    expect(await screen.findByText(/Confidence 80%/)).toBeInTheDocument();
    await waitFor(() => expect(body).not.toBeNull());
    expect(body.question).toBe('Can I patent this?');
    expect(body.context).toEqual({ jurisdiction: 'India' });
    expect(screen.getByPlaceholderText(/ask about patentability/)).toHaveValue('');
  });

  test('clicking a suggestion chip sends that question', async () => {
    mountHandlers();
    const user = userEvent.setup();
    let body: any = null;
    server.use(
      http.post(`${BASE}/chat/query`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ answer: 'Maybe.', sources: [], confidence: 0.5 });
      })
    );
    renderWithProviders(<AICopilot />);
    const chip = await screen.findByRole('button', { name: 'Is Neem already patented?' });
    await user.click(chip);
    await waitFor(() => expect(body).not.toBeNull());
    expect(body.question).toBe('Is Neem already patented?');
  });

  test('shows the loading indicator while the query is pending', async () => {
    mountHandlers();
    const user = userEvent.setup();
    let release: (response: Response) => void = () => {};
    server.use(
      http.post(`${BASE}/chat/query`, () =>
        new Promise<Response>((resolve) => {
          release = resolve;
        })
      )
    );
    renderWithProviders(<AICopilot />);
    await sendQuestion(user, 'Is this label compliant?');
    expect(
      await screen.findByText('Retrieving sources & reasoning...')
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/ask about patentability/)
    ).toBeInTheDocument();
    await act(async () => {
      release(
        HttpResponse.json({ answer: 'Label checked.', sources: [], confidence: 0.7 })
      );
    });
    expect(await screen.findByText('Label checked.')).toBeInTheDocument();
    expect(
      screen.queryByText('Retrieving sources & reasoning...')
    ).not.toBeInTheDocument();
  });

  test('expands the per-message citations toggle', async () => {
    mountHandlers();
    const user = userEvent.setup();
    server.use(
      http.post(`${BASE}/chat/query`, () =>
        HttpResponse.json({
          answer: 'Grounded answer.',
          confidence: 0.7,
          sources: [
            {
              source: 'Ayurvedic Pharmacopoeia of India, Edition 2024',
              category: 'Pharmacopoeia',
              content: longContent,
            },
          ],
        })
      )
    );
    renderWithProviders(<AICopilot />);
    await sendQuestion(user, 'What is the dosage?');
    const toggle = await screen.findByRole('button', { name: /1 sources used/ });
    await user.click(toggle);
    expect(await screen.findByText(longContent)).toBeInTheDocument();
    expect(
      screen.getAllByText('Ayurvedic Pharmacopoeia of India, Edition 2024')
    ).toHaveLength(2);
  });

  test('surfaces a friendly error when the chat endpoint fails', async () => {
    mountHandlers();
    const user = userEvent.setup();
    server.use(
      http.post(`${BASE}/chat/query`, () =>
        HttpResponse.text('boom', { status: 500 })
      )
    );
    renderWithProviders(<AICopilot />);
    await sendQuestion(user, 'Will this break?');
    // The failure must name the actual cause and be marked as a refusal, so it
    // can never be read as a sourced answer.
    const notice = await screen.findByText(
      /the request did not complete/i
    );
    expect(notice).toBeInTheDocument();
    expect(
      screen.getByText('No answer given — this reply is not backed by a cited source')
    ).toBeInTheDocument();
    expect(screen.getByText(/Nothing was cited because no sources were retrieved/)).toBeInTheDocument();
  });

  test('jurisdiction toggle changes the request context', async () => {
    mountHandlers();
    const user = userEvent.setup();
    let body: any = null;
    server.use(
      http.post(`${BASE}/chat/query`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ answer: 'Done.', sources: [], confidence: 0.5 });
      })
    );
    renderWithProviders(<AICopilot />);
    await user.click(await screen.findByRole('button', { name: 'International' }));
    await sendQuestion(user, 'Any FTO issues?');
    await waitFor(() => expect(body).not.toBeNull());
    expect(body.context).toEqual({ jurisdiction: 'International' });
  });

  test('submit stays disabled until there is a question', async () => {
    mountHandlers();
    const user = userEvent.setup();
    const { container } = renderWithProviders(<AICopilot />);
    const submit = container.querySelector('button[type="submit"]') as HTMLButtonElement;
    expect(submit).toBeDisabled();
    await user.type(
      screen.getByPlaceholderText(/ask about patentability/),
      'hello'
    );
    expect(submit).toBeEnabled();
  });
});

describe('AICopilot RAG engine path', () => {
  test('hybrid engine routes through /rag/search with rag_type and renders metrics', async () => {
    mountHandlers();
    const user = userEvent.setup();
    let body: any = null;
    server.use(
      http.post(`${BASE}/rag/search`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({
          rag_type: 'hybrid',
          count: 3,
          latency_ms: 42.4,
          confidence: 0.77,
          sources: [
            { source: 'PubMed', category: 'Peer-Reviewed', content: longContent },
          ],
        });
      })
    );
    renderWithProviders(<AICopilot />);
    await user.click(await screen.findByRole('button', { name: 'RAG Hybrid' }));
    expect(window.localStorage.getItem('ipsakti:rag-engine')).toBe('hybrid');
    await sendQuestion(user, 'Evidence for sleep claim?');
    expect(
      await screen.findByText(/\*\*RAG hybrid\*\* — 3 source\(s\) retrieved in 42ms/)
    ).toBeInTheDocument();
    expect(await screen.findByText(/Confidence 77%/)).toBeInTheDocument();
    expect(screen.getByText(/RAG hybrid · 42ms · 3 src/)).toBeInTheDocument();
    await waitFor(() => expect(body).not.toBeNull());
    expect(body.query).toBe('Evidence for sleep claim?');
    expect(body.rag_type).toBe('hybrid');
    expect(body.top_k).toBe(8);
    expect(body.jurisdiction).toBe('India');
  });

  test('surfaces RAG refusal blocks in the transcript', async () => {
    mountHandlers();
    const user = userEvent.setup();
    server.use(
      http.post(`${BASE}/rag/search`, () =>
        HttpResponse.json({
          rag_type: 'hybrid',
          count: 0,
          latency_ms: 8,
          confidence: 0,
          sources: [],
          refusal: { reason: 'Therapeutic claim requires clinical evidence' },
        })
      )
    );
    renderWithProviders(<AICopilot />);
    await user.click(await screen.findByRole('button', { name: 'RAG Hybrid' }));
    await sendQuestion(user, 'Cure diabetes?');
    expect(
      await screen.findByText(/Request blocked: Therapeutic claim requires clinical evidence/)
    ).toBeInTheDocument();
    expect(screen.getByText(/No sources matched/)).toBeInTheDocument();
  });
});

describe('AICopilot refusal handling defect', () => {
  test.failing(
    'drops the copilot-engine refusal reason from the transcript',
    async () => {
      mountHandlers();
      const user = userEvent.setup();
      server.use(
        http.post(`${BASE}/chat/query`, () =>
          HttpResponse.json({
            answer: 'Standard answer text.',
            sources: [],
            confidence: 0.5,
            refusal: { reason: 'Unsupported therapeutic claim detected' },
          })
        )
      );
      renderWithProviders(<AICopilot />);
      await sendQuestion(user, 'Does this cure cold?');
      expect(
        await screen.findByText(/Unsupported therapeutic claim detected/)
      ).toBeInTheDocument();
    }
  );
});
