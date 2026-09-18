import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useOutletContext } from 'react-router-dom';
import MonitoringPage from './Monitoring';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useOutletContext: vi.fn() };
});

vi.mock('../lib/api', () => ({
  endpoints: {
    monitoringPolicies: vi.fn(),
    monitoringAlerts: vi.fn(),
    monitoringEvaluate: vi.fn(),
    monitoringPolicy: vi.fn(),
    addMonitoringItem: vi.fn(),
    resolveMonitoringItem: vi.fn(),
    recordLossDevelopment: vi.fn(),
  },
  fmtCurrency: (n) => (n == null || isNaN(n) ? '—' : `$${Number(n).toLocaleString('en-US')}`),
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const policy = {
  policy_id: 'pol-1', insured_name: 'Acme Corp', status: 'active', policy_number: 'POL-1',
  line_of_business: 'General Liability', days_to_expiry: 200, latest_loss_ratio: 0.5,
  open_alert_count: 0, open_item_count: 1, premium: 10000,
};

const policyRecord = {
  effective_date: '2026-01-01', expiry_date: '2027-01-01', premium: 10000, tiv: 500000, bundle_id: 'bundle-1',
  items: [{ item_id: 'item-1', title: 'Roof inspection', description: 'Verify roof age', severity: 'moderate', source: 'manual', status: 'open' }],
  loss_development: [],
  alerts: [],
  latest_loss_ratio: 0.5,
};

function setupEmpty() {
  endpoints.monitoringPolicies.mockResolvedValue({ policies: [] });
  endpoints.monitoringAlerts.mockResolvedValue({ alerts: [] });
}

function renderPage() {
  useOutletContext.mockReturnValue({ user: { username: 'jdoe' } });
  return render(<MonitoringPage />);
}

describe('MonitoringPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching monitoring data', () => {
    endpoints.monitoringPolicies.mockReturnValue(new Promise(() => {}));
    endpoints.monitoringAlerts.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state when there are no monitored policies', async () => {
    setupEmpty();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No policies under monitoring')).toBeInTheDocument();
    });
  });

  it('renders a policy row with its status and loss ratio', async () => {
    endpoints.monitoringPolicies.mockResolvedValue({ policies: [policy] });
    endpoints.monitoringAlerts.mockResolvedValue({ alerts: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    expect(screen.getByText('POL-1')).toBeInTheDocument();
    expect(screen.getAllByText('50%').length).toBeGreaterThan(0);
  });

  it('renders a raw snake_case line of business as a readable label', async () => {
    endpoints.monitoringPolicies.mockResolvedValue({ policies: [{ ...policy, line_of_business: 'general_liability' }] });
    endpoints.monitoringAlerts.mockResolvedValue({ alerts: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    expect(screen.getByText(/General Liability/)).toBeInTheDocument();
  });

  it('renders open monitoring alerts', async () => {
    endpoints.monitoringPolicies.mockResolvedValue({ policies: [] });
    endpoints.monitoringAlerts.mockResolvedValue({
      alerts: [{ alert_id: 'a1', title: 'Loss ratio spike', severity: 'high', policy_id: 'pol-1', resolved: false }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Open monitoring alerts')).toBeInTheDocument();
    });
    expect(screen.getByText('Loss ratio spike')).toBeInTheDocument();
  });

  it('expands a policy and loads its detail', async () => {
    endpoints.monitoringPolicies.mockResolvedValue({ policies: [policy] });
    endpoints.monitoringAlerts.mockResolvedValue({ alerts: [] });
    endpoints.monitoringPolicy.mockResolvedValue(policyRecord);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Acme Corp'));

    await waitFor(() => {
      expect(endpoints.monitoringPolicy).toHaveBeenCalledWith('pol-1');
    });
    await waitFor(() => {
      expect(screen.getByText('Roof inspection')).toBeInTheDocument();
    });
  });

  it('adds a monitoring item to an expanded policy', async () => {
    endpoints.monitoringPolicies.mockResolvedValue({ policies: [policy] });
    endpoints.monitoringAlerts.mockResolvedValue({ alerts: [] });
    endpoints.monitoringPolicy.mockResolvedValue(policyRecord);
    endpoints.addMonitoringItem.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Acme Corp'));

    await waitFor(() => {
      expect(screen.getByText('Add item')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Add item'));
    fireEvent.change(screen.getByPlaceholderText(/roof age verified/), { target: { value: 'New item' } });
    fireEvent.click(screen.getByText('Add item', { selector: 'button[type="submit"]' }));

    await waitFor(() => {
      expect(endpoints.addMonitoringItem).toHaveBeenCalledWith('pol-1', expect.objectContaining({ title: 'New item' }));
    });
  });

  it('resolves an item as cleared', async () => {
    endpoints.monitoringPolicies.mockResolvedValue({ policies: [policy] });
    endpoints.monitoringAlerts.mockResolvedValue({ alerts: [] });
    endpoints.monitoringPolicy.mockResolvedValue(policyRecord);
    endpoints.resolveMonitoringItem.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Acme Corp'));

    await waitFor(() => {
      expect(screen.getByText('Cleared')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Cleared'));

    await waitFor(() => {
      expect(endpoints.resolveMonitoringItem).toHaveBeenCalledWith('pol-1', 'item-1', expect.objectContaining({ status: 'cleared' }));
    });
  });

  it('records loss development for a policy', async () => {
    endpoints.monitoringPolicies.mockResolvedValue({ policies: [policy] });
    endpoints.monitoringAlerts.mockResolvedValue({ alerts: [] });
    endpoints.monitoringPolicy.mockResolvedValue(policyRecord);
    endpoints.recordLossDevelopment.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Acme Corp'));

    await waitFor(() => {
      expect(screen.getByText('Record')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Record'));
    fireEvent.change(screen.getByPlaceholderText('Earned premium'), { target: { value: '10000' } });
    fireEvent.change(screen.getByPlaceholderText('Incurred losses'), { target: { value: '5000' } });
    fireEvent.click(screen.getByText('Record', { selector: 'button[type="submit"]' }));

    await waitFor(() => {
      expect(endpoints.recordLossDevelopment).toHaveBeenCalledWith('pol-1', expect.objectContaining({ earned_premium: 10000, incurred_losses: 5000 }));
    });
  });

  it('runs an evaluation and refreshes policies/alerts', async () => {
    setupEmpty();
    endpoints.monitoringEvaluate.mockResolvedValue({ policies: [policy], alerts: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No policies under monitoring')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Run evaluation'));

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
  });

  it('shows a toast error when evaluation fails', async () => {
    setupEmpty();
    endpoints.monitoringEvaluate.mockRejectedValue(new Error('Evaluation failed'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No policies under monitoring')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Run evaluation'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Evaluation failed');
    });
  });
});
