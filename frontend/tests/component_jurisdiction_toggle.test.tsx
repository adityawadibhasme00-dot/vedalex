import { renderWithProviders, screen } from './test-utils';
import userEvent from '@testing-library/user-event';
import { JurisdictionToggle } from '../src/components/ui/JurisdictionToggle';

describe('JurisdictionToggle (Component 3)', () => {
  test('renders India / International / Both options', () => {
    renderWithProviders(
      <JurisdictionToggle value="india" onChange={jest.fn()} />
    );
    expect(screen.getByText('India')).toBeInTheDocument();
    expect(screen.getByText('International')).toBeInTheDocument();
    expect(screen.getByText('Both')).toBeInTheDocument();
  });

  test('exposes an accessible labelled group with aria-pressed', () => {
    renderWithProviders(
      <JurisdictionToggle value="india" onChange={jest.fn()} />
    );
    const group = screen.getByRole('group');
    expect(group).toHaveAccessibleName('Jurisdiction scope');
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(3);
    expect(buttons[0]).toHaveAttribute('aria-pressed', 'true');
    expect(buttons[1]).toHaveAttribute('aria-pressed', 'false');
    expect(buttons[2]).toHaveAttribute('aria-pressed', 'false');
  });

  test('clicking International fires onChange with the new value', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    renderWithProviders(
      <JurisdictionToggle value="india" onChange={onChange} />
    );
    await user.click(screen.getByRole('button', { name: /International/i }));
    expect(onChange).toHaveBeenCalledWith('international');
  });

  test('reflects the controlled value prop in active state', () => {
    renderWithProviders(
      <JurisdictionToggle value="both" onChange={jest.fn()} />
    );
    const buttons = screen.getAllByRole('button');
    expect(buttons[2]).toHaveAttribute('aria-pressed', 'true');
    expect(buttons[0]).toHaveAttribute('aria-pressed', 'false');
  });

  test('disabled state blocks clicks', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    renderWithProviders(
      <JurisdictionToggle value="india" onChange={onChange} disabled />
    );
    const [india] = screen.getAllByRole('button');
    expect(india).toBeDisabled();
    await user.click(india);
    expect(onChange).not.toHaveBeenCalled();
  });

  test('custom label replaces the default heading text', () => {
    renderWithProviders(
      <JurisdictionToggle
        value="india"
        onChange={jest.fn()}
        label="Answer scope"
      />
    );
    expect(screen.getByText('Answer scope')).toBeInTheDocument();
  });
});
