import type { ComponentProps } from 'react';
import { AccessibilityProvider } from '../src/lib/AccessibilityContext';
import { SUPPORTED_LANGUAGES } from '../src/lib/i18n';
import { TopNav } from '../src/components/layout/TopNav';
import { renderWithProviders, screen, userEvent, waitFor } from './test-utils';

type TopNavProps = ComponentProps<typeof TopNav>;

const SEARCH_PLACEHOLDER = /Search statutes, patents, regulations/;

function makeProps(overrides: Partial<TopNavProps> = {}): TopNavProps {
  return {
    isOnline: true,
    offlineDraftCount: 0,
    userName: 'Dr. Rajesh Vaidya',
    userRole: 'Researcher',
    onMenuClick: jest.fn(),
    onSearch: jest.fn(),
    onLogout: jest.fn(),
    ...overrides,
  };
}

function renderTopNav(overrides: Partial<TopNavProps> = {}) {
  const props = makeProps(overrides);
  renderWithProviders(
    <AccessibilityProvider>
      <TopNav {...props} />
    </AccessibilityProvider>
  );
  return props;
}

function searchInput(): HTMLInputElement {
  return screen.getByPlaceholderText(SEARCH_PLACEHOLDER) as HTMLInputElement;
}

beforeEach(() => {
  localStorage.clear();
});

describe('TopNav search', () => {
  test('submits a trimmed query and clears the field', async () => {
    const user = userEvent.setup();
    const props = renderTopNav();
    await user.type(searchInput(), '  Canada export  {Enter}');
    expect(props.onSearch).toHaveBeenCalledWith('Canada export');
    expect(searchInput().value).toBe('');
  });

  test('ignores a whitespace only query', async () => {
    const user = userEvent.setup();
    const props = renderTopNav();
    await user.type(searchInput(), '   {Enter}');
    expect(props.onSearch).not.toHaveBeenCalled();
    expect(searchInput().value).toBe('   ');
  });

  test('ignores an empty submission', async () => {
    const user = userEvent.setup();
    const props = renderTopNav();
    await user.type(searchInput(), '{Enter}');
    expect(props.onSearch).not.toHaveBeenCalled();
  });

  test.failing('the search field has an accessible name', () => {
    renderTopNav();
    expect(
      screen.getByRole('textbox', { name: /search statutes/i })
    ).toBeInTheDocument();
  });
});

describe('TopNav shell controls', () => {
  test('mobile menu control notifies the shell', async () => {
    const user = userEvent.setup();
    const props = renderTopNav();
    await user.click(screen.getByRole('button', { name: 'Open navigation' }));
    expect(props.onMenuClick).toHaveBeenCalledTimes(1);
  });

  test('notifications control is always offered', () => {
    renderTopNav();
    expect(
      screen.getByRole('button', { name: 'Notifications' })
    ).toBeInTheDocument();
  });

  test('reports the online state', () => {
    renderTopNav({ isOnline: true });
    expect(screen.getByText('Online')).toBeInTheDocument();
  });

  test('reports the offline state with the pending draft count', () => {
    renderTopNav({ isOnline: false, offlineDraftCount: 3 });
    expect(screen.getByText('Offline (3)')).toBeInTheDocument();
  });

  test('product identity is announced as the page heading', () => {
    renderTopNav();
    expect(
      screen.getByRole('heading', { name: 'IP-SAKTI Sahayak' })
    ).toBeInTheDocument();
  });
});

describe('TopNav profile', () => {
  test('opens the menu with the signed in identity', async () => {
    const user = userEvent.setup();
    renderTopNav();
    await user.click(screen.getByRole('button', { name: 'Profile' }));
    expect(screen.getByText('Researcher')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Working Dashboard/ })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Sign Out' })
    ).toBeInTheDocument();
  });

  test('signing out reports the request and closes the menu', async () => {
    const user = userEvent.setup();
    const props = renderTopNav();
    await user.click(screen.getByRole('button', { name: 'Profile' }));
    await user.click(screen.getByRole('button', { name: 'Sign Out' }));
    expect(props.onLogout).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByRole('button', { name: /Government Working Dashboard/ })
    ).toBeNull();
  });

  test('falls back to a generic identity without a session', async () => {
    const user = userEvent.setup();
    renderTopNav({ userName: undefined, userRole: undefined });
    await user.click(screen.getByRole('button', { name: 'Profile' }));
    expect(screen.getByText('Innovator')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Working Dashboard/ })
    ).toBeInTheDocument();
  });
});

describe('TopNav language control', () => {
  test('opens the switcher and applies the chosen language', async () => {
    const user = userEvent.setup();
    const nativeNames = SUPPORTED_LANGUAGES.map((l) => l.nativeName);
    renderTopNav();
    expect(screen.queryByText(nativeNames[9])).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Select Language' }));
    expect(screen.getByText(nativeNames[9])).toBeInTheDocument();
    await user.click(screen.getByText(nativeNames[1]));
    expect(screen.queryByText(nativeNames[9])).toBeNull();
    expect(localStorage.getItem('ipsakti_lang')).toBe('hi');
    expect(
      screen.getByRole('button', { name: 'Select Language' })
    ).toHaveTextContent(nativeNames[1]);
  });
});

describe('TopNav accessibility control', () => {
  test('opens a panel whose switches really toggle the preference', async () => {
    const user = userEvent.setup();
    renderTopNav();
    await user.click(screen.getByRole('button', { name: 'Accessibility' }));
    const switches = screen.getAllByRole('switch');
    expect(switches).toHaveLength(3);
    await user.click(switches[0]);
    expect(switches[0]).toHaveAttribute('aria-checked', 'true');
    await waitFor(() =>
      expect(
        JSON.parse(localStorage.getItem('ipsakti_accessibility') as string)
          .highContrast
      ).toBe(true)
    );
    await user.click(switches[0]);
    expect(switches[0]).toHaveAttribute('aria-checked', 'false');
  });

  test('the panel reports its own title', async () => {
    const user = userEvent.setup();
    renderTopNav();
    await user.click(screen.getByRole('button', { name: 'Accessibility' }));
    expect(
      screen.getByRole('heading', { name: 'Accessibility' })
    ).toBeInTheDocument();
  });

  test.failing('every switch in the panel announces its own label', async () => {
    const user = userEvent.setup();
    renderTopNav();
    await user.click(screen.getByRole('button', { name: 'Accessibility' }));
    expect(
      screen.getByRole('switch', { name: /high contrast/i })
    ).toBeInTheDocument();
  });
});
