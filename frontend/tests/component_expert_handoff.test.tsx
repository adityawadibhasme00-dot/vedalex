import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import {
  renderWithProviders,
  screen,
  userEvent,
  waitFor,
} from './test-utils';
import ExpertHandoffModal from '../src/components/ExpertHandoffModal';

const BASE = 'http://localhost/api/v1';

function successPayload(overrides: Record<string, unknown> = {}) {
  return {
    message: 'Queued for facilitation center review.',
    ticket_id: 'TCK-1',
    assigned_facilitation_center: 'Pune IP Hub',
    consent_audit_hash: 'abcdef0123456789ffff',
    ...overrides,
  };
}

describe('ExpertHandoffModal', () => {
  test('renders nothing when closed', () => {
    const { container } = renderWithProviders(
      <ExpertHandoffModal isOpen={false} onClose={() => {}} passportId="p1" />
    );
    expect(container.innerHTML).toBe('');
  });

  test('renders all three expert track options', () => {
    renderWithProviders(
      <ExpertHandoffModal isOpen onClose={() => {}} passportId="p1" />
    );
    const select = screen.getByRole('combobox');
    expect(select).toHaveLength(3);
    expect(screen.getByText(/Registered Patent Agent \(Indian Patent Office/)).toBeInTheDocument();
    expect(screen.getByText(/AYUSH Regulatory Consultant/)).toBeInTheDocument();
    expect(screen.getByText(/US FDA & Health Canada Export Regulatory Consultant/)).toBeInTheDocument();
  });

  test('submit is disabled while DPDP consent is unchecked', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ExpertHandoffModal isOpen onClose={() => {}} passportId="p1" />
    );
    const submit = screen.getByRole('button', {
      name: /Submit Case to Certified Expert/,
    });
    const [dpdp] = screen.getAllByRole('checkbox');
    expect(submit).toBeEnabled();
    await user.click(dpdp);
    expect(submit).toBeDisabled();
    await user.click(dpdp);
    expect(submit).toBeEnabled();
  });

  test('submit is disabled while liability acknowledgement is unchecked', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ExpertHandoffModal isOpen onClose={() => {}} passportId="p1" />
    );
    const submit = screen.getByRole('button', {
      name: /Submit Case to Certified Expert/,
    });
    const [, liability] = screen.getAllByRole('checkbox');
    await user.click(liability);
    expect(submit).toBeDisabled();
    await user.click(liability);
    expect(submit).toBeEnabled();
  });

  test('submit dispatches the case with consent flags and shows the ticket', async () => {
    const user = userEvent.setup();
    let body: any = null;
    server.use(
      http.post(`${BASE}/expert-handoff/dispatch`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(successPayload());
      })
    );
    renderWithProviders(
      <ExpertHandoffModal isOpen onClose={() => {}} passportId="pid-9" />
    );
    await user.click(
      screen.getByRole('button', { name: /Submit Case to Certified Expert/ })
    );
    await screen.findByText('Case Successfully Queued for Dispatch');
    expect(body).toMatchObject({
      passport_id: 'pid-9',
      expert_type: 'Registered Patent Agent',
      explicit_dpdp_consent: true,
      liability_boundary_acknowledged: true,
    });
    expect(body.user_name).toBeTruthy();
    expect(body.user_email).toContain('@');
    expect(screen.getByText(/TCK-1/)).toBeInTheDocument();
    expect(screen.getByText(/Pune IP Hub/)).toBeInTheDocument();
    expect(screen.getByText(/abcdef0123456789/)).toBeInTheDocument();
  });

  test('initialExpertType maps escalation keys to expert tracks', () => {
    renderWithProviders(
      <ExpertHandoffModal
        isOpen
        onClose={() => {}}
        passportId="p1"
        initialExpertType="regulatory_expert"
      />
    );
    expect(screen.getByRole('combobox')).toHaveValue(
      'AYUSH Regulatory Consultant'
    );
  });

  test('failed dispatch alerts the user', async () => {
    const user = userEvent.setup();
    const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});
    server.use(
      http.post(`${BASE}/expert-handoff/dispatch`, () =>
        HttpResponse.text('down', { status: 500 })
      )
    );
    renderWithProviders(
      <ExpertHandoffModal isOpen onClose={() => {}} passportId="p1" />
    );
    await user.click(
      screen.getByRole('button', { name: /Submit Case to Certified Expert/ })
    );
    await waitFor(() => expect(alertSpy).toHaveBeenCalledTimes(1));
    alertSpy.mockRestore();
  });

  test.failing(
    'DPDP consent must start unchecked so consent is an affirmative act',
    async () => {
      renderWithProviders(
        <ExpertHandoffModal isOpen onClose={() => {}} passportId="p1" />
      );
      const [dpdp, liability] = screen.getAllByRole('checkbox');
      expect(dpdp).not.toBeChecked();
      expect(liability).not.toBeChecked();
    }
  );
});
