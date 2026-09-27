import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import { renderWithProviders, screen, userEvent, waitFor } from './test-utils';
import { AgentHub } from '../src/components/AgentHub';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

const BASE = 'http://localhost/api/v1';

const agentsPayload = {
  count: 2,
  phases: ['ip'],
  agents: [
    {
      slug: 'prior-art',
      label: 'Prior Art Scout',
      phase: 'ip',
      category_label: 'Intellectual Property',
      description: 'Searches patent corpora',
      enabled_by_default: true,
      requires_evidence: true,
      live_default: 'off',
    },
    {
      slug: 'fto-check',
      label: 'FTO Checker',
      phase: 'ip',
      category_label: 'Intellectual Property',
      description: 'Freedom-to-operate screening',
      enabled_by_default: true,
      requires_evidence: false,
      live_default: 'off',
    },
  ],
};

const planPayload = {
  brief: 'Canada export for Ashwagandha extract',
  intents: [{ intent: 'regulatory', label: 'Regulatory roadmap' }],
  entities: { target_markets: ['Canada'] },
  agents: [
    {
      slug: 'prior-art',
      label: 'Prior Art Scout',
      phase: 'ip',
      description: 'Searches patent corpora',
      reason: 'novelty evidence needed',
      tools: ['bm25', 'qdrant'],
      workflow_steps: ['search', 'rank'],
      questions: 1,
    },
  ],
  total_steps: 2,
};

const runPayload = {
  run_id: 'run-abcdef12',
  project_id: 'proj-1',
  status: 'completed',
  chain: [],
  base_inputs: {},
  steps: [
    {
      seq: 1,
      agent_slug: 'prior-art',
      label: 'Search prior art',
      status: 'completed',
      summary: 'Found 12 documents',
      output: {},
    },
  ],
  verification: {
    confidence: 91,
    band: 'high',
    checks: [{ name: 'grounding', status: 'pass', detail: 'all cited', score: 1 }],
    note: 'ok',
  },
};

function mockAgentsEndpoint() {
  server.use(
    http.get(`${BASE}/innolab/agents`, () => HttpResponse.json(agentsPayload)),
    http.get(`${BASE}/innolab/agents/:slug/workflow`, ({ params }) =>
      HttpResponse.json({
        slug: params.slug,
        label: 'wf',
        phase: 'ip',
        category_label: 'ip',
        description: 'd',
        enabled_by_default: true,
        requires_evidence: true,
        live_default: 'off',
        steps: [{ label: 'Step 1' }],
        questions: [],
      })
    )
  );
}

beforeEach(() => {
  mockPush.mockClear();
});

describe('AgentHub', () => {
  test('loads agents and groups them under their phase', async () => {
    let workflowCalls = 0;
    server.use(
      http.get(`${BASE}/innolab/agents`, () => HttpResponse.json(agentsPayload)),
      http.get(`${BASE}/innolab/agents/:slug/workflow`, ({ params }) => {
        workflowCalls += 1;
        return HttpResponse.json({
          slug: params.slug,
          label: 'wf',
          phase: 'ip',
          category_label: 'ip',
          description: 'd',
          enabled_by_default: true,
          requires_evidence: true,
          live_default: 'off',
          steps: [],
          questions: [],
        });
      })
    );
    renderWithProviders(<AgentHub />);
    expect(await screen.findByText('Prior Art Scout')).toBeInTheDocument();
    expect(screen.getByText('FTO Checker')).toBeInTheDocument();
    expect(screen.getByText(/Intellectual Property/)).toBeInTheDocument();
    await waitFor(() => expect(workflowCalls).toBe(2));
  });

  test('shows an error with a retry action when loading fails', async () => {
    const user = userEvent.setup();
    let fail = true;
    server.use(
      http.get(`${BASE}/innolab/agents`, () => {
        if (fail) {
          fail = false;
          return HttpResponse.text('hub unavailable', { status: 500 });
        }
        return HttpResponse.json(agentsPayload);
      }),
      http.get(`${BASE}/innolab/agents/:slug/workflow`, () =>
        HttpResponse.json({
          slug: 'x',
          label: 'wf',
          phase: 'ip',
          category_label: 'ip',
          description: 'd',
          enabled_by_default: true,
          requires_evidence: true,
          live_default: 'off',
          steps: [],
          questions: [],
        })
      )
    );
    renderWithProviders(<AgentHub />);
    expect(await screen.findByText(/hub unavailable/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('Prior Art Scout')).toBeInTheDocument();
  });

  test('plans a brief and renders the ordered agent chain', async () => {
    const user = userEvent.setup();
    mockAgentsEndpoint();
    let planBody: any = null;
    server.use(
      http.post(`${BASE}/innolab/orchestrator/plan`, async ({ request }) => {
        planBody = await request.json();
        return HttpResponse.json(planPayload);
      })
    );
    renderWithProviders(<AgentHub />);
    await screen.findByText('Prior Art Scout');
    const planButton = screen.getByRole('button', { name: /Plan/ });
    expect(planButton).toBeDisabled();
    await user.type(
      screen.getByPlaceholderText(/hydroalcoholic extract/),
      'Canada export for Ashwagandha extract'
    );
    expect(planButton).toBeEnabled();
    await user.click(planButton);
    expect(await screen.findByText(/→ 1 agents · 2 workflow steps/)).toBeInTheDocument();
    expect(screen.getByText('Regulatory roadmap')).toBeInTheDocument();
    expect(screen.getByText(/novelty evidence needed/)).toBeInTheDocument();
    expect(screen.getByText(/tools: bm25 · qdrant/)).toBeInTheDocument();
    expect(planBody).toEqual({ brief: 'Canada export for Ashwagandha extract' });
  });

  test('runs the plan and renders verification results', async () => {
    const user = userEvent.setup();
    mockAgentsEndpoint();
    let runBody: any = null;
    server.use(
      http.post(`${BASE}/innolab/orchestrator/plan`, () =>
        HttpResponse.json(planPayload)
      ),
      http.post(`${BASE}/innolab/orchestrator/run`, async ({ request }) => {
        runBody = await request.json();
        return HttpResponse.json(runPayload);
      })
    );
    renderWithProviders(<AgentHub />);
    await screen.findByText('Prior Art Scout');
    await user.type(
      screen.getByPlaceholderText(/hydroalcoholic extract/),
      'Canada export'
    );
    await user.click(screen.getByRole('button', { name: /Plan/ }));
    await user.click(
      await screen.findByRole('button', { name: /Run this plan/ })
    );
    expect(
      await screen.findByText(/HIGH verification · 91% confidence/)
    ).toBeInTheDocument();
    expect(screen.getByText(/Found 12 documents/)).toBeInTheDocument();
    expect(runBody).toEqual({ brief: 'Canada export for Ashwagandha extract' });
  });

  test('clear removes the plan from the view', async () => {
    const user = userEvent.setup();
    mockAgentsEndpoint();
    server.use(
      http.post(`${BASE}/innolab/orchestrator/plan`, () =>
        HttpResponse.json(planPayload)
      )
    );
    renderWithProviders(<AgentHub />);
    await screen.findByText('Prior Art Scout');
    await user.type(
      screen.getByPlaceholderText(/hydroalcoholic extract/),
      'brief'
    );
    await user.click(screen.getByRole('button', { name: /Plan/ }));
    await screen.findByText(/→ 1 agents/);
    await user.click(screen.getByRole('button', { name: 'Clear' }));
    await waitFor(() =>
      expect(screen.queryByText(/→ 1 agents/)).toBeNull()
    );
  });

  test('starting an agent navigates to its workspace', async () => {
    const user = userEvent.setup();
    mockAgentsEndpoint();
    renderWithProviders(<AgentHub />);
    await screen.findByText('Prior Art Scout');
    const startButtons = screen.getAllByRole('button', { name: /Start Agent/ });
    await user.click(startButtons[0]);
    expect(mockPush).toHaveBeenCalledWith('/innovation-lab/agents/prior-art');
  });

  test('agent cards fall back to the API description when no blurb exists', async () => {
    mockAgentsEndpoint();
    renderWithProviders(<AgentHub />);
    expect(await screen.findByText('Freedom-to-operate screening')).toBeInTheDocument();
  });
});
