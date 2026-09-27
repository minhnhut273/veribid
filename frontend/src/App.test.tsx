import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { App } from './App';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('landing page', () => {
  it('explains the evidence-first workflow', () => {
    render(<App />);
    expect(screen.getByText(/Turn vendor claims into/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Public demo$/i })).toBeInTheDocument();
  });

  it('routes the no-sign-up trial to the public sandbox without calling workspace APIs', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const path = String(input);
      const body = path.endsWith('/api/v1/demo')
        ? {
            data: {
              evaluation_id: 'demo-1',
              title: 'Synthetic fixture',
              status: 'DEMO',
              requirements: [{ id: 'req-residency', text: 'Keep customer data in the EU.', category: 'COMPLIANCE' }],
              vendors: [{ vendor_id: 'vendor-a', name: 'Example Vendor' }],
              matrix: [{
                requirement_id: 'req-residency',
                vendor_id: 'vendor-a',
                state: 'CONFLICTING_EVIDENCE',
                confidence: 0.93,
                source_pointers: [
                  { document_id: 'vendor-a-proposal', page: 4, locator: 'EU residency' },
                  { document_id: 'vendor-a-security', page: 2, locator: 'Telemetry processing' },
                ],
                conflict_pairs: [{ left: 'EU-only processing', right: 'Telemetry processed in US' }],
              }],
            },
            meta: { read_only: true, synthetic: true },
          }
        : { data: { service: 'veribid-api', version: 'test', status: 'ok', timestamp: 'now' } };
      return { ok: true, status: 200, json: async () => body } as Response;
    });

    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: /Open workspace/i }));
    fireEvent.click(screen.getByRole('button', { name: /Try the interactive demo/i }));

    expect(await screen.findByText(/Explore the basic review flow without an account/i)).toBeInTheDocument();
    expect(fetchSpy.mock.calls.some(([input]) => String(input).endsWith('/api/v1/demo'))).toBe(true);
    expect(fetchSpy.mock.calls.some(([input]) => String(input).includes('/api/v1/evaluations'))).toBe(false);
    expect(screen.getByText(/All vendors, requirements, and evidence are synthetic/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /click to inspect evidence/i }));
    expect(await screen.findByText(/DEMO SIMULATION · LOCAL ONLY/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Synthetic scenario statement: EU-only processing/i)).toHaveLength(2);
    expect(screen.getByText(/Sample scenario conflict/i)).toBeInTheDocument();
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'OVERRIDE' } });
    fireEvent.change(screen.getByPlaceholderText(/Override rationale is required/i), { target: { value: 'Temporary demo rationale' } });
    fireEvent.click(screen.getByRole('button', { name: /Apply locally/i }));
    expect(await screen.findByText(/Demo review: OVERRIDE/i)).toBeInTheDocument();
    expect(fetchSpy.mock.calls.some(([input]) => String(input).includes('/api/v1/evaluations'))).toBe(false);
  });

  it('keeps the landing page visible when the health endpoint returns an unexpected payload', async () => {
    window.history.replaceState({}, '', '/');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    } as Response);

    render(<App />);

    expect(screen.getByText(/Turn vendor claims into/i)).toBeInTheDocument();
    expect(await screen.findByText(/API health returned an unexpected response/i)).toBeInTheDocument();
  });
});
