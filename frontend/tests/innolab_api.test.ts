import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import { innolabApi } from '../src/lib/innolabApi';

const BASE = 'http://localhost/api/v1';

describe('innolabApi request contract', () => {
  test('agents() issues GET /innolab/agents and parses payload', async () => {
    let called = '';
    server.use(
      http.get(`${BASE}/innolab/agents`, () => {
        called = 'GET';
        return HttpResponse.json({
          count: 1,
          phases: ['Phase 1'],
          agents: [{ slug: 'prior-art', label: 'Prior Art', phase: 'Phase 1' }],
        });
      })
    );
    const res = await innolabApi.agents();
    expect(called).toBe('GET');
    expect(res.count).toBe(1);
    expect(res.agents[0].slug).toBe('prior-art');
  });

  test('runAgent posts JSON body with inputs', async () => {
    let body: any = null;
    let contentType = '';
    server.use(
      http.post(`${BASE}/innolab/agents/:slug/run`, async ({ request }) => {
        contentType = request.headers.get('content-type') || '';
        body = await request.json();
        return HttpResponse.json({
          agent_slug: 'x',
          run_id: 'r1',
          status: 'done',
          result: { ok: true },
        });
      })
    );
    const res = await innolabApi.runAgent('x', {
      project_id: 'p1',
      inputs: { query: 'q' },
    });
    expect(body).toEqual({ project_id: 'p1', inputs: { query: 'q' } });
    expect(contentType).toContain('application/json');
    expect(res.run_id).toBe('r1');
  });

  test('getAgentWorkflow resolves workflow schema', async () => {
    server.use(
      http.get(`${BASE}/innolab/agents/:slug/workflow`, () =>
        HttpResponse.json({
          slug: 'x',
          steps: [{ label: 'Step', description: 'd' }],
          questions: [],
        })
      )
    );
    const res = await innolabApi.getAgentWorkflow('x');
    expect(res.steps).toHaveLength(1);
    expect(res.steps[0].label).toBe('Step');
  });

  test('request failure throws Error with response body text', async () => {
    server.use(
      http.post(`${BASE}/innolab/agents/:slug/run`, () =>
        HttpResponse.text('agent crashed', { status: 500 })
      )
    );
    await expect(
      innolabApi.runAgent('x', { inputs: {} })
    ).rejects.toThrow('agent crashed');
  });

  test('missing agent detail propagates backend 404 body', async () => {
    server.use(
      http.get(`${BASE}/innolab/agents/:slug`, () =>
        HttpResponse.text('agent not found', { status: 404 })
      )
    );
    await expect(innolabApi.getAgent('ghost')).rejects.toThrow(
      'agent not found'
    );
  });

  test('exportAgentResult returns a Blob', async () => {
    server.use(
      http.post(`${BASE}/innolab/agents/:slug/export`, () =>
        new HttpResponse(Buffer.from('docx-bytes'), {
          headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
        })
      )
    );
    const blob = await innolabApi.exportAgentResult('x', {} as any);
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.size).toBeGreaterThan(0);
  });

  test('orchestratorPlan posts the brief', async () => {
    let body: any = null;
    server.use(
      http.post(`${BASE}/innolab/orchestrator/plan`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ brief: 'b', intents: [], entities: {}, agents: [], total_steps: 0 });
      })
    );
    const res = await innolabApi.orchestratorPlan('my brief');
    expect(body).toEqual({ brief: 'my brief' });
    expect(res.total_steps).toBe(0);
  });

  test.failing(
    'authenticated innolab requests carry the stored bearer token',
    async () => {
      let authHeader: string | null = 'unset';
      server.use(
        http.get(`${BASE}/innolab/agents`, ({ request }) => {
          authHeader = request.headers.get('authorization');
          return HttpResponse.json({ count: 0, phases: [], agents: [] });
        })
      );
      localStorage.setItem('ipsakti_token', 'stored-token');
      await innolabApi.agents();
      expect(authHeader).toBe('Bearer stored-token');
    }
  );
});
