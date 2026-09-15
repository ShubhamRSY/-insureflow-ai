import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import RatemakingPage from './Ratemaking';

vi.mock('../lib/api', () => ({
  endpoints: {
    ratemaking: vi.fn(),
    ratemakingRun: vi.fn(),
  },
  fmtCurrency: (n) => (n == null || isNaN(n) ? '—' : `$${Number(n).toLocaleString('en-US')}`),
}));

import { endpoints } from '../lib/api';

const overview = {
  line_build_ups: [{ line: 'general_liability', pure_premium: 100, base_rate: 150, gross_rate: 165 }],
  advisory_organizations: ['ISO', 'NCCI'],
  reserve_analysis: {
    payout_pattern: { reserve_redundancy_pct: 0, valuations: [] },
    filing_schedule: { total_lag_years: 2, stages: [] },
    data_delays: [],
  },
  investment_income: [],
  expense_analysis: { projections: [], allocations: [] },
  factors: [],
  states_requiring_explicit_investment_income: ['CA', 'NY'],
};

const study = {
  summary: 'Indicated rate change: +4.2%',
  pure_premium_result: { pure_premium: 1000, expense_loading: 200, base_rate: 1200, gross_rate: 1350, contingency_loading: 60, profit_loading: 60 },
  loss_ratio_result: { indicated_rate: 1250, rate_change_pct: 4.2 },
  judgment_result: { judgment_rate: 1300 },
  regulatory: [{ goal: 'not_excessive', status: 'pass', detail: 'Within bounds' }],
  characteristics: [{ characteristic: 'stability', status: 'pass' }],
};

function setupSuccess() {
  endpoints.ratemaking.mockResolvedValue(overview);
  endpoints.ratemakingRun.mockResolvedValue(study);
}

describe('RatemakingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching data', () => {
    endpoints.ratemaking.mockReturnValue(new Promise(() => {}));
    endpoints.ratemakingRun.mockReturnValue(new Promise(() => {}));
    const { container } = render(<RatemakingPage />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an error message when loading fails', async () => {
    endpoints.ratemaking.mockRejectedValue(new Error('Ratemaking service unavailable'));
    endpoints.ratemakingRun.mockResolvedValue(study);
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('Ratemaking service unavailable')).toBeInTheDocument();
    });
  });

  it('shows an empty state when no study is returned', async () => {
    endpoints.ratemaking.mockResolvedValue(overview);
    endpoints.ratemakingRun.mockResolvedValue(null);
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('No ratemaking data')).toBeInTheDocument();
    });
  });

  it('renders the study summary and pure-premium stat cards', async () => {
    setupSuccess();
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('Indicated rate change: +4.2%')).toBeInTheDocument();
    });
    expect(screen.getByText('Pure Premium')).toBeInTheDocument();
    expect(screen.getByText('$1,000')).toBeInTheDocument();
    expect(screen.getByText('Base Rate')).toBeInTheDocument();
    expect(screen.getAllByText('$1,200').length).toBeGreaterThan(0);
  });

  it('renders the three ratemaking methods with their computed values', async () => {
    setupSuccess();
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('Pure premium')).toBeInTheDocument();
    });
    expect(screen.getByText('Loss ratio')).toBeInTheDocument();
    expect(screen.getByText('Judgment')).toBeInTheDocument();
    expect(screen.getByText('$1,300')).toBeInTheDocument();
  });

  it('renders regulatory goals and rate characteristics', async () => {
    setupSuccess();
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('not excessive')).toBeInTheDocument();
    });
    expect(screen.getByText('Within bounds')).toBeInTheDocument();
    expect(screen.getByText('stability')).toBeInTheDocument();
  });

  it('renders per-line base rates and advisory organizations', async () => {
    setupSuccess();
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('general_liability')).toBeInTheDocument();
    });
    expect(screen.getByText('ISO')).toBeInTheDocument();
    expect(screen.getByText('NCCI')).toBeInTheDocument();
  });

  it('reruns ratemaking when the line selector changes', async () => {
    setupSuccess();
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('Pure Premium')).toBeInTheDocument();
    });
    expect(endpoints.ratemakingRun).toHaveBeenCalledWith(expect.objectContaining({ line: 'commercial_property' }));

    fireEvent.change(screen.getByDisplayValue('commercial_property'), { target: { value: 'workers_comp' } });

    await waitFor(() => {
      expect(endpoints.ratemakingRun).toHaveBeenLastCalledWith(expect.objectContaining({ line: 'workers_comp' }));
    });
  });

  it('recalculates the rate from the build-a-rate form', async () => {
    setupSuccess();
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('Recalculate rate')).toBeInTheDocument();
    });
    endpoints.ratemakingRun.mockClear();

    fireEvent.click(screen.getByText('Recalculate rate'));

    await waitFor(() => {
      expect(endpoints.ratemakingRun).toHaveBeenCalledWith(
        expect.objectContaining({ incurred_losses: 10000000, exposure_units: 100000 })
      );
    });
  });

  it('shows an error when recalculating the rate fails', async () => {
    setupSuccess();
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('Recalculate rate')).toBeInTheDocument();
    });
    endpoints.ratemakingRun.mockRejectedValueOnce(new Error('Invalid inputs'));

    fireEvent.click(screen.getByText('Recalculate rate'));

    await waitFor(() => {
      expect(screen.getByText('Invalid inputs')).toBeInTheDocument();
    });
  });

  it('reloads data when Refresh is clicked', async () => {
    setupSuccess();
    render(<RatemakingPage />);

    await waitFor(() => {
      expect(screen.getByText('Pure Premium')).toBeInTheDocument();
    });
    endpoints.ratemaking.mockClear();

    fireEvent.click(screen.getByText('Refresh'));

    await waitFor(() => {
      expect(endpoints.ratemaking).toHaveBeenCalled();
    });
  });
});
