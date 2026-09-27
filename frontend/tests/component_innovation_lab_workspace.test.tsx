import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import { renderWithProviders, screen } from './test-utils';
import { InnovationLabWorkspace } from '../src/components/InnovationLabWorkspace';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

const BASE = 'http://localhost/api/v1';

describe('InnovationLabWorkspace', () => {
  test('renders the Agent Hub shell with loaded agents', async () => {
    server.use(
      http.get(`${BASE}/innolab/agents`, () =>
        HttpResponse.json({
          count: 1,
          phases: ['engineering'],
          agents: [
            {
              slug: 'inventor',
              label: 'Inventor Assistant',
              phase: 'engineering',
              category_label: 'Engineering',
              description: 'Idea-to-concept helper',
              enabled_by_default: true,
              requires_evidence: false,
              live_default: 'off',
            },
          ],
        })
      ),
      http.get(`${BASE}/innolab/agents/:slug/workflow`, () =>
        HttpResponse.json({
          slug: 'inventor',
          label: 'wf',
          phase: 'engineering',
          category_label: 'Engineering',
          description: 'd',
          enabled_by_default: true,
          requires_evidence: false,
          live_default: 'off',
          steps: [],
          questions: [],
        })
      )
    );
    renderWithProviders(<InnovationLabWorkspace />);
    expect(await screen.findByText('Inventor Assistant')).toBeInTheDocument();
    expect(screen.getByText('Agent Hub')).toBeInTheDocument();
    expect(screen.getByText(/POWERED BY THE IP-SAKTI ORCHESTRATION ENGINE/)).toBeInTheDocument();
    expect(
      screen.getByText(/Not legal, medical, safety, regulatory, or patentability advice/)
    ).toBeInTheDocument();
  });
});
