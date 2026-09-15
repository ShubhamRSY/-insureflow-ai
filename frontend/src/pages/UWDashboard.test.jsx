import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import UWDashboard from './UWDashboard';

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual('../lib/api');
  return {
    ...actual,
    endpoints: {
      workflowInbox: vi.fn(),
    },
  };
});

import { endpoints } from '../lib/api';

const pendingCase = {
  id: 'job-1',
  results: { insured_name: 'Acme Corp', state: 'CA', insurance_line: 'general_liability', memo: { overall_risk_score: 5 } },
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
    endpoints.workflowInbox.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows the all-caught-up message when there is nothing pending', async () => {
    endpoints.workflowInbox.mockResolvedValue({ cases: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('All caught up! No submissions pending review.')).toBeInTheDocument();
    });
  });

  it('renders a pending submission row', async () => {
    endpoints.workflowInbox.mockResolvedValue({ cases: [pendingCase] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    expect(screen.getAllByText('CA').length).toBeGreaterThan(0);
    expect(screen.getByText('Risk 5/10')).toBeInTheDocument();
  });

  it('renders the pending-review metric count', async () => {
    endpoints.workflowInbox.mockResolvedValue({ cases: [pendingCase] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Needs Review (1)')).toBeInTheDocument();
    });
  });

  it('filters the inbox by search query', async () => {
    endpoints.workflowInbox.mockResolvedValue({
      cases: [pendingCase, { id: 'job-2', results: { insured_name: 'Beta LLC', state: 'NY' } }],
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
    endpoints.workflowInbox.mockResolvedValue({ cases: [pendingCase] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Acme Corp'));

    expect(screen.getByText('Next step')).toBeInTheDocument();
    expect(screen.getByText('Open Workbench')).toBeInTheDocument();
  });

  it('toggles the keyboard shortcuts panel', async () => {
    endpoints.workflowInbox.mockResolvedValue({ cases: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('All caught up! No submissions pending review.')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTitle('Keyboard shortcuts (?)'));

    expect(screen.getByText('Keyboard Shortcuts')).toBeInTheDocument();
  });

  it('shows regulatory alerts fetched from the law tracker endpoint', async () => {
    endpoints.workflowInbox.mockResolvedValue({ cases: [] });
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
    endpoints.workflowInbox.mockResolvedValue({ cases: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No alerts')).toBeInTheDocument();
    });
  });

  it('dismisses an alert', async () => {
    endpoints.workflowInbox.mockResolvedValue({ cases: [] });
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
