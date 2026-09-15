import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PortfolioPage from './Portfolio';

vi.mock('../lib/api', () => ({
  endpoints: {
    portfolioSummary: vi.fn(),
  },
  fmtCurrency: (n) => (n == null || isNaN(n) ? '—' : `$${Number(n).toLocaleString('en-US')}`),
}));

import { endpoints } from '../lib/api';

describe('PortfolioPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching portfolio data', () => {
    endpoints.portfolioSummary.mockReturnValue(new Promise(() => {}));
    const { container } = render(<PortfolioPage />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an error message when the request fails', async () => {
    endpoints.portfolioSummary.mockRejectedValue(new Error('Could not load portfolio'));
    render(<PortfolioPage />);

    await waitFor(() => {
      expect(screen.getByText('Could not load portfolio')).toBeInTheDocument();
    });
  });

  it('shows an empty state when there is no portfolio data yet', async () => {
    endpoints.portfolioSummary.mockResolvedValue(null);
    render(<PortfolioPage />);

    await waitFor(() => {
      expect(screen.getByText('No portfolio data')).toBeInTheDocument();
    });
  });

  it('renders stat cards with policy count and premium totals', async () => {
    endpoints.portfolioSummary.mockResolvedValue({
      total_policies: 42,
      total_premium: 1250000,
      geo_concentration: { score: 55 },
    });
    render(<PortfolioPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Policies')).toBeInTheDocument();
    });
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('$1,250,000')).toBeInTheDocument();
    expect(screen.getByText('55')).toBeInTheDocument();
  });

  it('renders geographic distribution details when present', async () => {
    endpoints.portfolioSummary.mockResolvedValue({
      total_policies: 10,
      total_premium: 100000,
      geo_concentration: { score: 80, details: [{ state: 'CA', count: 6, percentage: 60 }] },
    });
    render(<PortfolioPage />);

    await waitFor(() => {
      expect(screen.getByText('Geographic Distribution')).toBeInTheDocument();
    });
    expect(screen.getByText('CA')).toBeInTheDocument();
    expect(screen.getByText('6 policies · 60.0%')).toBeInTheDocument();
  });

  it('does not render geographic distribution when details are absent', async () => {
    endpoints.portfolioSummary.mockResolvedValue({ total_policies: 10, total_premium: 100000, geo_concentration: { score: 10 } });
    render(<PortfolioPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Policies')).toBeInTheDocument();
    });
    expect(screen.queryByText('Geographic Distribution')).not.toBeInTheDocument();
  });

  it('renders industry distribution details when present', async () => {
    endpoints.portfolioSummary.mockResolvedValue({
      total_policies: 10,
      total_premium: 100000,
      industry_concentration: { details: [{ industry: 'Construction', count: 4, percentage: 40 }] },
    });
    render(<PortfolioPage />);

    await waitFor(() => {
      expect(screen.getByText('Industry Distribution')).toBeInTheDocument();
    });
    expect(screen.getByText('Construction')).toBeInTheDocument();
    expect(screen.getByText('4 policies · 40.0%')).toBeInTheDocument();
  });

  it('reloads portfolio data when Refresh is clicked', async () => {
    endpoints.portfolioSummary.mockResolvedValue({ total_policies: 1, total_premium: 500, geo_concentration: {} });
    render(<PortfolioPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Policies')).toBeInTheDocument();
    });
    expect(endpoints.portfolioSummary).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('Refresh'));
    expect(endpoints.portfolioSummary).toHaveBeenCalledTimes(2);
  });

  it('shows the geo concentration accent switch above the 70 threshold', async () => {
    endpoints.portfolioSummary.mockResolvedValue({ total_policies: 1, total_premium: 500, geo_concentration: { score: 95 } });
    const { container } = render(<PortfolioPage />);

    await waitFor(() => {
      expect(screen.getByText('95')).toBeInTheDocument();
    });
    // accent="success" renders the emerald gradient top-border on the StatCard.
    expect(container.querySelector('.from-emerald-500')).toBeInTheDocument();
  });
});
