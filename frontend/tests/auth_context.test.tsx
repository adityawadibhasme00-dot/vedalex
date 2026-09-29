import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import { act, render, waitFor } from './test-utils';
import { AuthProvider, useAuth } from '../src/lib/AuthContext';

const BASE = 'http://localhost/api/v1';

let ctx: any;

function Capture() {
  ctx = useAuth();
  return null;
}

async function renderAuth() {
  const utils = render(
    <AuthProvider>
      <Capture />
    </AuthProvider>
  );
  await waitFor(() => expect(ctx.isLoading).toBe(false));
  return utils;
}

beforeEach(() => {
  localStorage.clear();
  ctx = undefined;
});

describe('AuthContext login', () => {
  test('successful backend login stores user and token', async () => {
    server.use(
      http.post(`${BASE}/auth/login`, () =>
        HttpResponse.json({
          access_token: 'tok-1',
          token_type: 'bearer',
          user: { id: 'u1', name: 'Ada', email: 'ada@example.test', role: 'Researcher' },
        })
      )
    );
    await renderAuth();
    const result = await ctx.login('ada@example.test', 'pw');
    expect(result.success).toBe(true);
    await waitFor(() => expect(ctx.apiToken).toBe('tok-1'));
    expect(ctx.user.email).toBe('ada@example.test');
    expect(localStorage.getItem('ipsakti_token')).toBe('tok-1');
    expect(JSON.parse(localStorage.getItem('ipsakti_user')!).email).toBe(
      'ada@example.test'
    );
    expect(ctx.isLoading).toBe(false);
  });

  test('failed login returns error from backend detail', async () => {
    server.use(
      http.post(`${BASE}/auth/login`, () =>
        HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
      )
    );
    await renderAuth();
    const result = await ctx.login('nobody@example.test', 'bad');
    expect(result.success).toBe(false);
    expect(result.error).toBe('Invalid credentials');
    expect(ctx.user).toBeNull();
    expect(localStorage.getItem('ipsakti_token')).toBeNull();
  });

  test.failing(
    'backend outage must not accept hardcoded demo credentials',
    async () => {
      server.use(
        http.post(`${BASE}/auth/login`, () =>
          HttpResponse.text('down', { status: 500 })
        )
      );
      await renderAuth();
      const result = await ctx.login('founder@ayurstartup.in', 'demo123');
      expect(result.success).toBe(false);
    }
  );

  test('demo account fallback does not persist an api token', async () => {
    server.use(
      http.post(`${BASE}/auth/login`, () =>
        HttpResponse.text('down', { status: 500 })
      )
    );
    await renderAuth();
    const result = await ctx.login('founder@ayurstartup.in', 'demo123');
    expect(result.success).toBe(true);
    expect(localStorage.getItem('ipsakti_token')).toBeNull();
  });
});

describe('AuthContext session lifecycle', () => {
  test('restores saved session from localStorage on mount', async () => {
    server.use(
      http.get(`${BASE}/auth/profile`, () =>
        HttpResponse.text('unavailable', { status: 503 })
      )
    );
    localStorage.setItem(
      'ipsakti_user',
      JSON.stringify({ name: 'Saved', email: 'saved@example.test', role: 'Researcher' })
    );
    localStorage.setItem('ipsakti_token', 'saved-token');
    await renderAuth();
    expect(ctx.user.email).toBe('saved@example.test');
    expect(ctx.apiToken).toBe('saved-token');
    expect(ctx.isLoading).toBe(false);
  });

  test('logout clears state and localStorage', async () => {
    server.use(
      http.get(`${BASE}/auth/profile`, () =>
        HttpResponse.text('unavailable', { status: 503 })
      )
    );
    localStorage.setItem(
      'ipsakti_user',
      JSON.stringify({ name: 'Saved', email: 'saved@example.test', role: 'Researcher' })
    );
    localStorage.setItem('ipsakti_token', 'saved-token');
    await renderAuth();
    ctx.logout();
    await waitFor(() => expect(ctx.user).toBeNull());
    expect(ctx.apiToken).toBeNull();
    expect(localStorage.getItem('ipsakti_user')).toBeNull();
    expect(localStorage.getItem('ipsakti_token')).toBeNull();
  });

  test('signup stores returned user and token', async () => {
    server.use(
      http.post(`${BASE}/auth/signup`, () =>
        HttpResponse.json({
          access_token: 'signup-tok',
          token_type: 'bearer',
          user: { name: 'New', email: 'new@example.test', role: 'Researcher' },
        })
      )
    );
    await renderAuth();
    const result = await ctx.signup('New', 'new@example.test', 'pw12345');
    expect(result.success).toBe(true);
    await waitFor(() => expect(ctx.apiToken).toBe('signup-tok'));
    expect(localStorage.getItem('ipsakti_token')).toBe('signup-tok');
  });

  test('corrupt saved user does not crash the provider', async () => {
    localStorage.setItem('ipsakti_user', '{not-json');
    await renderAuth();
    expect(ctx.user).toBeNull();
    expect(ctx.isLoading).toBe(false);
  });
});

describe('AuthContext profile revalidation', () => {
  test('replaces the stale cached name with the server profile on mount', async () => {
    server.use(
      http.get(`${BASE}/auth/profile`, () =>
        HttpResponse.json({
          id: 'u9',
          name: 'Dr. Ananya Desai',
          email: 'ananya@example.test',
          role: 'Patent Agent',
          institution: 'NIPER',
          is_active: true,
          created_at: '2024-01-01 00:00:00',
        })
      )
    );
    localStorage.setItem(
      'ipsakti_user',
      JSON.stringify({ name: 'Stale Name', email: 'old@example.test', role: 'Researcher' })
    );
    localStorage.setItem('ipsakti_token', 'tok-9');
    await renderAuth();

    await waitFor(() => expect(ctx.user.name).toBe('Dr. Ananya Desai'));
    expect(ctx.user.email).toBe('ananya@example.test');
    expect(ctx.user.role).toBe('Patent Agent');
    expect(ctx.user.institution).toBe('NIPER');
    expect(JSON.parse(localStorage.getItem('ipsakti_user')!).name).toBe('Dr. Ananya Desai');
  });

  test('sends the stored bearer token when revalidating', async () => {
    let seenAuth: string | null = null;
    server.use(
      http.get(`${BASE}/auth/profile`, ({ request }) => {
        seenAuth = request.headers.get('Authorization');
        return HttpResponse.json({ name: 'Ada', email: 'ada@example.test', role: 'Researcher' });
      })
    );
    localStorage.setItem(
      'ipsakti_user',
      JSON.stringify({ name: 'Ada', email: 'ada@example.test', role: 'Researcher' })
    );
    localStorage.setItem('ipsakti_token', 'tok-auth');
    await renderAuth();

    await waitFor(() => expect(seenAuth).toBe('Bearer tok-auth'));
  });

  test('keeps the cached profile when the profile request is unauthorised', async () => {
    server.use(
      http.get(`${BASE}/auth/profile`, () =>
        HttpResponse.json({ detail: 'Could not validate credentials' }, { status: 401 })
      )
    );
    localStorage.setItem(
      'ipsakti_user',
      JSON.stringify({ name: 'Cached', email: 'cached@example.test', role: 'Researcher' })
    );
    localStorage.setItem('ipsakti_token', 'expired-token');
    await renderAuth();

    await waitFor(() => expect(ctx.isLoading).toBe(false));
    expect(ctx.user.name).toBe('Cached');
    expect(ctx.apiToken).toBe('expired-token');
  });

  test('falls back to cached fields the server response omits', async () => {
    server.use(
      http.get(`${BASE}/auth/profile`, () =>
        HttpResponse.json({ name: 'Server Name' })
      )
    );
    localStorage.setItem(
      'ipsakti_user',
      JSON.stringify({ name: 'Cached', email: 'cached@example.test', role: 'Researcher' })
    );
    localStorage.setItem('ipsakti_token', 'tok-partial');
    await renderAuth();

    await waitFor(() => expect(ctx.user.name).toBe('Server Name'));
    expect(ctx.user.email).toBe('cached@example.test');
    expect(ctx.user.role).toBe('Researcher');
  });

  test('does not restore the profile when logout wins the race', async () => {
    server.use(
      http.get(`${BASE}/auth/profile`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 20));
        return HttpResponse.json({
          name: 'Late Name',
          email: 'late@example.test',
          role: 'Researcher',
        });
      })
    );
    localStorage.setItem(
      'ipsakti_user',
      JSON.stringify({ name: 'Cached', email: 'cached@example.test', role: 'Researcher' })
    );
    localStorage.setItem('ipsakti_token', 'tok-race');
    await renderAuth();
    act(() => ctx.logout());

    await new Promise((resolve) => setTimeout(resolve, 60));
    expect(ctx.user).toBeNull();
    expect(localStorage.getItem('ipsakti_user')).toBeNull();
    expect(localStorage.getItem('ipsakti_token')).toBeNull();
  });
});
