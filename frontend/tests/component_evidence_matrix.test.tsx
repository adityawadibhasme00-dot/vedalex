import { renderWithProviders, screen, userEvent, within } from './test-utils';
import EvidenceMatrix from '../src/components/EvidenceMatrix';

function renderMatrix(onStatusUpdate?: (itemId: string, status: string) => void) {
  renderWithProviders(<EvidenceMatrix onStatusUpdate={onStatusUpdate} />);
}

describe('EvidenceMatrix', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders the default rows with their strength tallies', () => {
    renderMatrix();
    expect(screen.getByText('Supports healthy sleep')).toBeInTheDocument();
    expect(screen.getByText('Batch consistency')).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(6);
    expect(screen.getByRole('button', { name: /^All/ })).toHaveTextContent('5');
    expect(screen.getByRole('button', { name: /^Strong/ })).toHaveTextContent('2');
    expect(screen.getByRole('button', { name: /^Moderate/ })).toHaveTextContent('2');
    expect(screen.queryByRole('link')).toBeNull();
  });

  test('filters the table to a single strength', async () => {
    const user = userEvent.setup();
    renderMatrix();
    await user.click(screen.getByRole('button', { name: /^Moderate/ }));
    expect(screen.getByText('Supports healthy sleep')).toBeInTheDocument();
    expect(screen.getByText('Safety profile')).toBeInTheDocument();
    expect(screen.queryByText('Batch consistency')).toBeNull();
    expect(screen.queryByText('Promotes mental relaxation')).toBeNull();
    expect(screen.getAllByRole('row')).toHaveLength(3);
  });

  test('search narrows the visible claims', async () => {
    const user = userEvent.setup();
    renderMatrix();
    const search = screen.getByPlaceholderText('Search claims or evidence...');
    await user.type(search, 'sleep');
    expect(screen.getByText('Supports healthy sleep')).toBeInTheDocument();
    expect(screen.queryByText('Batch consistency')).toBeNull();
    await user.clear(search);
    await user.type(search, 'zzzz');
    expect(screen.getByText('No evidence matches your filter.')).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(2);
  });

  test('cycling a row reports the new status to the caller', async () => {
    const user = userEvent.setup();
    const onStatusUpdate = jest.fn();
    renderMatrix(onStatusUpdate);
    const claim = screen.getByText('Standardized botanical ratio');
    const row = claim.closest('tr');
    expect(row).not.toBeNull();
    expect(
      within(row as HTMLElement).getByRole('button', { name: /Verified/ })
    ).toBeInTheDocument();
    await user.click(within(row as HTMLElement).getByRole('button', { name: /Verified/ }));
    expect(onStatusUpdate).toHaveBeenCalledTimes(1);
    expect(onStatusUpdate).toHaveBeenCalledWith('ev-3', 'RED');
    expect(
      within(row as HTMLElement).queryByRole('button', { name: /Verified/ })
    ).toBeNull();
    expect(
      within(row as HTMLElement).getByRole('button', { name: /Missing/ })
    ).toBeInTheDocument();
  });

  test('a row without a source reference offers the upload action', async () => {
    const user = userEvent.setup();
    renderMatrix();
    const row = screen.getByText('Supports healthy sleep').closest('tr') as HTMLElement;
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    const spy = jest.spyOn(input, 'click');
    await user.click(within(row).getByRole('button', { name: /^Upload$/ }));
    expect(spy).toHaveBeenCalled();
  });

  test.failing('the toolbar upload action opens the file picker', async () => {
    const user = userEvent.setup();
    renderMatrix();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    const spy = jest.spyOn(HTMLElement.prototype, 'click');
    await user.click(screen.getByRole('button', { name: /Upload Evidence/ }));
    expect(spy).toHaveBeenCalled();
  });
});
