import type { ReactElement, ReactNode } from 'react';
import { render, type RenderOptions, type RenderResult } from '@testing-library/react';
import { AuthProvider } from '../src/lib/AuthContext';
import { LangProvider } from '../src/lib/LangContext';

function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <LangProvider>{children}</LangProvider>
    </AuthProvider>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
): RenderResult {
  return render(ui, { wrapper: Providers, ...options });
}

export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
