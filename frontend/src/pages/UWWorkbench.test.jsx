import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import UWWorkbench from './UWWorkbench';

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual('../lib/api');
  return {
    ...actual,
    endpoints: {
      uwWorkbench: vi.fn(),
      signOff: vi.fn(),
      bindReadiness: vi.fn(),
      bindPolicy: vi.fn(),
      resolveCheckpoint: vi.fn(),
    },
  };
});

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

vi.mock('../components/BindReadinessPanel', () => ({
  default: ({ bundleId }) => <div data-testid="bind-readiness-panel">BindReadinessPanel:{bundleId}</div>,
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const pendingCase = {
  bundle_id: 'bundle-1',
  insured_name: 'Acme Corp',
  state: 'pending_review',
  insurance_line: 'general_liability',
  premium: 12500,
  ai_decision: 'accept',
  human_review_required: false,
  checkpoints: [],
};

const approvedCase = {
  bundle_id: 'bundle-2',
  insured_name: 'Beta LLC',
  state: 'approved',
  insurance_line: 'workers_comp',
  premium: 8000,
  ai_decision: 'accept',
  checkpoints: [],
};

function renderWorkbench(props = {}) {
  return render(
    <MemoryRouter>
      <UWWorkbench {...props} />
    </MemoryRouter>
  );
}

describe('UWWorkbench', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching the workbench', () => {
    endpoints.uwWorkbench.mockReturnValue(new Promise(() => {}));
    const { container } = renderWorkbench();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an error message when the workbench fails to load', async () => {
    endpoints.uwWorkbench.mockRejectedValue(new Error('Server error'));
    renderWorkbench();
    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument();
    });
  });

  it('renders stat totals and an empty inbox state', async () => {
    endpoints.uwWorkbench.mockResolvedValue({ pending: [], approved: [], done: [], totals: { pending: 0, approved: 0, co_sign: 0, done: 0 } });
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByText('Inbox clear')).toBeInTheDocument();
    });
    expect(screen.getByText('Awaiting UW')).toBeInTheDocument();
  });

  it('renders a pending case card with its details', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [pendingCase], approved: [], done: [], totals: { pending: 1, approved: 0, co_sign: 0, done: 0 },
    });
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByText('bundle-1')).toBeInTheDocument();
    });
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('$12,500')).toBeInTheDocument();
  });

  it('switches to the "Ready to bind" tab and shows approved cases', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [], approved: [approvedCase], done: [], totals: { pending: 0, approved: 1, co_sign: 0, done: 0 },
    });
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ready to bind/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /ready to bind/i }));

    expect(screen.getByText('bundle-2')).toBeInTheDocument();
    expect(screen.getByText('Beta LLC')).toBeInTheDocument();
    expect(screen.getByTestId('bind-readiness-panel')).toHaveTextContent('bundle-2');
  });

  it('opens the sign-off form for Quote and submits it', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [pendingCase], approved: [], done: [], totals: { pending: 1, approved: 0, co_sign: 0, done: 0 },
    });
    endpoints.signOff.mockResolvedValue({ ok: true });
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByText('Quote')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Quote'));

    expect(screen.getByPlaceholderText('License number')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Confirm quote'));

    await waitFor(() => {
      expect(endpoints.signOff).toHaveBeenCalledWith('bundle-1', expect.objectContaining({ action: 'quote' }));
    });
  });

  it('shows a toast error when sign-off fails', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [pendingCase], approved: [], done: [], totals: { pending: 1, approved: 0, co_sign: 0, done: 0 },
    });
    endpoints.signOff.mockRejectedValue(new Error('Missing license number'));
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByText('Quote')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Quote'));
    fireEvent.click(screen.getByText('Confirm quote'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Missing license number');
    });
  });

  it('cancels bind when readiness checks are not clear', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [], approved: [approvedCase], done: [], totals: { pending: 0, approved: 1, co_sign: 0, done: 0 },
    });
    endpoints.bindReadiness.mockResolvedValue({ bind_readiness: { ready_to_bind: false, summary: 'Open subjectivities remain' } });
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ready to bind/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /ready to bind/i }));

    await waitFor(() => {
      expect(screen.getByText('Bind policy')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Bind policy'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Open subjectivities remain');
    });
    expect(endpoints.bindPolicy).not.toHaveBeenCalled();
  });

  it('binds the policy after readiness passes and confirm is accepted', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [], approved: [approvedCase], done: [], totals: { pending: 0, approved: 1, co_sign: 0, done: 0 },
    });
    endpoints.bindReadiness.mockResolvedValue({ bind_readiness: { ready_to_bind: true } });
    endpoints.bindPolicy.mockResolvedValue({ ok: true });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ready to bind/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /ready to bind/i }));

    await waitFor(() => {
      expect(screen.getByText('Bind policy')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Bind policy'));

    await waitFor(() => {
      expect(endpoints.bindPolicy).toHaveBeenCalledWith('bundle-2');
    });
  });

  it('does not bind when the confirm dialog is dismissed', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [], approved: [approvedCase], done: [], totals: { pending: 0, approved: 1, co_sign: 0, done: 0 },
    });
    endpoints.bindReadiness.mockResolvedValue({ bind_readiness: { ready_to_bind: true } });
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ready to bind/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /ready to bind/i }));

    await waitFor(() => {
      expect(screen.getByText('Bind policy')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Bind policy'));

    await waitFor(() => {
      expect(endpoints.bindReadiness).toHaveBeenCalled();
    });
    expect(endpoints.bindPolicy).not.toHaveBeenCalled();
  });

  it('resolves a pending checkpoint', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [{ ...pendingCase, checkpoints: [{ id: 'oracle_review', status: 'pending' }] }],
      approved: [], done: [], totals: { pending: 1, approved: 0, co_sign: 0, done: 0 },
    });
    endpoints.resolveCheckpoint.mockResolvedValue({ ok: true });
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByText('Approve')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Approve'));

    await waitFor(() => {
      expect(endpoints.resolveCheckpoint).toHaveBeenCalledWith('bundle-1', 'oracle_review', 'approve');
    });
  });

  it('shows a Co-sign button for cases pending co-sign', async () => {
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [{ ...pendingCase, state: 'pending_co_sign' }], approved: [], done: [],
      totals: { pending: 1, approved: 0, co_sign: 1, done: 0 },
    });
    renderWorkbench();

    await waitFor(() => {
      expect(screen.getByText('Co-sign')).toBeInTheDocument();
    });
    expect(screen.getByText('Needs co-sign')).toBeInTheDocument();
    expect(screen.getByText('Co-sign required')).toBeInTheDocument();
  });

  it('calls onOpenJob when View is clicked', async () => {
    const onOpenJob = vi.fn();
    endpoints.uwWorkbench.mockResolvedValue({
      pending: [pendingCase], approved: [], done: [], totals: { pending: 1, approved: 0, co_sign: 0, done: 0 },
    });
    renderWorkbench({ onOpenJob });

    await waitFor(() => {
      expect(screen.getByText('View')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('View'));
    expect(onOpenJob).toHaveBeenCalledWith('insurance', 'bundle-1', 'bundle-1');
  });
});
