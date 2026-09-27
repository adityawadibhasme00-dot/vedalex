import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

function Harness() {
  return <button type="button">Run test action</button>;
}

test('renders and accepts user interaction', async () => {
  const user = userEvent.setup();
  render(<Harness />);
  const button = screen.getByRole('button', { name: 'Run test action' });
  await user.click(button);
  expect(button).toBeEnabled();
});

test('intercepts API requests with MSW', async () => {
  const response = await fetch('http://localhost/api/v1/health');
  const payload = await response.json();
  expect(response.status).toBe(200);
  expect(payload).toEqual(
    expect.objectContaining({
      status: 'healthy',
      version: 'test',
      database: 'connected'
    })
  );
});
