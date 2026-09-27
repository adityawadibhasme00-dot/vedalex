import { renderWithProviders, screen, userEvent, within } from './test-utils';
import { ActivityItem } from '../src/components/dashboard/ActivityItem';
import { ActionCard } from '../src/components/dashboard/ActionCard';
import { GovStatCard } from '../src/components/dashboard/GovStatCard';
import { ProjectCard } from '../src/components/dashboard/ProjectCard';

describe('ActivityItem', () => {
  test('renders the activity with its icon, description and time', () => {
    renderWithProviders(
      <ActivityItem
        icon={<span>icon</span>}
        title="Passport generated"
        description="Assessment finished for Ashwagandha extract"
        time="2 min ago"
        status="completed"
      />
    );
    expect(screen.getByRole('heading', { name: 'Passport generated' })).toBeInTheDocument();
    expect(
      screen.getByText('Assessment finished for Ashwagandha extract')
    ).toBeInTheDocument();
    expect(screen.getByText('2 min ago')).toBeInTheDocument();
    expect(screen.getByText('icon')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  test.each([
    ['completed', 'Completed'],
    ['in_progress', 'In Progress'],
    ['failed', 'Failed'],
  ] as const)('announces a %s activity as %s', (status, label) => {
    renderWithProviders(
      <ActivityItem icon="i" title="Task" description="Details" time="now" status={status} />
    );
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByText('Task')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
    expect(screen.getByText('now')).toBeInTheDocument();
  });
});

describe('ActionCard', () => {
  test('describes the action it offers', () => {
    renderWithProviders(
      <ActionCard
        icon="+"
        label="New Passport"
        description="Start an innovation passport"
        color="emerald"
        onClick={jest.fn()}
      />
    );
    expect(screen.getByRole('heading', { name: 'New Passport' })).toBeInTheDocument();
    expect(screen.getByText('Start an innovation passport')).toBeInTheDocument();
  });

  test('invokes its callback once when the card is clicked', async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();
    renderWithProviders(
      <ActionCard
        icon="+"
        label="New Passport"
        description="Start an innovation passport"
        color="blue"
        onClick={onClick}
      />
    );
    await user.click(screen.getByRole('button', { name: /New Passport/ }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  test('keeps separate callbacks for separate cards', async () => {
    const user = userEvent.setup();
    const first = jest.fn();
    const second = jest.fn();
    renderWithProviders(
      <>
        <ActionCard icon="a" label="First" description="first action" color="emerald" onClick={first} />
        <ActionCard icon="b" label="Second" description="second action" color="amber" onClick={second} />
      </>
    );
    await user.click(screen.getByRole('button', { name: /Second/ }));
    expect(second).toHaveBeenCalledTimes(1);
    expect(first).not.toHaveBeenCalled();
  });
});

describe('GovStatCard', () => {
  test('renders the reported figure, its label and its change', () => {
    renderWithProviders(
      <GovStatCard
        icon="chart"
        label="Passports issued"
        value="128"
        change="+12% vs last month"
        trend="up"
      />
    );
    expect(screen.getByText('128')).toBeInTheDocument();
    expect(screen.getByText('Passports issued')).toBeInTheDocument();
    expect(screen.getByText('+12% vs last month')).toBeInTheDocument();
    expect(screen.getByText('chart')).toBeInTheDocument();
  });

  test('renders a declining figure with its change text', () => {
    renderWithProviders(
      <GovStatCard icon="chart" label="Open review queues" value="7" change="-3 this week" trend="down" />
    );
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('-3 this week')).toBeInTheDocument();
  });
});

describe('ProjectCard', () => {
  test('renders the project summary, status and rounded progress', () => {
    const { container } = renderWithProviders(
      <ProjectCard
        title="Prior art dossier"
        agent="Prior Art Scout"
        status="in_progress"
        progress={66.6}
        date="12 Sep 2026"
      />
    );
    expect(screen.getByRole('heading', { name: 'Prior art dossier' })).toBeInTheDocument();
    expect(screen.getByText('Prior Art Scout')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('67%')).toBeInTheDocument();
    expect(screen.getByText('12 Sep 2026')).toBeInTheDocument();
    expect(screen.queryByRole('link')).toBeNull();
    expect(container.querySelector('[style*="width: 66.6%"]')).not.toBeNull();
  });

  test('labels a queued project as ready to run', () => {
    renderWithProviders(
      <ProjectCard title="FTO screening" agent="FTO Checker" status="queued" progress={0} date="13 Sep 2026" />
    );
    expect(screen.getByText('Ready to Run')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  test('links the project when an href is supplied', () => {
    renderWithProviders(
      <ProjectCard
        title="Dossier export"
        agent="Dossier Writer"
        status="completed"
        progress={100}
        date="14 Sep 2026"
        href="/projects/proj-1"
      />
    );
    const link = screen.getByRole('link', { name: /Dossier export/ });
    expect(link).toHaveAttribute('href', '/projects/proj-1');
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(within(link).getByText('100%')).toBeInTheDocument();
  });

  test.failing('the reported progress never exceeds 100%', () => {
    renderWithProviders(
      <ProjectCard title="Overshoot" agent="Agent" status="completed" progress={150} date="today" />
    );
    expect(screen.queryByText('150%')).toBeNull();
  });
});
