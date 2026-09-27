import { renderWithProviders, screen, userEvent } from './test-utils';
import ClarificationAlert from '../src/components/ClarificationAlert';
import type { ClarificationQuery } from '../src/types';

const EN_QUESTION = 'Which solvent system is used for the extraction?';
const HI_QUESTION = 'à¤¨à¤¿à¤·à¥à¤•à¤°à¥à¤·à¤£ à¤•à¥‡ à¤²à¤¿à¤ à¤•à¥Œà¤¨ à¤¸à¤¾ à¤µà¤¿à¤²à¤¾à¤¯à¤• à¤ªà¥à¤°à¤¯à¥‹à¤— à¤¹à¥‹à¤¤à¤¾ à¤¹à¥ˆ?';

const baseQuery: ClarificationQuery = {
  id: 'clar-1',
  field_key: 'solvent',
  question_text: { en: EN_QUESTION, hi: HI_QUESTION },
  options: ['Ethanol 90% v/v', 'Hydroalcoholic 70% v/v'],
  severity: 'decision-critical',
};

function renderAlert(queries: ClarificationQuery[], currentLang = 'en') {
  const onResolve = jest.fn();
  renderWithProviders(
    <ClarificationAlert
      clarifications={queries}
      currentLang={currentLang}
      onResolve={onResolve}
    />
  );
  return { onResolve };
}

describe('ClarificationAlert', () => {
  test('renders nothing while no clarification is pending', () => {
    const { container } = renderWithProviders(
      <ClarificationAlert clarifications={[]} currentLang="en" onResolve={jest.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  test('asks the first pending question in the active language', () => {
    renderAlert([baseQuery], 'hi');
    expect(screen.getByText(HI_QUESTION)).toBeInTheDocument();
    expect(screen.queryByText(EN_QUESTION)).toBeNull();
    expect(
      screen.getByText('Decision-Critical Clarification Required')
    ).toBeInTheDocument();
  });

  test('falls back to English when the active language is unavailable', () => {
    renderAlert([baseQuery], 'mr');
    expect(screen.getByText(EN_QUESTION)).toBeInTheDocument();
    expect(screen.queryByText(HI_QUESTION)).toBeNull();
  });

  test('falls back to any available language when English is missing', () => {
    renderAlert([{ ...baseQuery, question_text: { hi: HI_QUESTION } }], 'en');
    expect(screen.getByText(HI_QUESTION)).toBeInTheDocument();
  });

  test('offers every answer option as an action', () => {
    renderAlert([baseQuery]);
    expect(
      screen.getByRole('button', { name: /Ethanol 90% v\/v/ })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Hydroalcoholic 70% v\/v/ })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/FSSAI Ayurveda Aahara food category/)
    ).toBeInTheDocument();
  });

  test('resolving with an option reports the query id and the choice', async () => {
    const user = userEvent.setup();
    const { onResolve } = renderAlert([baseQuery]);
    await user.click(
      screen.getByRole('button', { name: /Hydroalcoholic 70% v\/v/ })
    );
    expect(onResolve).toHaveBeenCalledTimes(1);
    expect(onResolve).toHaveBeenCalledWith('clar-1', 'Hydroalcoholic 70% v/v');
    expect(onResolve).not.toHaveBeenCalledWith('clar-1', 'Ethanol 90% v/v');
  });
});
