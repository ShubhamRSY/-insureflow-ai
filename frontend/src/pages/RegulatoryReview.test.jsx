import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import RegulatoryReview from './RegulatoryReview';

vi.mock('../lib/api', () => ({
  api: vi.fn(),
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

vi.mock('../components/StateRegulatoryPanel', () => ({
  default: () => <div data-testid="state-regulatory-panel">StateRegulatoryPanel</div>,
}));

import { api } from '../lib/api';
import { toast } from '../lib/toast';

const change = {
  changelog_id: 'chg-1', state: 'detected', line_of_business: 'General Liability',
  rule_key: 'min_premium', old_value: '500', new_value: '750', source: 'ISO circular',
  detected_at: '2026-01-01T00:00:00Z',
};

function setupEmpty() {
  api.mockImplementation((path) => {
    if (path === '/api/regulatory/review/pending') return Promise.resolve({ changes: [] });
    if (path === '/api/regulatory/health') return Promise.resolve(null);
    if (path === '/api/regulatory/changelog') return Promise.resolve({ entries: [] });
    return Promise.resolve(null);
  });
}

describe('RegulatoryReview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching regulatory data', () => {
    api.mockReturnValue(new Promise(() => {}));
    const { container } = render(<RegulatoryReview />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('always renders the StateRegulatoryPanel', async () => {
    setupEmpty();
    render(<RegulatoryReview />);

    await waitFor(() => {
      expect(screen.getByTestId('state-regulatory-panel')).toBeInTheDocument();
    });
  });

  it('shows an empty state when there are no pending changes', async () => {
    setupEmpty();
    render(<RegulatoryReview />);

    await waitFor(() => {
      expect(screen.getByText('No pending changes')).toBeInTheDocument();
    });
  });

  it('renders a pending change row', async () => {
    api.mockImplementation((path) => {
      if (path === '/api/regulatory/review/pending') return Promise.resolve({ changes: [change] });
      if (path === '/api/regulatory/health') return Promise.resolve(null);
      if (path === '/api/regulatory/changelog') return Promise.resolve({ entries: [] });
      return Promise.resolve(null);
    });
    render(<RegulatoryReview />);

    await waitFor(() => {
      expect(screen.getByText('min_premium')).toBeInTheDocument();
    });
    expect(screen.getByText('500')).toBeInTheDocument();
    expect(screen.getByText('750')).toBeInTheDocument();
    expect(screen.getByText(/ISO circular/)).toBeInTheDocument();
  });

  it('renders overall freshness score when health data is present', async () => {
    api.mockImplementation((path) => {
      if (path === '/api/regulatory/review/pending') return Promise.resolve({ changes: [] });
      if (path === '/api/regulatory/health') return Promise.resolve({ overall_freshness: 82.4, by_line_of_business: {} });
      if (path === '/api/regulatory/changelog') return Promise.resolve({ entries: [] });
      return Promise.resolve(null);
    });
    render(<RegulatoryReview />);

    await waitFor(() => {
      expect(screen.getAllByText('82.4%').length).toBeGreaterThan(0);
    });
  });

  it('renders per-line-of-business freshness breakdown', async () => {
    api.mockImplementation((path) => {
      if (path === '/api/regulatory/review/pending') return Promise.resolve({ changes: [] });
      if (path === '/api/regulatory/health') return Promise.resolve({ overall_freshness: 90, by_line_of_business: { general_liability: { score: 95, label: 'General Liability' } } });
      if (path === '/api/regulatory/changelog') return Promise.resolve({ entries: [] });
      return Promise.resolve(null);
    });
    render(<RegulatoryReview />);

    await waitFor(() => {
      expect(screen.getByText('Freshness by line of business')).toBeInTheDocument();
    });
    expect(screen.getByText('General Liability')).toBeInTheDocument();
  });

  it('approves a pending change', async () => {
    api.mockImplementation((path, opts) => {
      if (path === '/api/regulatory/review/pending') return Promise.resolve({ changes: [change] });
      if (path === '/api/regulatory/health') return Promise.resolve(null);
      if (path === '/api/regulatory/changelog') return Promise.resolve({ entries: [] });
      if (path.startsWith('/api/regulatory/review/chg-1')) return Promise.resolve({ ok: true });
      return Promise.resolve(null);
    });
    render(<RegulatoryReview />);

    await waitFor(() => {
      expect(screen.getByText('Approve')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Approve'));

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith('/api/regulatory/review/chg-1?approved=true', { method: 'POST' });
    });
  });

  it('shows a toast error when reviewing a change fails', async () => {
    api.mockImplementation((path) => {
      if (path === '/api/regulatory/review/pending') return Promise.resolve({ changes: [change] });
      if (path === '/api/regulatory/health') return Promise.resolve(null);
      if (path === '/api/regulatory/changelog') return Promise.resolve({ entries: [] });
      if (path.startsWith('/api/regulatory/review/chg-1')) return Promise.reject(new Error('Not authorized'));
      return Promise.resolve(null);
    });
    render(<RegulatoryReview />);

    await waitFor(() => {
      expect(screen.getByText('Reject')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Reject'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Not authorized');
    });
  });

  it('renders the recent changelog table when entries exist', async () => {
    api.mockImplementation((path) => {
      if (path === '/api/regulatory/review/pending') return Promise.resolve({ changes: [] });
      if (path === '/api/regulatory/health') return Promise.resolve(null);
      if (path === '/api/regulatory/changelog') {
        return Promise.resolve({ entries: [{ changelog_id: 'chg-2', state: 'approved', rule_key: 'max_limit', reviewed_by: 'jdoe', reviewed_at: '2026-01-02T00:00:00Z' }] });
      }
      return Promise.resolve(null);
    });
    render(<RegulatoryReview />);

    await waitFor(() => {
      expect(screen.getByText('Recent changelog')).toBeInTheDocument();
    });
    expect(screen.getByText('max_limit')).toBeInTheDocument();
    expect(screen.getByText('jdoe')).toBeInTheDocument();
  });
});
