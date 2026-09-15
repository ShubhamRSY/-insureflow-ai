import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import WorkflowPage from './Workflow';

vi.mock('../lib/api', () => ({
  endpoints: {
    signOff: vi.fn(),
    bindPolicy: vi.fn(),
    workflowDetail: vi.fn(),
  },
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const pendingItem = { bundle_id: 'bundle-1', state: 'pending_review', premium: 5000, recommendation: 'Looks good' };

function renderPage(props = {}) {
  return render(<WorkflowPage pending={[]} onRefresh={vi.fn()} authorityData={null} onOpenJob={vi.fn()} {...props} />);
}

describe('WorkflowPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows an empty state when there is nothing pending', () => {
    renderPage();
    expect(screen.getByText('Queue empty')).toBeInTheDocument();
  });

  it('renders a pending item with its recommendation', () => {
    renderPage({ pending: [pendingItem] });
    expect(screen.getByText('bundle-1')).toBeInTheDocument();
    expect(screen.getByText('Looks good')).toBeInTheDocument();
  });

  it('renders the authority label when premium falls within a tier', () => {
    renderPage({
      pending: [pendingItem],
      authorityData: { authorities: [{ username: 'jdoe', tier: 'Tier 1', display_name: 'Jane Doe', binding_authority: { max_premium: 10000 } }] },
    });
    expect(screen.getByText(/Tier 1 \(Jane Doe, max \$10K\)/)).toBeInTheDocument();
  });

  it('shows "Needs CUO approval" when premium exceeds every tier', () => {
    renderPage({
      pending: [{ ...pendingItem, premium: 999999 }],
      authorityData: { authorities: [{ username: 'jdoe', tier: 'Tier 1', display_name: 'Jane Doe', binding_authority: { max_premium: 10000 } }] },
    });
    expect(screen.getByText(/Needs CUO approval/)).toBeInTheDocument();
  });

  it('opens a job when View is clicked', () => {
    const onOpenJob = vi.fn();
    renderPage({ pending: [pendingItem], onOpenJob });
    fireEvent.click(screen.getByText('View'));
    expect(onOpenJob).toHaveBeenCalledWith('insurance', 'bundle-1', 'bundle-1');
  });

  it('opens the sign-off form for Quote and submits it', async () => {
    endpoints.signOff.mockResolvedValue({ ok: true });
    const onRefresh = vi.fn();
    renderPage({ pending: [pendingItem], onRefresh });

    fireEvent.click(screen.getByText('Quote'));
    expect(screen.getByPlaceholderText('License number')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Confirm quote'));

    await waitFor(() => {
      expect(endpoints.signOff).toHaveBeenCalledWith('bundle-1', expect.objectContaining({ action: 'quote' }));
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it('shows a toast error when sign-off fails', async () => {
    endpoints.signOff.mockRejectedValue(new Error('License required'));
    renderPage({ pending: [pendingItem] });

    fireEvent.click(screen.getByText('Quote'));
    fireEvent.click(screen.getByText('Confirm quote'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('License required');
    });
  });

  it('shows a Bind button only for approved or quoted items', () => {
    renderPage({ pending: [{ ...pendingItem, state: 'approved' }] });
    expect(screen.getByText('Bind')).toBeInTheDocument();
  });

  it('does not show a Bind button for a pending_review item', () => {
    renderPage({ pending: [pendingItem] });
    expect(screen.queryByText('Bind')).not.toBeInTheDocument();
  });

  it('binds the policy when Bind is clicked', async () => {
    endpoints.bindPolicy.mockResolvedValue({ ok: true });
    const onRefresh = vi.fn();
    renderPage({ pending: [{ ...pendingItem, state: 'approved' }], onRefresh });

    fireEvent.click(screen.getByText('Bind'));

    await waitFor(() => {
      expect(endpoints.bindPolicy).toHaveBeenCalledWith('bundle-1');
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it('loads and shows workflow detail', async () => {
    endpoints.workflowDetail.mockResolvedValue({ state: 'pending_review', decision: 'accept', sign_offs: [{ license_number: 'LIC-1', action: 'quote', username: 'jdoe' }] });
    renderPage({ pending: [pendingItem] });

    fireEvent.click(screen.getByText('Detail'));

    await waitFor(() => {
      expect(screen.getByText('Workflow State')).toBeInTheDocument();
    });
    expect(screen.getByText('LIC-1')).toBeInTheDocument();
  });

  it('shows a toast error when loading workflow detail fails', async () => {
    endpoints.workflowDetail.mockRejectedValue(new Error('Not found'));
    renderPage({ pending: [pendingItem] });

    fireEvent.click(screen.getByText('Detail'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Not found');
    });
  });

  it('cancels the sign-off form', () => {
    renderPage({ pending: [pendingItem] });
    fireEvent.click(screen.getByText('Quote'));
    expect(screen.getByPlaceholderText('License number')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Cancel'));
    expect(screen.queryByPlaceholderText('License number')).not.toBeInTheDocument();
  });
});
