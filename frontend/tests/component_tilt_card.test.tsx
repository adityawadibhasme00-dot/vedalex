import { renderWithProviders, screen, userEvent } from './test-utils';
import TiltCard from '../src/components/TiltCard';

describe('TiltCard', () => {
  test('renders its content without offering a flip control', () => {
    renderWithProviders(
      <TiltCard>
        <p>Confidential dossier</p>
      </TiltCard>
    );
    expect(screen.getByText('Confidential dossier')).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });

  test('offers no flip control when only the front face exists', () => {
    renderWithProviders(<TiltCard isFlippable>
      <p>Front only</p>
    </TiltCard>);
    expect(screen.getByText('Front only')).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });

  test('flips between the front and back faces', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <TiltCard isFlippable backContent={<p>Confidence 91%</p>}>
        <p>Prior art dossier</p>
      </TiltCard>
    );
    expect(screen.getByText('Prior art dossier')).toBeInTheDocument();
    expect(screen.queryByText('Confidence 91%')).toBeNull();

    await user.click(screen.getByRole('button', { name: 'Inspect Stat' }));
    expect(screen.getByText('Confidence 91%')).toBeInTheDocument();
    expect(screen.queryByText('Prior art dossier')).toBeNull();

    await user.click(screen.getByRole('button', { name: 'Flip Front' }));
    expect(screen.getByText('Prior art dossier')).toBeInTheDocument();
    expect(screen.queryByText('Confidence 91%')).toBeNull();
  });

  test('falls back to the front face when a flip has no back face to show', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <TiltCard backContent={<p>Back face</p>}>
        <p>Front face</p>
      </TiltCard>
    );
    expect(screen.getByText('Front face')).toBeInTheDocument();
    expect(screen.queryByText('Back face')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
  });
});
