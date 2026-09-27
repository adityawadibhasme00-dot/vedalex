import { renderWithProviders, screen, userEvent } from './test-utils';
import CitationPopover from '../src/components/CitationPopover';
import type { StatutoryCitation } from '../src/types';

const citation: StatutoryCitation = {
  act_title: 'Indian Patents Act, 1970',
  section_reference: 'Section 3(p)',
  authority: 'Legislature',
  effective_date: '1970-01-01',
  exact_passage: 'A claim shall not be patented if it is a mere aggregation.',
  source_url: 'https://example.test/gazette/1970',
  authority_rank: 1,
} as StatutoryCitation;

describe('CitationPopover', () => {
  test('renders nothing when citation is null', () => {
    const { container } = renderWithProviders(
      <CitationPopover citation={null} onClose={jest.fn()} />
    );
    expect(container.innerHTML).toBe('');
  });

  test('renders full statutory citation details', () => {
    renderWithProviders(<CitationPopover citation={citation} onClose={jest.fn()} />);
    expect(
      screen.getByText('Indian Patents Act, 1970')
    ).toBeInTheDocument();
    expect(screen.getByText('Section 3(p)')).toBeInTheDocument();
    expect(screen.getByText('1970-01-01')).toBeInTheDocument();
    expect(
      screen.getByText(/A claim shall not be patented/)
    ).toBeInTheDocument();
    expect(screen.getByText(/Rank #1 Authority/)).toBeInTheDocument();
    expect(screen.getByText(/Authority: Legislature/)).toBeInTheDocument();
  });

  test('official gazette link opens safely in a new tab', () => {
    renderWithProviders(<CitationPopover citation={citation} onClose={jest.fn()} />);
    const link = screen.getByRole('link', { name: /View Official Gazette/ });
    expect(link).toHaveAttribute('href', 'https://example.test/gazette/1970');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
    expect(link).toHaveAttribute('rel', expect.stringContaining('noreferrer'));
  });

  test('omits gazette link when no source_url is present', () => {
    renderWithProviders(
      <CitationPopover
        citation={{ ...citation, source_url: undefined as any }}
        onClose={jest.fn()}
      />
    );
    expect(
      screen.queryByRole('link', { name: /View Official Gazette/ })
    ).toBeNull();
  });

  test('close button invokes onClose', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    renderWithProviders(<CitationPopover citation={citation} onClose={onClose} />);
    await user.click(screen.getByRole('button'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('markup inside exact_passage is rendered as inert text', () => {
    renderWithProviders(
      <CitationPopover
        citation={{
          ...citation,
          exact_passage: '<script>alert("xss")</script> quoted passage',
        }}
        onClose={jest.fn()}
      />
    );
    expect(document.querySelector('script')).toBeNull();
    expect(
      screen.getByText(/<script>alert\("xss"\)<\/script>/)
    ).toBeInTheDocument();
  });
});
