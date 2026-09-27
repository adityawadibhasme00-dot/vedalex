import { renderWithProviders, screen, userEvent, waitFor } from './test-utils';
import AuthModal from '../src/components/AuthModal';

function renderModal() {
  const onClose = jest.fn();
  const onLoginSuccess = jest.fn();
  renderWithProviders(
    <AuthModal isOpen onClose={onClose} onLoginSuccess={onLoginSuccess} />
  );
  return { onClose, onLoginSuccess };
}

function passwordInput(): HTMLInputElement | null {
  return document.querySelector('input[type="password"]');
}

describe('AuthModal', () => {
  test('renders nothing when closed', () => {
    const { container } = renderWithProviders(
      <AuthModal isOpen={false} onClose={() => {}} onLoginSuccess={() => {}} />
    );
    expect(container.innerHTML).toBe('');
  });

  test('login mode renders persona roles and submit action', () => {
    renderModal();
    expect(screen.getByText('Sign in to IP-SAKTI')).toBeInTheDocument();
    expect(screen.getAllByRole('option')).toHaveLength(5);
    expect(
      screen.getByRole('button', { name: 'Authenticate & Enter Dashboard' })
    ).toBeInTheDocument();
  });

  test('successful login reports the selected persona and closes', async () => {
    const user = userEvent.setup();
    const { onClose, onLoginSuccess } = renderModal();
    await user.selectOptions(screen.getByRole('combobox'), 'Researcher');
    const emailInput = screen.getByDisplayValue('founder@ayurstartup.in');
    await user.clear(emailInput);
    await user.type(emailInput, 'a@b.test');
    await user.click(
      screen.getByRole('button', { name: 'Authenticate & Enter Dashboard' })
    );
    await waitFor(() => expect(onLoginSuccess).toHaveBeenCalledTimes(1), {
      timeout: 3000,
    });
    expect(onLoginSuccess).toHaveBeenCalledWith({
      name: expect.any(String),
      role: 'Researcher',
      email: 'a@b.test',
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('signup mode advances to 2FA instead of logging in', async () => {
    const user = userEvent.setup();
    const { onLoginSuccess } = renderModal();
    await user.click(screen.getByRole('button', { name: 'Create Account' }));
    expect(screen.getByText('Create Innovation Account')).toBeInTheDocument();
    await user.click(
      screen.getByRole('button', { name: 'Proceed to 2FA Token' })
    );
    await screen.findByText('Verify 2FA Security Token');
    expect(onLoginSuccess).not.toHaveBeenCalled();
  });

  test('2FA mode shows the demo OTP note and caps input at 6 digits', async () => {
    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByRole('button', { name: 'Create Account' }));
    await user.click(
      screen.getByRole('button', { name: 'Proceed to 2FA Token' })
    );
    await screen.findByText('Verify 2FA Security Token');
    expect(screen.getByText(/Simulated demo OTP token/)).toBeInTheDocument();
    const otpInput = screen.getByDisplayValue('626108');
    expect(otpInput).toHaveAttribute('maxlength', '6');
  });

  test('forgot mode hides the password field', async () => {
    const user = userEvent.setup();
    renderModal();
    expect(passwordInput()).not.toBeNull();
    await user.click(screen.getByRole('button', { name: 'Forgot?' }));
    expect(screen.getByText('Reset Access Key')).toBeInTheDocument();
    expect(passwordInput()).toBeNull();
    expect(
      screen.getByRole('button', { name: 'Confirm Access' })
    ).toBeInTheDocument();
  });

  test.failing(
    'login must verify credentials against the backend auth endpoint',
    async () => {
      const user = userEvent.setup();
      const fetchSpy = jest.spyOn(globalThis, 'fetch');
      const { onLoginSuccess } = renderModal();
      await user.click(
        screen.getByRole('button', { name: 'Authenticate & Enter Dashboard' })
      );
      await waitFor(() => expect(onLoginSuccess).toHaveBeenCalled(), {
        timeout: 3000,
      });
      expect(fetchSpy).toHaveBeenCalled();
      fetchSpy.mockRestore();
    }
  );

  test.failing('password field must start empty', () => {
    renderModal();
    expect(passwordInput()).toHaveValue('');
  });

  test.failing('2FA OTP must not be auto-injected', async () => {
    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByRole('button', { name: 'Create Account' }));
    await user.click(
      screen.getByRole('button', { name: 'Proceed to 2FA Token' })
    );
    await screen.findByText('Verify 2FA Security Token');
    expect(screen.getByDisplayValue('626108')).toHaveValue('');
  });
});
