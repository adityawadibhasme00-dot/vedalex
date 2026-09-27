import { renderWithProviders, screen, userEvent } from './test-utils';
import EvidenceGapList from '../src/components/EvidenceGapList';
import type { EvidenceGapSummary, EvidenceItem } from '../src/types';

const makeItem = (overrides: Partial<EvidenceItem> = {}): EvidenceItem => ({
  id: 'GAP-1',
  passport_id: 'passport-1',
  requirement_name: 'Stability study report',
  why_it_applies: 'Shelf-life data backs the preservation claim',
  expected_evidence_type: 'Test report',
  status: 'Missing',
  prerequisites: [],
  next_action: 'Upload the 6-month stability data',
  jurisdiction: 'India (FSSAI)',
  ...overrides,
});

const makeSummary = (items: EvidenceItem[]): EvidenceGapSummary => ({
  passport_id: 'passport-1',
  total_checks: 8,
  evaluated_checks: 3,
  blocked_by_missing_sources: 2,
  coverage_meter_percentage: 38,
  items,
});

function renderList(summary: EvidenceGapSummary | null, isLoading = false) {
  const onUpdateStatus = jest.fn();
  renderWithProviders(
    <EvidenceGapList
      evidenceSummary={summary}
      isLoading={isLoading}
      onUpdateStatus={onUpdateStatus}
    />
  );
  return { onUpdateStatus };
}

describe('EvidenceGapList', () => {
  test('asks for an assessment when no checklist is loaded', () => {
    renderList(null);
    expect(screen.getByText(/No evidence checklist loaded/)).toBeInTheDocument();
  });

  test('reports how much of the case is covered', () => {
    renderList(makeSummary([makeItem()]));
    expect(
      screen.getByRole('heading', { name: /Evidence-Gap Analysis/ })
    ).toBeInTheDocument();
    expect(screen.getByText('3 of 8 requirements evaluated')).toBeInTheDocument();
    expect(screen.getByText('38%')).toBeInTheDocument();
  });

  test('renders every requirement with its context and next action', () => {
    renderList(
      makeSummary([
        makeItem(),
        makeItem({
          id: 'GAP-2',
          requirement_name: 'Marker chromatogram',
          jurisdiction: 'USA (FDA)',
          expected_evidence_type: 'Chromatogram',
          status: 'Uploaded',
          why_it_applies: 'Identity confirmation for the declared botanical',
          next_action: 'Await reviewer confirmation',
        }),
      ])
    );
    expect(screen.getByText('Stability study report')).toBeInTheDocument();
    expect(screen.getByText('GAP-1 • India (FSSAI)')).toBeInTheDocument();
    expect(screen.getByText('(Test report)')).toBeInTheDocument();
    expect(
      screen.getByText('Shelf-life data backs the preservation claim')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Next Action: Upload the 6-month stability data/)
    ).toBeInTheDocument();
    expect(screen.getByText('Marker chromatogram')).toBeInTheDocument();
    expect(screen.getByText('GAP-2 • USA (FDA)')).toBeInTheDocument();
  });

  test('labels each lifecycle state of a requirement', () => {
    const statuses: EvidenceItem['status'][] = [
      'Missing',
      'Uploaded',
      'Needs review',
      'Accepted for this assessment',
    ];
    renderList(
      makeSummary(statuses.map((status, i) => makeItem({ id: `GAP-${i + 1}`, status })))
    );
    expect(screen.getByText('Missing Evidence', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getByText('Uploaded', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getByText('Needs Review', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getByText('Accepted', { selector: 'span' })).toBeInTheDocument();
  });

  test('moves an item through its lifecycle with the row selector', async () => {
    const user = userEvent.setup();
    const { onUpdateStatus } = renderList(makeSummary([makeItem()]));
    const select = screen.getByRole('combobox');
    expect(select).toHaveValue('Missing');
    await user.selectOptions(select, 'Uploaded');
    expect(onUpdateStatus).toHaveBeenCalledTimes(1);
    expect(onUpdateStatus).toHaveBeenCalledWith('GAP-1', 'Uploaded');
  });

  test('lists every lifecycle state as a transition target', () => {
    renderList(makeSummary([makeItem({ status: 'Needs review' })]));
    const select = screen.getByRole('combobox') as HTMLSelectElement;
    expect(select).toHaveValue('Needs review');
    const options = Array.from(select.options).map((option) => option.textContent);
    expect(options).toEqual([
      'Missing',
      'Uploaded',
      'Needs review',
      'Accepted for assessment',
    ]);
  });

  test.failing('a loading checklist reports progress instead of an empty state', () => {
    renderList(null, true);
    expect(screen.queryByText(/No evidence checklist loaded/)).toBeNull();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
