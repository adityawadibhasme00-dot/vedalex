import type { ComponentProps, ReactNode } from 'react';
import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import {
  act,
  renderWithProviders,
  screen,
  userEvent,
  waitFor,
  within,
} from './test-utils';
import { DashboardLayout } from '../src/components/layout/DashboardLayout';
import { useAuth } from '../src/lib/AuthContext';
import type { InnolabAgent } from '../src/lib/innolabApi';

const mockPush = jest.fn();
const mockPathname = jest.fn(() => '/dashboard');
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, pathname: mockPathname() }),
  usePathname: () => mockPathname(),
}));

const BASE = 'http://localhost/api/v1';

const labAgent: InnolabAgent = {
  slug: 'prior-art',
  label: 'Prior Art Scout',
  phase: 'ip',
  category_label: 'Intellectual Property',
  description: 'Searches patent corpora',
  enabled_by_default: true,
  requires_evidence: true,
  live_default: 'off',
};

let agentCalls = 0;

function agentsHandler(agents: InnolabAgent[]) {
  return http.get(`${BASE}/innolab/agents`, () => {
    agentCalls += 1;
    return HttpResponse.json({
      count: agents.length,
      phases: ['ip'],
      agents,
    });
  });
}

let authCtx: any = null;

function AuthProbe() {
  authCtx = useAuth();
  return null;
}

type LayoutProps = ComponentProps<typeof DashboardLayout>;

function makeProps(overrides: Partial<LayoutProps> = {}): LayoutProps {
  const children: ReactNode = (
    <>
      <div>Passport workspace</div>
      <AuthProbe />
    </>
  );
  return {
    activeTab: 'overview',
    onNavigate: jest.fn(),
    onSearch: jest.fn(),
    labAgents: [],
    labAgentsLoaded: true,
    children,
    ...overrides,
  };
}

function renderLayout(overrides: Partial<LayoutProps> = {}) {
  const props = makeProps(overrides);
  renderWithProviders(<DashboardLayout {...props} />);
  return props;
}

function topNav(): HTMLElement {
  const landmarks = screen.getAllByRole('navigation');
  expect(landmarks.length).toBeGreaterThan(0);
  return landmarks[0];
}

function drawer(): HTMLElement | null {
  return document.querySelector('[class*="z-[60]"]');
}

beforeEach(() => {
  mockPush.mockClear();
  mockPathname.mockClear();
  localStorage.clear();
  authCtx = null;
  agentCalls = 0;
  server.use(agentsHandler([]));
});

describe('DashboardLayout shell', () => {
  test('renders the chrome around the routed content', () => {
    renderLayout();
    expect(screen.getByText('Passport workspace')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Open navigation' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Collapse sidebar' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Profile' })
    ).toBeInTheDocument();
  });

  test('sidebar collapse toggles the shell state', async () => {
    const user = userEvent.setup();
    renderLayout();
    await user.click(screen.getByRole('button', { name: 'Collapse sidebar' }));
    expect(
      screen.getByRole('button', { name: 'Expand sidebar' })
    ).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Expand sidebar' }));
    expect(
      screen.getByRole('button', { name: 'Collapse sidebar' })
    ).toBeInTheDocument();
  });

  test('mobile drawer opens from the top nav and closes on the backdrop', async () => {
    const user = userEvent.setup();
    renderLayout();
    expect(drawer()).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Open navigation' }));
    const nav = drawer() as HTMLElement;
    expect(nav).not.toBeNull();
    expect(
      within(nav).getByRole('button', { name: 'Innovation Lab' })
    ).toBeInTheDocument();
    await user.click(nav.firstElementChild as HTMLElement);
    expect(drawer()).toBeNull();
  });
});

describe('DashboardLayout data and status', () => {
  test('loads lab agents into the sidebar when they are not supplied', async () => {
    server.use(agentsHandler([labAgent]));
    renderLayout({ labAgents: undefined, labAgentsLoaded: undefined });
    expect(await screen.findByText('Prior Art Scout')).toBeInTheDocument();
    await waitFor(() => expect(agentCalls).toBe(1));
  });

  test('skips the agents request when they are supplied', async () => {
    renderLayout({ labAgents: [labAgent], labAgentsLoaded: true });
    expect(await screen.findByText('Prior Art Scout')).toBeInTheDocument();
    expect(agentCalls).toBe(0);
  });

  test('browser offline and online events drive the status indicator', async () => {
    renderLayout();
    act(() => {
      window.dispatchEvent(new Event('offline'));
    });
    expect(within(topNav()).getByText('Offline (0)')).toBeInTheDocument();
    expect(screen.getByText('Offline (0 drafts)')).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(new Event('online'));
    });
    expect(within(topNav()).getByText('Online')).toBeInTheDocument();
  });

  test('an explicit online prop overrides browser events', () => {
    renderLayout({ isOnline: true });
    act(() => {
      window.dispatchEvent(new Event('offline'));
    });
    expect(within(topNav()).getByText('Online')).toBeInTheDocument();
  });
});

describe('DashboardLayout identity', () => {
  test('shows a generic identity without a saved session', async () => {
    renderLayout();
    expect(await screen.findByText('Innovator')).toBeInTheDocument();
    expect(authCtx.user).toBeNull();
  });

  test('shows the saved session identity', async () => {
    localStorage.setItem(
      'ipsakti_user',
      JSON.stringify({
        name: 'Saved User',
        email: 'saved@example.test',
        role: 'Researcher',
      })
    );
    renderLayout();
    expect((await screen.findAllByText('Saved User')).length).toBeGreaterThan(0);
    expect(screen.getByText('Researcher')).toBeInTheDocument();
    expect(authCtx.user.name).toBe('Saved User');
  });

  test('signing out clears the session and routes to login', async () => {
    localStorage.setItem(
      'ipsakti_user',
      JSON.stringify({
        name: 'Saved User',
        email: 'saved@example.test',
        role: 'Researcher',
      })
    );
    const user = userEvent.setup();
    renderLayout();
    expect((await screen.findAllByText('Saved User')).length).toBeGreaterThan(0);
    await user.click(screen.getByRole('button', { name: 'Profile' }));
    await user.click(within(topNav()).getByRole('button', { name: 'Sign Out' }));
    expect(mockPush).toHaveBeenCalledWith('/login');
    await waitFor(() => expect(authCtx.user).toBeNull());
    expect(localStorage.getItem('ipsakti_user')).toBeNull();
    expect(localStorage.getItem('ipsakti_token')).toBeNull();
  });
});

describe('DashboardLayout routing', () => {
  test('search delegates to the provided handler', async () => {
    const user = userEvent.setup();
    const props = renderLayout();
    await user.type(
      screen.getByPlaceholderText(/Search statutes, patents, regulations/),
      'Canada export{Enter}'
    );
    expect(props.onSearch).toHaveBeenCalledWith('Canada export');
    expect(mockPush).not.toHaveBeenCalledWith('/dashboard#copilot');
  });

  test('search without a handler routes to the copilot channel', async () => {
    const user = userEvent.setup();
    const seen: string[] = [];
    const listener = (event: Event) => {
      seen.push((event as CustomEvent).detail);
    };
    window.addEventListener('ipsakti:copilot-question', listener);
    try {
      renderLayout({ onSearch: undefined });
      await user.type(
        screen.getByPlaceholderText(/Search statutes, patents, regulations/),
        'Canada export{Enter}'
      );
      expect(mockPush).toHaveBeenCalledWith('/dashboard#copilot');
      await waitFor(() => expect(seen).toEqual(['Canada export']));
    } finally {
      window.removeEventListener('ipsakti:copilot-question', listener);
    }
  });

  test('a lab agent quick link routes to its workspace', async () => {
    const user = userEvent.setup();
    renderLayout({ labAgents: [labAgent], labAgentsLoaded: true });
    await user.click(screen.getByRole('button', { name: 'Prior Art Scout' }));
    expect(mockPush).toHaveBeenCalledWith('/innovation-lab/agents/prior-art');
  });

  test('the home control routes to the application root', async () => {
    const user = userEvent.setup();
    renderLayout();
    await user.click(screen.getByRole('button', { name: 'Home' }));
    expect(mockPush).toHaveBeenCalledWith('/');
  });

  test.failing('the routed content is exposed as a main landmark', () => {
    renderLayout();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  test.failing('each navigation landmark carries its own accessible name', () => {
    renderLayout();
    const landmarks = screen.getAllByRole('navigation');
    expect(landmarks.length).toBeGreaterThan(1);
    for (const landmark of landmarks) {
      expect(landmark).toHaveAccessibleName();
    }
  });
});
