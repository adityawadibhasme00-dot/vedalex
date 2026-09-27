import { http, HttpResponse } from 'msw';
import { server } from './mw/server';
import { renderWithProviders, screen, userEvent, waitFor } from './test-utils';
import DossierView from '../src/components/DossierView';

const BASE = 'http://localhost/api/v1';

function exportPayload(overrides: Record<string, unknown> = {}) {
  return {
    filename: 'dossier-p1.pdf',
    download_url: '/api/v1/export/files/dossier-p1.pdf',
    generated_at: '2026-09-26T10:00:00Z',
    ...overrides,
  };
}

describe('DossierView', () => {
  test('offers PDF, DOCX and checklist export actions', () => {
    renderWithProviders(<DossierView passportId="p1" />);
    expect(screen.getByText('Dossier PDF')).toBeInTheDocument();
    expect(screen.getByText('Dossier DOCX')).toBeInTheDocument();
    expect(screen.getByText('Checklist')).toBeInTheDocument();
  });

  test('runs the export request for the chosen format and shows the file', async () => {
    let requestedFormat = '';
    server.use(
      http.post(`${BASE}/export/dossier`, async ({ request }) => {
        const body: any = await request.json();
        requestedFormat = body.format;
        return HttpResponse.json(exportPayload());
      })
    );
    const user = userEvent.setup();
    renderWithProviders(<DossierView passportId="p1" />);
    await user.click(screen.getByText('Dossier PDF'));
    expect(await screen.findByText('Dossier generated successfully')).toBeInTheDocument();
    expect(requestedFormat).toBe('pdf');
    expect(screen.getByText('dossier-p1.pdf')).toBeInTheDocument();
    const links = screen.getAllByRole('link');
    for (const link of links) {
      expect(link.getAttribute('href')).toContain('/api/v1/export/files/dossier-p1.pdf');
    }
  });

  test('send the passport id with the requested format', async () => {
    let body: any = null;
    server.use(
      http.post(`${BASE}/export/dossier`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(exportPayload());
      })
    );
    const user = userEvent.setup();
    renderWithProviders(<DossierView passportId="pid-42" />);
    await user.click(screen.getByText('Checklist'));
    await screen.findByText('Dossier generated successfully');
    expect(body).toEqual({ passport_id: 'pid-42', format: 'checklist' });
  });

  test('surfaces backend export failures as an error card', async () => {
    server.use(
      http.post(`${BASE}/export/dossier`, () =>
        HttpResponse.json({ detail: 'renderer crashed' }, { status: 500 })
      )
    );
    const user = userEvent.setup();
    renderWithProviders(<DossierView passportId="p1" />);
    await user.click(screen.getByText('Dossier PDF'));
    expect(await screen.findByText(/renderer crashed/)).toBeInTheDocument();
    expect(screen.queryByText('Dossier generated successfully')).toBeNull();
  });

  test('refuses to export without a passport', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DossierView passportId="" />);
    await user.click(screen.getByText('Dossier PDF'));
    expect(
      await screen.findByText('No passport available. Create one first.')
    ).toBeInTheDocument();
    expect(screen.queryByText('Dossier generated successfully')).toBeNull();
  });

  test('disables the export buttons while a request is in flight', async () => {
    server.use(
      http.post(`${BASE}/export/dossier`, async () => {
        await new Promise((r) => setTimeout(r, 120));
        return HttpResponse.json(exportPayload());
      })
    );
    const user = userEvent.setup();
    renderWithProviders(<DossierView passportId="p1" />);
    const pdfBtn = screen.getByText('Dossier PDF').closest('button')!;
    await user.click(pdfBtn);
    expect(pdfBtn).toBeDisabled();
    await waitFor(() => expect(pdfBtn).toBeEnabled(), { timeout: 3000 });
  });

  test.failing(
    'download links must not accept cross-origin backend URLs',
    async () => {
      server.use(
        http.post(`${BASE}/export/dossier`, () =>
          HttpResponse.json(
            exportPayload({ download_url: 'http://evil.test/malware.exe' })
          )
        )
      );
      const user = userEvent.setup();
      renderWithProviders(<DossierView passportId="p1" />);
      await user.click(screen.getByText('Dossier PDF'));
      await screen.findByText('Dossier generated successfully');
      const link = screen.getByRole('link', { name: /Download again/ });
      expect(link.getAttribute('href')).not.toBe('http://evil.test/malware.exe');
    }
  );
});
