import { renderWithProviders, screen } from './test-utils';
import AdminDashboard from '../src/components/AdminDashboard';

describe('AdminDashboard', () => {
  test('renders the security hub header and status badge', () => {
    renderWithProviders(<AdminDashboard />);
    expect(
      screen.getByText('Enterprise System Administration & Security Hub')
    ).toBeInTheDocument();
    expect(screen.getByText(/All Systems Operational/)).toBeInTheDocument();
  });

  test('renders the dynamic feature flags section', () => {
    const { container } = renderWithProviders(<AdminDashboard />);
    expect(
      screen.getByText('Dynamic Feature Flags (Zero Downtime Toggle)')
    ).toBeInTheDocument();
    expect(screen.getByText('IP-SAKTI Assistant')).toBeInTheDocument();
    expect(screen.getByText('Reactive What-If Simulation DAG')).toBeInTheDocument();
    expect(screen.getByText('DPDP Act 2023 Consent Audit Hashes')).toBeInTheDocument();
    const toggles = container.querySelectorAll('button');
    expect(toggles).toHaveLength(3);
    expect(container.querySelectorAll('svg.lucide-toggle-right')).toHaveLength(3);
  });

  test('toggling a feature flag flips its rendered state locally', async () => {
    const user = (await import('@testing-library/user-event')).default.setup();
    const { container } = renderWithProviders(<AdminDashboard />);
    const [firstToggle] = Array.from(container.querySelectorAll('button'));
    await user.click(firstToggle);
    expect(container.querySelectorAll('svg.lucide-toggle-right')).toHaveLength(2);
    expect(container.querySelectorAll('svg.lucide-toggle-left')).toHaveLength(1);
  });

  test('renders the audit log panel with its columns', () => {
    renderWithProviders(<AdminDashboard />);
    expect(
      screen.getByText('Cryptographic Consent & Access Audit Logs (SHA-256)')
    ).toBeInTheDocument();
    expect(screen.getByText('EXPORT_PASSPORT_PDF')).toBeInTheDocument();
    expect(screen.getByText('DPDP_CONSENT_CAPTURED')).toBeInTheDocument();
    expect(screen.getByText(/SHA256: e3b0c442/)).toBeInTheDocument();
    expect(screen.getByText(/User: founder@ayurstartup.in/)).toBeInTheDocument();
  });

  test.failing(
    'feature flag toggles must be persisted to the backend',
    async () => {
      const user = (await import('@testing-library/user-event')).default.setup();
      const fetchSpy = jest.spyOn(globalThis, 'fetch');
      const { container } = renderWithProviders(<AdminDashboard />);
      const [firstToggle] = Array.from(container.querySelectorAll('button'));
      await user.click(firstToggle);
      expect(fetchSpy).toHaveBeenCalled();
      fetchSpy.mockRestore();
    }
  );

  test.failing(
    'audit log entries must be loaded from the backend, not hardcoded',
    () => {
      renderWithProviders(<AdminDashboard />);
      expect(screen.queryByText('EXPORT_PASSPORT_PDF')).toBeNull();
    }
  );
});
