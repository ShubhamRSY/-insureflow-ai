import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import BusinessKPIsPage from './BusinessKPIs';

vi.mock('../lib/api', () => ({
  endpoints: {
    businessKpis: vi.fn(),
    billingUsage: vi.fn(),
    bootstrapBusinessKpis: vi.fn(),
  },
}));

import { endpoints } from '../lib/api';

const report = {
  overall: 'lab_partial',
  production_ready_count: 2,
  total_kpis: 7,
  measured_count: 3,
  generated_at: '2026-01-01T00:00:00Z',
  org_id: 'org-1',
  kpis: {
    roi: { status: 'production_ready', value: 42.5, unit: 'percent', sample_size: 10, what_to_say: 'Strong ROI', target: { label: 'Target 20%+' }, pass: true },
    cycle_time: { status: 'lab_partial', value: 300, unit: 'seconds_avg', sample_size: 5, p95_seconds: 400, min_seconds: 100, p50_seconds: 250, max_seconds: 500, what_to_say: 'Fast cycle' },
  },
};

describe('BusinessKPIsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching KPIs', () => {
    endpoints.businessKpis.mockReturnValue(new Promise(() => {}));
    endpoints.billingUsage.mockReturnValue(new Promise(() => {}));
    const { container } = render(<BusinessKPIsPage />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state when there is no report', async () => {
    endpoints.businessKpis.mockResolvedValue(null);
    endpoints.billingUsage.mockResolvedValue(null);
    render(<BusinessKPIsPage />);

    await waitFor(() => {
      expect(screen.getByText('No KPI report')).toBeInTheDocument();
    });
  });

  it('renders the overall status stat card', async () => {
    endpoints.businessKpis.mockResolvedValue(report);
    endpoints.billingUsage.mockResolvedValue(null);
    render(<BusinessKPIsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('lab partial').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('2/7 production-ready')).toBeInTheDocument();
  });

  it('renders a KPI card with its formatted value', async () => {
    endpoints.businessKpis.mockResolvedValue(report);
    endpoints.billingUsage.mockResolvedValue(null);
    render(<BusinessKPIsPage />);

    await waitFor(() => {
      expect(screen.getByText('ROI')).toBeInTheDocument();
    });
    expect(screen.getByText('42.5%')).toBeInTheDocument();
    expect(screen.getByText('Strong ROI')).toBeInTheDocument();
  });

  it('renders cycle time detail fields for the cycle_time KPI', async () => {
    endpoints.businessKpis.mockResolvedValue(report);
    endpoints.billingUsage.mockResolvedValue(null);
    render(<BusinessKPIsPage />);

    await waitFor(() => {
      expect(screen.getByText('Cycle time')).toBeInTheDocument();
    });
    expect(screen.getByText(/min 100s · p50 250s · max 500s/)).toBeInTheDocument();
  });

  it('bootstraps from labeled scenarios', async () => {
    endpoints.businessKpis.mockResolvedValue(report);
    endpoints.billingUsage.mockResolvedValue(null);
    endpoints.bootstrapBusinessKpis.mockResolvedValue({ ...report, bootstrap: { scenarios_passed: 8, scenarios_run: 10, note: 'Looks good' } });
    render(<BusinessKPIsPage />);

    await waitFor(() => {
      expect(screen.getByText('Bootstrap from labeled scenarios')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Bootstrap from labeled scenarios'));

    await waitFor(() => {
      expect(screen.getByText(/Bootstrapped 8\/10 labeled scenarios/)).toBeInTheDocument();
    });
  });

  it('shows an error message when bootstrap fails', async () => {
    endpoints.businessKpis.mockResolvedValue(report);
    endpoints.billingUsage.mockResolvedValue(null);
    endpoints.bootstrapBusinessKpis.mockRejectedValue(new Error('Scenario run failed'));
    render(<BusinessKPIsPage />);

    await waitFor(() => {
      expect(screen.getByText('Bootstrap from labeled scenarios')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Bootstrap from labeled scenarios'));

    await waitFor(() => {
      expect(screen.getByText('Scenario run failed')).toBeInTheDocument();
    });
  });

  it('renders the plan and LLM usage panel when present', async () => {
    endpoints.businessKpis.mockResolvedValue(report);
    endpoints.billingUsage.mockResolvedValue({ plan_id: 'pilot', session: { total_cost: 1.5, request_count: 4 } });
    render(<BusinessKPIsPage />);

    await waitFor(() => {
      expect(screen.getByText('Plan & LLM usage')).toBeInTheDocument();
    });
    expect(screen.getByText('pilot')).toBeInTheDocument();
    expect(screen.getByText(/4 LLM calls/)).toBeInTheDocument();
  });
});
