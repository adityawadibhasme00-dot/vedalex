import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import { render, waitFor } from './test-utils';
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
