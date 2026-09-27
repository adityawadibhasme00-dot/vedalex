import { renderWithProviders, screen, userEvent } from './test-utils';
import JurisdictionMatrix from '../src/components/JurisdictionMatrix';
import type { RegulatoryFinding, StatutoryCitation } from '../src/types';

const citation: StatutoryCitation = {
  act_title: 'Indian Patents Act, 1970',
  section_reference: 'Section 3(p)',
  authority: 'Legislature',
  effective_date: '1970-01-01',
  exact_passage: 'A claim shall not be patented if it is a mere aggregation.',
  source_url: 'https://example.test/gazette/1970',
  authority_rank: 1,
} as StatutoryCitation;

function finding(overrides: Partial<RegulatoryFinding> = {}): RegulatoryFinding {
  return {
    jurisdiction: 'India',
    pathway_category: 'Patentability',
    status: 'condition_satisfied',
    confidence: 'HIGH',
    explanation_text: 'Deterministic match against rule pack.',
    conditions_evaluated: ['Novelty verified'],
    supporting_citations: [citation],
    next_action_steps: ['Draft claims'],
    coverage_limitations: 'None recorded',
    ...overrides,
  } as unknown as RegulatoryFinding;
}

describe('JurisdictionMatrix', () => {
  test('shows empty-state prompt when there are no findings', () => {
    renderWithProviders(
      <JurisdictionMatrix findings={[]} onSelectCitation={jest.fn()} coverageMeterScore={0} />
    );
    expect(
      screen.getByText(/Please generate an assessment/)
    ).toBeInTheDocument();
  });

  test('renders jurisdiction cards with coverage meter', () => {
    renderWithProviders(
      <JurisdictionMatrix
        findings={[
          finding(),
          finding({ jurisdiction: 'United States', confidence: 'MEDIUM' }),
          finding({ jurisdiction: 'Canada', confidence: 'LOW' }),
        ]}
        onSelectCitation={jest.fn()}
        coverageMeterScore={75}
      />
    );
    expect(screen.getByText('India')).toBeInTheDocument();
    expect(screen.getByText('United States')).toBeInTheDocument();
    expect(screen.getByText('Canada')).toBeInTheDocument();
    expect(screen.getAllByText(/75% Evaluated/)).toHaveLength(1);
    expect(screen.getByText('HIGH CONFIDENCE')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM CONFIDENCE')).toBeInTheDocument();
    expect(screen.getByText('LOW CONFIDENCE')).toBeInTheDocument();
  });

  test('unknown confidence renders abstain badge', () => {
    renderWithProviders(
      <JurisdictionMatrix
        findings={[finding({ confidence: 'INSUFFICIENT_EVIDENCE' as any })]}
        onSelectCitation={jest.fn()}
        coverageMeterScore={10}
      />
    );
    expect(screen.getByText('ABSTAIN / LOW EVIDENCE')).toBeInTheDocument();
  });

  test('citation button invokes onSelectCitation with the citation', async () => {
    const user = userEvent.setup();
    const onSelectCitation = jest.fn();
    renderWithProviders(
      <JurisdictionMatrix
        findings={[finding()]}
        onSelectCitation={onSelectCitation}
        coverageMeterScore={50}
      />
    );
    await user.click(screen.getByText(/Indian Patents Act, 1970/));
    expect(onSelectCitation).toHaveBeenCalledWith(citation);
  });

  test('renders conditions, actions, limitations and explanation', () => {
    renderWithProviders(
      <JurisdictionMatrix
        findings={[finding()]}
        onSelectCitation={jest.fn()}
        coverageMeterScore={50}
      />
    );
    expect(screen.getByText('Novelty verified')).toBeInTheDocument();
    expect(screen.getByText('Draft claims')).toBeInTheDocument();
    expect(screen.getByText('None recorded')).toBeInTheDocument();
    expect(screen.getByText('Deterministic match against rule pack.')).toBeInTheDocument();
  });

  test('falls back to default explanation when none provided', () => {
    renderWithProviders(
      <JurisdictionMatrix
        findings={[finding({ explanation_text: null as any })]}
        onSelectCitation={jest.fn()}
        coverageMeterScore={50}
      />
    );
    expect(
      screen.getByText(/Pathway conditions deterministically matched/)
    ).toBeInTheDocument();
  });

  test('unsatisfied status is distinguished from satisfied', () => {
    const { container } = renderWithProviders(
      <JurisdictionMatrix
        findings={[
          finding({ status: 'condition_not_satisfied' }),
          finding({ status: 'condition_satisfied' }),
        ]}
        onSelectCitation={jest.fn()}
        coverageMeterScore={50}
      />
    );
    const cards = container.querySelectorAll('div.glass-panel.rounded-2xl.p-5');
    expect(cards).toHaveLength(2);
    expect(cards[0].className).toContain('border-amber-500/40');
    expect(cards[1].className).toContain('border-emerald-500/30');
  });
});
