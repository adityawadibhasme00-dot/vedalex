import { renderWithProviders, screen } from './test-utils';
import userEvent from '@testing-library/user-event';
import { HumanEscalation } from '../src/components/escalation/HumanEscalation';

describe('HumanEscalation (Component 12)', () => {
  test('renders facilitator contact details', () => {
    renderWithProviders(<HumanEscalation />);
    expect(screen.getByText('Human IP Facilitator')).toBeInTheDocument();
    expect(
      screen.getByText('Aditya Sharma (Compliance Lead)')
    ).toBeInTheDocument();
    expect(screen.getByText('grievance@ipsakti.in')).toBeInTheDocument();
  });

  test('email link targets the facilitator and includes the query', () => {
    renderWithProviders(
      <HumanEscalation query="Can we patent Ashwagandha churna?" />
    );
    const link = screen.getByRole('link', { name: /Email facilitator/i });
    const href = link.getAttribute('href') ?? '';
    expect(href.startsWith('mailto:grievance@ipsakti.in')).toBe(true);
    expect(decodeURIComponent(href)).toContain(
      'Can we patent Ashwagandha churna?'
    );
  });

  test('escalated query is echoed in the card', () => {
    renderWithProviders(
      <HumanEscalation query="Should I sue them?" />
    );
    expect(screen.getByText(/Should I sue them\?/)).toBeInTheDocument();
  });

  test('export button delivers payload via onExport callback', async () => {
    const user = userEvent.setup();
    const onExport = jest.fn();
    const log = [{ step: 'orchestrator', result: 'PRODUCT_SPECIFIC' }];
    renderWithProviders(
      <HumanEscalation
        query="Ashwagandha churna patent"
        log={log}
        onExport={onExport}
      />
    );
    await user.click(
      screen.getByRole('button', { name: /Export query log/i })
    );
    expect(onExport).toHaveBeenCalledTimes(1);
    const payload = onExport.mock.calls[0][0];
    expect(payload.query).toBe('Ashwagandha churna patent');
    expect(payload.log).toEqual(log);
    expect(typeof payload.exportedAt).toBe('string');
  });

  test('phone row and call link only render when phone provided', () => {
    const { rerender } = renderWithProviders(<HumanEscalation />);
    expect(screen.queryByText('Phone')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: /^Call$/i })
    ).not.toBeInTheDocument();

    rerender(<HumanEscalation phone="+91 11 4000 0000" />);
    expect(screen.getByText('Phone')).toBeInTheDocument();
    const call = screen.getByRole('link', { name: /^Call$/i });
    expect(call.getAttribute('href')).toBe('tel:+911140000000');
  });
});
