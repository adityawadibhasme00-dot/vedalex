import type { ComponentProps } from 'react';
import { Sidebar } from '../src/components/layout/Sidebar';
import type { InnolabAgent } from '../src/lib/innolabApi';
import {
  renderWithProviders,
  screen,
  userEvent,
  within,
} from './test-utils';

type SidebarProps = ComponentProps<typeof Sidebar>;

function makeProps(overrides: Partial<SidebarProps> = {}): SidebarProps {
  return {
    activeTab: 'overview',
    onNavigate: jest.fn(),
    collapsed: false,
    onToggleCollapsed: jest.fn(),
    isOnline: true,
    offlineDraftCount: 0,
    userName: 'Dr. Rajesh Vaidya',
    userRole: 'Researcher',
    onLogout: jest.fn(),
    labAgents: [],
    labAgentsLoaded: false,
    onOpenAgent: jest.fn(),
    onHome: jest.fn(),
    lang: 'en',
    mobileOpen: false,
    onCloseMobile: jest.fn(),
    ...overrides,
  };
}

function renderSidebar(overrides: Partial<SidebarProps> = {}) {
  const props = makeProps(overrides);
  renderWithProviders(<Sidebar {...props} />);
  return props;
}

function labAgents(count: number): InnolabAgent[] {
  return Array.from({ length: count }, (_, index) => ({
    slug: `agent-${index + 1}`,
    label: `Lab Agent ${index + 1}`,
    phase: 'ip',
    category_label: 'Intellectual Property',
    description: 'Lab agent description',
    enabled_by_default: true,
    requires_evidence: false,
    live_default: 'off',
  }));
}

function drawer(): HTMLElement {
  const el = document.querySelector('[class*="lg:hidden"]');
  expect(el).not.toBeNull();
  return el as HTMLElement;
}

const MAIN_DESTINATIONS: Array<[string, string]> = [
  ['Innovation Lab', 'innolab'],
  ['AI Assistant', 'copilot'],
  ['Profile & Settings', 'settings'],
];

const KNOWLEDGE_DESTINATIONS: Array<[string, string]> = [
  ['Innovation Passport', 'passport'],
  ['IP & Regulatory Base', 'ipreg'],
  ['Evidence & Compliance', 'evidence'],
  ['Bio-Resource Intelligence', 'biores'],
  ['Product Classifier', 'classify'],
  ['Market Readiness', 'market'],
  ['What-If Simulator', 'whatif'],
  ['Dossier Export', 'dossier'],
];

describe('Sidebar navigation', () => {
  test(
    'routes the main destinations to their own tab id',
    async () => {
      const user = userEvent.setup();
      const props = renderSidebar();
      for (const [label, tab] of MAIN_DESTINATIONS) {
        await user.click(screen.getByRole('button', { name: label }));
        expect(props.onNavigate).toHaveBeenLastCalledWith(tab);
      }
      expect(props.onHome).not.toHaveBeenCalled();
    },
    20000
  );

  test(
    'routes the knowledge destinations to their own tab ids',
    async () => {
      const user = userEvent.setup();
      const props = renderSidebar();
      for (const [label, tab] of KNOWLEDGE_DESTINATIONS) {
        await user.click(screen.getByRole('button', { name: label }));
        expect(props.onNavigate).toHaveBeenLastCalledWith(tab);
      }
      expect(props.onNavigate).toHaveBeenCalledTimes(KNOWLEDGE_DESTINATIONS.length);
    },
    20000
  );

  test('home control returns to the dashboard root', async () => {
    const user = userEvent.setup();
    const props = renderSidebar();
    await user.click(screen.getByRole('button', { name: 'Home' }));
    expect(props.onHome).toHaveBeenCalledTimes(1);
    expect(props.onNavigate).not.toHaveBeenCalled();
  });

  test('sign out control reports the logout request', async () => {
    const user = userEvent.setup();
    const props = renderSidebar();
    await user.click(screen.getByRole('button', { name: 'Sign Out' }));
    expect(props.onLogout).toHaveBeenCalledTimes(1);
  });

  test('help entry links to the support mailbox', () => {
    renderSidebar();
    const link = screen.getByRole('link', { name: /Help & Support/ });
    expect(link).toHaveAttribute('href', 'mailto:support@ipsakti.gov.in');
  });

  test('collapse control reports the requested state change', async () => {
    const user = userEvent.setup();
    const props = renderSidebar();
    await user.click(screen.getByRole('button', { name: 'Collapse sidebar' }));
    expect(props.onToggleCollapsed).toHaveBeenCalledTimes(1);
  });

  test('collapsed sidebar shows the expand control', () => {
    renderSidebar({ collapsed: true });
    expect(
      screen.getByRole('button', { name: 'Expand sidebar' })
    ).toBeInTheDocument();
  });

  test('collapsed sidebar still exposes every destination by name', () => {
    renderSidebar({ collapsed: true });
    for (const [label] of [...MAIN_DESTINATIONS, ...KNOWLEDGE_DESTINATIONS]) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    }
    expect(
      screen.getByRole('button', { name: 'Dashboard' })
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'AI Assistant' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Home' })).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Help & Support' })
    ).toBeInTheDocument();
  });

  test.failing('the active destination is announced with aria-current', () => {
    renderSidebar({ activeTab: 'innolab' });
    const active = screen.getByRole('button', { name: 'Innovation Lab' });
    expect(active).toHaveAttribute('aria-current', 'page');
    const inactive = screen.getByRole('button', { name: 'Dossier Export' });
    expect(inactive).not.toHaveAttribute('aria-current');
  });

  test.failing('the collapsed sign out control keeps an accessible name', () => {
    renderSidebar({ collapsed: true });
    expect(
      screen.getByRole('button', { name: /sign out/i })
    ).toBeInTheDocument();
  });
});

describe('Sidebar lab agents', () => {
  test('offers quick links for the first six loaded agents', async () => {
    const user = userEvent.setup();
    const props = renderSidebar({
      labAgents: labAgents(8),
      labAgentsLoaded: true,
    });
    expect(screen.getByText('Lab Agent 1')).toBeInTheDocument();
    expect(screen.getByText('Lab Agent 6')).toBeInTheDocument();
    expect(screen.queryByText('Lab Agent 7')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Lab Agent 3' }));
    expect(props.onOpenAgent).toHaveBeenCalledWith('agent-3');
    expect(props.onNavigate).not.toHaveBeenCalled();
  });

  test('overflow link routes back to the lab', async () => {
    const user = userEvent.setup();
    const props = renderSidebar({
      labAgents: labAgents(8),
      labAgentsLoaded: true,
    });
    await user.click(
      screen.getByRole('button', { name: '+ 2 more in the lab' })
    );
    expect(props.onNavigate).toHaveBeenCalledWith('innolab');
  });

  test('quick links stay hidden until the agents are loaded', () => {
    renderSidebar({ labAgents: labAgents(3), labAgentsLoaded: false });
    expect(screen.queryByText('Lab Agent 1')).toBeNull();
    expect(screen.queryByRole('button', { name: /more in the lab/ })).toBeNull();
  });

  test('quick links stay hidden when the lab has no agents', () => {
    renderSidebar({ labAgents: [], labAgentsLoaded: true });
    expect(screen.queryByText('Lab Agent 1')).toBeNull();
    expect(screen.queryByRole('button', { name: /more in the lab/ })).toBeNull();
  });

  test('quick links are hidden while the sidebar is collapsed', () => {
    renderSidebar({
      labAgents: labAgents(3),
      labAgentsLoaded: true,
      collapsed: true,
    });
    expect(screen.queryByText('Lab Agent 1')).toBeNull();
  });
});

describe('Sidebar status and identity', () => {
  test('reports the online state', () => {
    renderSidebar({ isOnline: true });
    expect(screen.getByText('Online')).toBeInTheDocument();
  });

  test('reports the offline state with the pending draft count', () => {
    renderSidebar({ isOnline: false, offlineDraftCount: 3 });
    expect(screen.getByText('Offline (3 drafts)')).toBeInTheDocument();
  });

  test('identity falls back to a generic profile', () => {
    renderSidebar({ userName: undefined, userRole: undefined });
    expect(screen.getByText('User')).toBeInTheDocument();
    expect(screen.getByText('Innovator')).toBeInTheDocument();
  });

  test('identity reflects the signed in user', () => {
    renderSidebar({ userName: 'Adv. Priya Sharma', userRole: 'Patent Agent' });
    expect(screen.getByText('Adv. Priya Sharma')).toBeInTheDocument();
    expect(screen.getByText('Patent Agent')).toBeInTheDocument();
  });
});

describe('Sidebar mobile drawer', () => {
  test('stays closed until the shell opens it', () => {
    renderSidebar({ mobileOpen: false });
    expect(screen.queryByText('IP-SAKTI Sahayak')).toBeNull();
  });

  test('opens the full navigation and closes from the backdrop', async () => {
    const user = userEvent.setup();
    const props = renderSidebar({ mobileOpen: true });
    const nav = drawer();
    expect(
      within(nav).getByRole('button', { name: 'Innovation Lab' })
    ).toBeInTheDocument();
    await user.click(nav.firstElementChild as HTMLElement);
    expect(props.onCloseMobile).toHaveBeenCalledTimes(1);
  });

  test('navigates from inside the drawer', async () => {
    const user = userEvent.setup();
    const props = renderSidebar({ mobileOpen: true });
    const nav = drawer();
    await user.click(within(nav).getByRole('button', { name: 'Dossier Export' }));
    expect(props.onNavigate).toHaveBeenCalledWith('dossier');
  });

  test('closes from the panel close control', async () => {
    const user = userEvent.setup();
    const props = renderSidebar({ mobileOpen: true });
    const header = screen.getByText('IP-SAKTI Sahayak').parentElement as HTMLElement;
    await user.click(within(header).getByRole('button'));
    expect(props.onCloseMobile).toHaveBeenCalledTimes(1);
  });

  test.failing('the drawer close control has an accessible name', () => {
    renderSidebar({ mobileOpen: true });
    expect(
      within(drawer()).getByRole('button', { name: /close/i })
    ).toBeInTheDocument();
  });
});
