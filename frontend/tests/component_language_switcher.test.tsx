import { useState } from 'react';
import { renderWithProviders, screen, userEvent } from './test-utils';
import LanguageSwitcher from '../src/components/LanguageSwitcher';
import { SUPPORTED_LANGUAGES } from '../src/lib/i18n';
import { useLang } from '../src/lib/LangContext';

function Harness({ onClose }: { onClose: () => void }) {
  const { lang } = useLang();
  const [open, setOpen] = useState(true);
  return (
    <>
      <span data-testid="current-lang">{lang}</span>
      <LanguageSwitcher isOpen={open} onClose={() => { setOpen(false); onClose(); }} />
    </>
  );
}

beforeEach(() => {
  localStorage.clear();
});

describe('LanguageSwitcher', () => {
  test('renders nothing when closed', () => {
    const { container } = renderWithProviders(
      <LanguageSwitcher isOpen={false} onClose={() => {}} />
    );
    expect(container.innerHTML).toBe('');
  });

  test('lists every supported language when open', () => {
    renderWithProviders(<LanguageSwitcher isOpen onClose={() => {}} />);
    expect(screen.getByText('IP-SAKTI')).toBeInTheDocument();
    for (const l of SUPPORTED_LANGUAGES) {
      expect(screen.getByText(l.nativeName)).toBeInTheDocument();
      expect(screen.getByText(l.scriptLabel)).toBeInTheDocument();
    }
  });

  test('selecting a language persists it and closes the modal', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    renderWithProviders(<LanguageSwitcher isOpen onClose={onClose} />);
    await user.click(screen.getByText(SUPPORTED_LANGUAGES[1].nativeName));
    expect(localStorage.getItem('ipsakti_lang')).toBe('hi');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('saved locale is restored into the active language', () => {
    localStorage.setItem('ipsakti_lang', 'mr');
    renderWithProviders(<Harness onClose={() => {}} />);
    expect(screen.getByTestId('current-lang')).toHaveTextContent('mr');
  });

  test('backdrop click closes the modal', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    const { container } = renderWithProviders(
      <LanguageSwitcher isOpen onClose={onClose} />
    );
    const backdrop = container.querySelector('.absolute.inset-0') as HTMLElement;
    expect(backdrop).not.toBeNull();
    await user.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('close button closes the modal', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    renderWithProviders(<LanguageSwitcher isOpen onClose={onClose} />);
    const buttons = screen.getAllByRole('button');
    await user.click(buttons[buttons.length - 1]);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
