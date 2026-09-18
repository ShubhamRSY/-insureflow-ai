import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import WorkflowPage from './Workflow';

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual('../lib/api');
  return {
    ...actual,
    endpoints: {
      uwWorkbench: vi.fn(),
      signOff: vi.fn(),
      bindPolicy: vi.fn(),
      workflowDetail: vi.fn(),
    },
  };
});

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const pendingItem = {
  bundle_id: 'bundle-1',
  state: 'pending_review',
  insured_name: 'Acme Corp',
  premium: 5000,
  ai_decision: 'quote',
};

function renderPage(props = {}) {
  return render(<WorkflowPage onRefresh={vi.fn()} authorityData={null} onOpenJob={vi.fn()} {...props} />);
}

describe('WorkflowPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows an empty state when there is nothing pending', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [] });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Queue empty')).toBeInTheDocument();
    });
  });

  it('renders a pending item with insured name and AI recommendation', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingItem] });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('bundle-1')).toBeInTheDocument();
    });
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('AI recommendation: Quote')).toBeInTheDocument();
  });

  it('shows the reason when human review reasons are present', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [{ ...pendingItem, human_review_reasons: ['Insufficient Data'] }],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/^Why:/)).toBeInTheDocument();
    });
  });

  it('renders the authority label when premium falls within a tier', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingItem] });
    renderPage({
      authorityData: { authorities: [{ username: 'jdoe', tier: 'Tier 1', display_name: 'Jane Doe', binding_authority: { max_premium: 10000 } }] },
    });
    await waitFor(() => {
      expect(screen.getByText(/Tier 1 \(Jane Doe, max \$10K\)/)).toBeInTheDocument();
    });
  });

  it('shows "Needs CUO approval" when premium exceeds every tier', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [{ ...pendingItem, premium: 999999 }] });
    renderPage({
      authorityData: { authorities: [{ username: 'jdoe', tier: 'Tier 1', display_name: 'Jane Doe', binding_authority: { max_premium: 10000 } }] },
    });
    await waitFor(() => {
      expect(screen.getByText(/Needs CUO approval/)).toBeInTheDocument();
    });
  });

  it('opens a job when View is clicked', async () => {
    const onOpenJob = vi.fn();
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingItem] });
    renderPage({ onOpenJob });
    await waitFor(() => {
      expect(screen.getByText('View')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('View'));
    expect(onOpenJob).toHaveBeenCalledWith('insurance', 'bundle-1', 'bundle-1');
  });

  it('opens the sign-off form for Quote and submits it', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingItem] });
    endpoints.signOff.mockResolvedValue({ ok: true });
    const onRefresh = vi.fn();
    renderPage({ onRefresh });

    await waitFor(() => {
      expect(screen.getByText('Quote')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Quote'));
    expect(screen.getByPlaceholderText('License number')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Confirm Quote'));

    await waitFor(() => {
      expect(endpoints.signOff).toHaveBeenCalledWith('bundle-1', expect.objectContaining({ action: 'quote' }));
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it('shows a toast error when sign-off fails', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingItem] });
    endpoints.signOff.mockRejectedValue(new Error('License required'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Quote')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Quote'));
    fireEvent.click(screen.getByText('Confirm Quote'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('License required');
    });
  });

  it('shows a Bind button only for approved or quoted items', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [{ ...pendingItem, state: 'approved' }] });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Bind')).toBeInTheDocument();
    });
  });

  it('does not show a Bind button for a pending_review item', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingItem] });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('bundle-1')).toBeInTheDocument();
    });
    expect(screen.queryByText('Bind')).not.toBeInTheDocument();
  });

  it('binds the policy when Bind is clicked', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [{ ...pendingItem, state: 'approved' }] });
    endpoints.bindPolicy.mockResolvedValue({ ok: true });
    const onRefresh = vi.fn();
    renderPage({ onRefresh });

    await waitFor(() => {
      expect(screen.getByText('Bind')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Bind'));

    await waitFor(() => {
      expect(endpoints.bindPolicy).toHaveBeenCalledWith('bundle-1');
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it('loads and shows workflow detail', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingItem] });
    endpoints.workflowDetail.mockResolvedValue({ state: 'pending_review', decision: 'accept', sign_offs: [{ license_number: 'LIC-1', action: 'quote', username: 'jdoe' }] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Detail')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Detail'));

    await waitFor(() => {
      expect(screen.getByText('Workflow State')).toBeInTheDocument();
    });
    expect(screen.getByText('LIC-1')).toBeInTheDocument();
  });

  it('shows a toast error when loading workflow detail fails', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingItem] });
    endpoints.workflowDetail.mockRejectedValue(new Error('Not found'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Detail')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Detail'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Not found');
    });
  });

  it('cancels the sign-off form', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [pendingItem] });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Quote')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Quote'));
    expect(screen.getByPlaceholderText('License number')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Cancel'));
    expect(screen.queryByPlaceholderText('License number')).not.toBeInTheDocument();
  });

  it('filters the queue by search query', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [pendingItem, { ...pendingItem, bundle_id: 'bundle-2', insured_name: 'Beta LLC' }],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    expect(screen.getByText('Beta LLC')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Search insured, broker, bundle id…'), { target: { value: 'beta' } });

    expect(screen.queryByText('Acme Corp')).not.toBeInTheDocument();
    expect(screen.getByText('Beta LLC')).toBeInTheDocument();
  });
});
