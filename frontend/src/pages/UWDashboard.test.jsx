import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import UWDashboard from './UWDashboard';

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual('../lib/api');
  return {
    ...actual,
    endpoints: {
      uwWorkbench: vi.fn(),
    },
  };
});

import { endpoints } from '../lib/api';

const pendingCase = {
  bundle_id: 'bundle-1',
  insured_name: 'Acme Corp',
  insurance_line: 'general_liability',
  risk_score: 50,
  ai_decision: 'quote',
};

function renderPage(props = {}) {
  return render(
    <MemoryRouter>
      <UWDashboard onOpenJob={vi.fn()} {...props} />
    </MemoryRouter>
  );
}

describe('UWDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
    vi.stubGlobal('localStorage', { getItem: vi.fn().mockReturnValue('fake-token') });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows a loading spinner while fetching the inbox', () => {
    endpoints.uwWorkbench.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows the all-caught-up message when there is nothing pending', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [], done: [], totals: {} });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('All caught up')).toBeInTheDocument();
    });
    expect(screen.getByText('No submissions pending review.')).toBeInTheDocument();
  });

  it('renders a pending submission row', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingCase], done: [], totals: { pending: 1 } });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    expect(screen.getByText('Risk 50%')).toBeInTheDocument();
    expect(screen.getByText('Quote')).toBeInTheDocument();
  });

  it('renders the pending-review metric count', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingCase], done: [], totals: { pending: 1 } });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Needs Review (1)')).toBeInTheDocument();
    });
  });

  it('filters the inbox by search query', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [pendingCase, { bundle_id: 'bundle-2', insured_name: 'Beta LLC' }],
      done: [],
      totals: { pending: 2 },
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText('Search submissions... ( / )'), { target: { value: 'beta' } });

    expect(screen.queryByText('Acme Corp')).not.toBeInTheDocument();
    expect(screen.getByText('Beta LLC')).toBeInTheDocument();
  });

  it('selects a job and shows the "Next step" quick-actions panel', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingCase], done: [], totals: { pending: 1 } });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Acme Corp'));

    expect(screen.getByText('Next step')).toBeInTheDocument();
    expect(screen.getByText('Open Workbench')).toBeInTheDocument();
  });

  it('opens the selected job via onOpenJob when "Open submission" is clicked', async () => {
    const onOpenJob = vi.fn();
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingCase], done: [], totals: { pending: 1 } });
    renderPage({ onOpenJob });

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Acme Corp'));
    fireEvent.click(screen.getByText('Open submission'));

    expect(onOpenJob).toHaveBeenCalledWith('insurance', 'bundle-1', 'bundle-1');
  });

  it('toggles the keyboard shortcuts panel', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [], done: [], totals: {} });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('All caught up')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTitle('Keyboard shortcuts (?)'));

    expect(screen.getByText('Keyboard Shortcuts')).toBeInTheDocument();
  });

  it('shows regulatory alerts fetched from the law tracker endpoint', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [], done: [], totals: {} });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ alerts: [{ alert_id: 'a1', title: 'New rate filing', severity: 'warning', detected_at: '2026-01-01T00:00:00Z' }] }),
    }));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('New rate filing')).toBeInTheDocument();
    });
  });

  it('shows "No alerts" when the alerts feed is empty', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [], done: [], totals: {} });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No alerts')).toBeInTheDocument();
    });
  });

  it('dismisses an alert', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [], done: [], totals: {} });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ alerts: [{ alert_id: 'a1', title: 'New rate filing', severity: 'warning', reviewed: false }] }),
    }));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Dismiss')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Dismiss'));

    await waitFor(() => {
      expect(screen.queryByText('Dismiss')).not.toBeInTheDocument();
    });
  });
});
