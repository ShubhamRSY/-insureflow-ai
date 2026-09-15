import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import EvalTrendsPage from './EvalTrends';

vi.mock('../lib/api', () => ({
  endpoints: {
    evalTrends: vi.fn(),
    logExplorers: vi.fn(),
  },
}));

vi.mock('recharts', () => ({
  LineChart: ({ children }) => <div>{children}</div>,
  Line: () => null,
  BarChart: ({ children }) => <div>{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Legend: () => null,
  CartesianGrid: () => null,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
}));

import { endpoints } from '../lib/api';

const trendData = {
  points: 5,
  agent_snapshot: { avg_error_rate: 0.02, avg_latency_ms: 1200, agents: { uw_agent: { error_rate: 0.01, avg_duration_ms: 900, findings: 3 } } },
  series: {
    precision: [{ ts: '2026-01-01', value: 0.9 }],
    recall: [{ ts: '2026-01-01', value: 0.85 }],
    hallucination_rate: [{ ts: '2026-01-01', value: 0.02 }],
    ragas_quality_score: [{ ts: '2026-01-01', value: 0.88 }],
  },
};

describe('EvalTrendsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching trend data', () => {
    endpoints.evalTrends.mockReturnValue(new Promise(() => {}));
    endpoints.logExplorers.mockReturnValue(new Promise(() => {}));
    const { container } = render(<EvalTrendsPage />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state when there are no trend points', async () => {
    endpoints.evalTrends.mockResolvedValue({ points: 0 });
    endpoints.logExplorers.mockResolvedValue(null);
    render(<EvalTrendsPage />);

    await waitFor(() => {
      expect(screen.getByText('No trend points yet')).toBeInTheDocument();
    });
  });

  it('renders trend stat cards', async () => {
    endpoints.evalTrends.mockResolvedValue(trendData);
    endpoints.logExplorers.mockResolvedValue(null);
    render(<EvalTrendsPage />);

    await waitFor(() => {
      expect(screen.getByText('Trend points')).toBeInTheDocument();
    });
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('2.00%')).toBeInTheDocument();
    expect(screen.getByText('1200 ms')).toBeInTheDocument();
  });

  it('does not render the benchmark section when there is no benchmark data', async () => {
    endpoints.evalTrends.mockResolvedValue(trendData);
    endpoints.logExplorers.mockResolvedValue(null);
    render(<EvalTrendsPage />);

    await waitFor(() => {
      expect(screen.getByText('Trend points')).toBeInTheDocument();
    });
    expect(screen.queryByText(/Performance & price benchmark/)).not.toBeInTheDocument();
  });

  it('renders the benchmark section when benchmark series are present', async () => {
    endpoints.evalTrends.mockResolvedValue({
      ...trendData,
      series: { ...trendData.series, time_to_first_token_s: [{ ts: '2026-01-01', value: 0.45 }] },
    });
    endpoints.logExplorers.mockResolvedValue(null);
    render(<EvalTrendsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Performance & price benchmark/)).toBeInTheDocument();
    });
    expect(screen.getByText('0.45')).toBeInTheDocument();
  });

  it('renders log explorer links when present', async () => {
    endpoints.evalTrends.mockResolvedValue(trendData);
    endpoints.logExplorers.mockResolvedValue({
      automation: 'Nightly CloudWatch Insights run',
      explorers: [{ name: 'Agent errors', url: 'https://example.com/explorer', role: 'Error triage' }],
    });
    render(<EvalTrendsPage />);

    await waitFor(() => {
      expect(screen.getByText('Log explorers')).toBeInTheDocument();
    });
    expect(screen.getByText('Agent errors')).toBeInTheDocument();
    expect(screen.getByText('Agent errors').closest('a')).toHaveAttribute('href', 'https://example.com/explorer');
  });
});
