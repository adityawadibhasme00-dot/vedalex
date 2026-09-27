import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import {
  askCopilot,
  createPassportFromIntake,
  getClarifications,
  getPassport,
  getRegulatoryDiffs,
  getSuggestedQuestions,
  getWhiteSpaceAnalysis,
  loginUser,
  ragSearch,
} from '../src/lib/api';

const BASE = 'http://localhost/api/v1';

afterEach(() => {
  localStorage.clear();
});

describe('api.ts request contract', () => {
  test('getPassport issues GET /passport/{id}', async () => {
    let capturedPath = '';
    server.use(
      http.get(`${BASE}/passport/:id`, ({ params }) => {
        capturedPath = `/passport/${params.id}`;
        return HttpResponse.json({ id: params.id, title: 'P' });
      })
    );
    const result = await getPassport('abc-123');
    expect(capturedPath).toBe('/passport/abc-123');
    expect(result).toEqual({ id: 'abc-123', title: 'P' });
  });

  test('createPassportFromIntake posts raw_text and user_lang', async () => {
    let body: any = null;
    server.use(
      http.post(`${BASE}/passport/create`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ id: 'new-1', title: 'T' });
      })
    );
    await createPassportFromIntake('raw herbs text', 'hi', 'Case title');
    expect(body).toMatchObject({
      raw_text: 'raw herbs text',
      user_lang: 'hi',
      case_title: 'Case title',
    });
  });

  test('createPassportFromIntake throws generic error on failure', async () => {
    server.use(
      http.post(`${BASE}/passport/create`, () =>
        HttpResponse.json({ detail: 'boom' }, { status: 500 })
      )
    );
    await expect(createPassportFromIntake('x')).rejects.toThrow(
      'Failed to create passport'
    );
  });

  test('loginUser posts credentials and returns token payload', async () => {
    let body: any = null;
    server.use(
      http.post(`${BASE}/auth/login`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ access_token: 'tok', token_type: 'bearer' });
      })
    );
    const res = await loginUser('a@b.test', 'secret');
    expect(body).toEqual({ email: 'a@b.test', password: 'secret' });
    expect(res.access_token).toBe('tok');
  });

  test('loginUser surfaces backend detail message', async () => {
    server.use(
      http.post(`${BASE}/auth/login`, () =>
        HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
      )
    );
    await expect(loginUser('a@b.test', 'wrong')).rejects.toThrow(
      'Invalid credentials'
    );
  });

  test('askCopilot posts question and passport_id', async () => {
    let body: any = null;
    server.use(
      http.post(`${BASE}/chat/query`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ answer: 'ok' });
      })
    );
    const res = await askCopilot('What is novelty?', 'pid-1');
    expect(body).toMatchObject({ question: 'What is novelty?', passport_id: 'pid-1' });
    expect(res).toEqual({ answer: 'ok' });
  });

  test('getClarifications degrades to empty list on error', async () => {
    server.use(
      http.get(`${BASE}/passport/:id/clarifications`, () =>
        HttpResponse.json({ detail: 'nope' }, { status: 500 })
      )
    );
    await expect(getClarifications('p1')).resolves.toEqual([]);
  });

  test('getRegulatoryDiffs degrades to empty list on error', async () => {
    server.use(
      http.get(`${BASE}/regulatory-diff/updates`, () =>
        HttpResponse.text('err', { status: 500 })
      )
    );
    await expect(getRegulatoryDiffs()).resolves.toEqual([]);
  });

  test('getSuggestedQuestions degrades to empty questions on error', async () => {
    server.use(
      http.get(`${BASE}/chat/suggested-questions`, () =>
        HttpResponse.text('err', { status: 500 })
      )
    );
    await expect(getSuggestedQuestions()).resolves.toEqual({ questions: [] });
  });

  test('ragSearch surfaces backend detail message on failure', async () => {
    server.use(
      http.post(`${BASE}/rag/search`, () =>
        HttpResponse.json({ detail: 'invalid rag_type' }, { status: 422 })
      )
    );
    await expect(ragSearch('ashwagandha')).rejects.toThrow('invalid rag_type');
  });

  test('getWhiteSpaceAnalysis surfaces backend detail on failure', async () => {
    server.use(
      http.get(`${BASE}/whitespace/:id`, () =>
        HttpResponse.json({ detail: 'passport not found' }, { status: 404 })
      )
    );
    await expect(getWhiteSpaceAnalysis('missing')).rejects.toThrow(
      'passport not found'
    );
  });
});

describe('api.ts authentication contract', () => {
  test.failing(
    'authenticated request carries stored bearer token',
    async () => {
      let authHeader: string | null = 'unset';
      server.use(
        http.get(`${BASE}/passport/:id`, ({ request }) => {
          authHeader = request.headers.get('authorization');
          return HttpResponse.json({ id: 'p' });
        })
      );
      localStorage.setItem('ipsakti_token', 'stored-token');
      await getPassport('p');
      expect(authHeader).toBe('Bearer stored-token');
    }
  );

  test.failing(
    'login response token is reusable on subsequent requests',
    async () => {
      const seen: Array<string | null> = [];
      server.use(
        http.post(`${BASE}/auth/login`, () =>
          HttpResponse.json({ access_token: 'fresh-token', token_type: 'bearer' })
        ),
        http.get(`${BASE}/passport/:id`, ({ request }) => {
          seen.push(request.headers.get('authorization'));
          return HttpResponse.json({ id: 'p' });
        })
      );
      const res = await loginUser('a@b.test', 'pw');
      localStorage.setItem('ipsakti_token', res.access_token);
      await getPassport('p');
      expect(seen[0]).toBe('Bearer fresh-token');
    }
  );
});
