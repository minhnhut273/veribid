import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from './App';

describe('landing page', () => {
  it('explains the evidence-first workflow', () => {
    render(<App />);
    expect(screen.getByText(/Turn vendor claims into/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Public demo$/i })).toBeInTheDocument();
  });
});
