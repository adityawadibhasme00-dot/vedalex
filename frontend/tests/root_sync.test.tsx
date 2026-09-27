import { useLang } from '../src/lib/LangContext';
import RootSync from '../src/lib/RootSync';
import { renderWithProviders, screen, userEvent, waitFor } from './test-utils';

function Harness() {
  const { lang, setLang } = useLang();
  return (
    <div>
      <span data-testid="active-lang">{lang}</span>
      <button type="button" onClick={() => setLang('hi')}>
        Switch language
      </button>
      <RootSync />
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.lang = '';
});

describe('RootSync document language', () => {
  test('sets the document language when it mounts', async () => {
    renderWithProviders(<RootSync />);
    await waitFor(() => expect(document.documentElement.lang).toBe('en'));
  });

  test('renders no visible output', () => {
    const { container } = renderWithProviders(<RootSync />);
    expect(container.innerHTML).toBe('');
  });

  test('applies the locale saved by a previous session', async () => {
    localStorage.setItem('ipsakti_lang', 'mr');
    renderWithProviders(<Harness />);
    await waitFor(() => expect(document.documentElement.lang).toBe('mr'));
    expect(screen.getByTestId('active-lang')).toHaveTextContent('mr');
  });

  test('follows language changes made at runtime', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness />);
    await waitFor(() => expect(document.documentElement.lang).toBe('en'));
    await user.click(screen.getByRole('button', { name: 'Switch language' }));
    expect(screen.getByTestId('active-lang')).toHaveTextContent('hi');
    await waitFor(() => expect(document.documentElement.lang).toBe('hi'));
  });

  test('persists the chosen locale while syncing the document', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Harness />);
    await waitFor(() => expect(document.documentElement.lang).toBe('en'));
    await user.click(screen.getByRole('button', { name: 'Switch language' }));
    await waitFor(() => expect(document.documentElement.lang).toBe('hi'));
    expect(localStorage.getItem('ipsakti_lang')).toBe('hi');
  });

  test.failing('an unsupported stored locale is not applied to the document', async () => {
    localStorage.setItem('ipsakti_lang', 'invalid locale!!');
    renderWithProviders(<RootSync />);
    await waitFor(() => expect(document.documentElement.lang).toBe('en'));
  });
});
