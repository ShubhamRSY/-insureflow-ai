import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import RenewalDashboard from './RenewalDashboard';

vi.mock('../lib/api', () => ({
  endpoints: {
    premiumAudits: vi.fn(),
    materialAdjustments: vi.fn(),
    createPremiumAudit: vi.fn(),
    completePremiumAudit: vi.fn(),
  },
  fmtCurrency: (n) => (n == null || isNaN(n) ? '—' : `$${Number(n).toLocaleString('en-US')}`),
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const audit = {
  audit_id: 'audit-1', bundle_id: 'bundle-1', policy_number: 'POL-1',
  estimated_premium: 10000, actual_premium: 11000, premium_delta: 1000,
  status: 'in_progress', adjustments: [],
};

function setupEmpty() {
  endpoints.premiumAudits.mockResolvedValue({ audits: [] });
  endpoints.materialAdjustments.mockResolvedValue({ adjustments: [] });
}

describe('RenewalDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching audits', () => {
    endpoints.premiumAudits.mockReturnValue(new Promise(() => {}));
    endpoints.materialAdjustments.mockReturnValue(new Promise(() => {}));
    const { container } = render(<RenewalDashboard />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state when there are no audits', async () => {
    setupEmpty();
    render(<RenewalDashboard />);

    await waitFor(() => {
      expect(screen.getByText('No audits yet')).toBeInTheDocument();
    });
  });

  it('renders an audit row with its delta percentage', async () => {
    endpoints.premiumAudits.mockResolvedValue({ audits: [audit] });
    endpoints.materialAdjustments.mockResolvedValue({ adjustments: [] });
    render(<RenewalDashboard />);

    await waitFor(() => {
      expect(screen.getByText('bundle-1')).toBeInTheDocument();
    });
    expect(screen.getByText('POL-1')).toBeInTheDocument();
    expect(screen.getByText('+10.0%')).toBeInTheDocument();
  });

  it('renders total/pending/completed stat cards', async () => {
    endpoints.premiumAudits.mockResolvedValue({ audits: [audit, { ...audit, audit_id: 'audit-2', status: 'completed' }] });
    endpoints.materialAdjustments.mockResolvedValue({ adjustments: [] });
    render(<RenewalDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Total Audits')).toBeInTheDocument();
    });
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('creates a new premium audit', async () => {
    setupEmpty();
    endpoints.createPremiumAudit.mockResolvedValue({ ok: true });
    render(<RenewalDashboard />);

    await waitFor(() => {
      expect(screen.getByText('No audits yet')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Create Audit'));

    fireEvent.change(document.querySelector('input[required]'), { target: { value: 'bundle-9' } });
    const numberInput = document.querySelector('input[type="number"][required]');
    fireEvent.change(numberInput, { target: { value: '5000' } });
    fireEvent.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(endpoints.createPremiumAudit).toHaveBeenCalledWith('bundle-9', 5000, expect.objectContaining({ policy_number: '' }));
    });
  });

  it('shows a toast error when creating an audit fails', async () => {
    setupEmpty();
    endpoints.createPremiumAudit.mockRejectedValue(new Error('Bundle not found'));
    render(<RenewalDashboard />);

    await waitFor(() => {
      expect(screen.getByText('No audits yet')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Create Audit'));
    fireEvent.change(document.querySelector('input[required]'), { target: { value: 'bad-bundle' } });
    fireEvent.change(document.querySelector('input[type="number"][required]'), { target: { value: '1000' } });
    fireEvent.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Bundle not found');
    });
  });

  it('completes an in-progress audit', async () => {
    endpoints.premiumAudits.mockResolvedValue({ audits: [audit] });
    endpoints.materialAdjustments.mockResolvedValue({ adjustments: [] });
    endpoints.completePremiumAudit.mockResolvedValue({ ok: true });
    render(<RenewalDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Complete')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Complete'));
    expect(screen.getByText('Complete Audit')).toBeInTheDocument();

    fireEvent.change(document.querySelector('input[type="number"][required]'), { target: { value: '12000' } });
    fireEvent.click(screen.getByText('Complete', { selector: 'button[type="submit"]' }));

    await waitFor(() => {
      expect(endpoints.completePremiumAudit).toHaveBeenCalledWith('audit-1', 12000, '');
    });
  });

  it('does not show a Complete button for a completed audit', async () => {
    endpoints.premiumAudits.mockResolvedValue({ audits: [{ ...audit, status: 'completed' }] });
    endpoints.materialAdjustments.mockResolvedValue({ adjustments: [] });
    render(<RenewalDashboard />);

    await waitFor(() => {
      expect(screen.getByText('bundle-1')).toBeInTheDocument();
    });
    expect(screen.queryByText('Complete')).not.toBeInTheDocument();
  });

  it('renders material adjustments pending review', async () => {
    setupEmpty();
    endpoints.materialAdjustments.mockResolvedValue({ adjustments: [{ audit_id: 'audit-3', reason: 'Payroll increase', amount: 500 }] });
    render(<RenewalDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Material Adjustments Pending Review')).toBeInTheDocument();
    });
    expect(screen.getByText(/audit-3 — Payroll increase/)).toBeInTheDocument();
    expect(screen.getByText('+$500')).toBeInTheDocument();
  });

  it('reloads audits when Refresh is clicked', async () => {
    setupEmpty();
    render(<RenewalDashboard />);

    await waitFor(() => {
      expect(screen.getByText('No audits yet')).toBeInTheDocument();
    });
    expect(endpoints.premiumAudits).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('Refresh'));
    expect(endpoints.premiumAudits).toHaveBeenCalledTimes(2);
  });
});
