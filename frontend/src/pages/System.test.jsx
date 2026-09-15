import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SystemPage from './System';

const health = {
  overall: 'healthy',
  llm_mode: 'live',
  summary: { ok: 8, degraded: 1, missing: 0, total: 9 },
  checks: [
    { component: 'Database', message: 'Connected', status: 'ok' },
    { component: 'LLM Provider', message: 'Rate limited', status: 'degraded' },
  ],
};

function renderPage(props = {}) {
  return render(
    <MemoryRouter>
      <SystemPage health={null} {...props} />
    </MemoryRouter>
  );
}

describe('SystemPage', () => {
  it('shows a loading spinner when health is not yet loaded', () => {
    const { container } = renderPage({ health: null });
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders overall health status and LLM mode', () => {
    renderPage({ health });
    expect(screen.getByText('healthy')).toBeInTheDocument();
    expect(screen.getByText('live')).toBeInTheDocument();
  });

  it('renders the computed health percentage', () => {
    renderPage({ health });
    expect(screen.getByText('89%')).toBeInTheDocument();
  });

  it('renders ok/degraded/missing counts', () => {
    renderPage({ health });
    expect(screen.getByText('8 OK')).toBeInTheDocument();
    expect(screen.getByText('1 Degraded')).toBeInTheDocument();
    expect(screen.getByText('0 Missing')).toBeInTheDocument();
  });

  it('renders each health check with its status', () => {
    renderPage({ health });
    expect(screen.getByText('Database')).toBeInTheDocument();
    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('LLM Provider')).toBeInTheDocument();
    expect(screen.getByText('Rate limited')).toBeInTheDocument();
  });

  it('links to the Pilot Lab', () => {
    renderPage({ health });
    const link = screen.getByText(/Open Pilot Lab/);
    expect(link).toHaveAttribute('href', '/pilot');
  });
});
