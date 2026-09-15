import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import MarketAdmin from './MarketAdmin';

vi.mock('../lib/api', () => ({
  endpoints: {
    marketCycle: vi.fn(),
    setMarketCycle: vi.fn(),
  },
}));

import { endpoints } from '../lib/api';

const cycle = {
  phase: 'hard', description: 'Rates rising, capacity tight',
  property_mod: 1.15, liability_mod: 1.2, workers_comp_mod: 1.05, auto_mod: 1.1,
  appetite_tightness: 'high', reinsurance_cost_mod: 1.3, industry_loss_ratio: 0.68, nuclear_verdict_trend: 'rising',
};

describe('MarketAdmin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching the market cycle', () => {
    endpoints.marketCycle.mockReturnValue(new Promise(() => {}));
    const { container } = render(<MarketAdmin />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state when there is no market data', async () => {
    endpoints.marketCycle.mockResolvedValue(null);
    render(<MarketAdmin />);

    await waitFor(() => {
      expect(screen.getByText('No market data')).toBeInTheDocument();
    });
  });

  it('renders the current phase banner and description', async () => {
    endpoints.marketCycle.mockResolvedValue(cycle);
    render(<MarketAdmin />);

    await waitFor(() => {
      expect(screen.getByText('hard market')).toBeInTheDocument();
    });
    expect(screen.getAllByText('Rates rising, capacity tight').length).toBeGreaterThan(0);
  });

  it('renders rate impact stat cards', async () => {
    endpoints.marketCycle.mockResolvedValue(cycle);
    render(<MarketAdmin />);

    await waitFor(() => {
      expect(screen.getByText('Property')).toBeInTheDocument();
    });
    expect(screen.getByText('1.15')).toBeInTheDocument();
    expect(screen.getByText('Nuclear verdicts rising')).toBeInTheDocument();
  });

  it('renders market metrics', async () => {
    endpoints.marketCycle.mockResolvedValue(cycle);
    render(<MarketAdmin />);

    await waitFor(() => {
      expect(screen.getByText('Appetite Tightness')).toBeInTheDocument();
    });
    expect(screen.getByText('high')).toBeInTheDocument();
    expect(screen.getByText('rising')).toBeInTheDocument();
  });

  it('marks the current phase as Active and disables its button', async () => {
    endpoints.marketCycle.mockResolvedValue(cycle);
    render(<MarketAdmin />);

    await waitFor(() => {
      expect(screen.getByText('Active')).toBeInTheDocument();
    });
    expect(screen.getByText('Hard Market').closest('button')).toBeDisabled();
  });

  it('sets a new market phase', async () => {
    endpoints.marketCycle.mockResolvedValue(cycle);
    endpoints.setMarketCycle.mockResolvedValue({ ok: true });
    render(<MarketAdmin />);

    await waitFor(() => {
      expect(screen.getByText('Soft Market')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Soft Market'));

    await waitFor(() => {
      expect(endpoints.setMarketCycle).toHaveBeenCalledWith('soft');
    });
    await waitFor(() => {
      expect(screen.getByText('Market phase set to Soft Market')).toBeInTheDocument();
    });
  });

  it('shows an error message when setting the phase fails', async () => {
    endpoints.marketCycle.mockResolvedValue(cycle);
    endpoints.setMarketCycle.mockRejectedValue(new Error('Not authorized'));
    render(<MarketAdmin />);

    await waitFor(() => {
      expect(screen.getByText('Soft Market')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Soft Market'));

    await waitFor(() => {
      expect(screen.getByText('Not authorized')).toBeInTheDocument();
    });
  });
});
