import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import OverrideAnalyticsPage from './OverrideAnalytics';

vi.mock('../lib/api', () => ({
  endpoints: {
    overrideAnalytics: vi.fn(),
    overridePatterns: vi.fn(),
  },
}));

import { endpoints } from '../lib/api';

function setupEmpty() {
  endpoints.overrideAnalytics.mockResolvedValue({ overrides: [] });
  endpoints.overridePatterns.mockResolvedValue({ patterns: [] });
}

describe('OverrideAnalyticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching data', () => {
    endpoints.overrideAnalytics.mockReturnValue(new Promise(() => {}));
    endpoints.overridePatterns.mockReturnValue(new Promise(() => {}));
    const { container } = render(<OverrideAnalyticsPage />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state when there are no overrides', async () => {
    setupEmpty();
    render(<OverrideAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText('No overrides recorded')).toBeInTheDocument();
    });
  });

  it('renders an override history row', async () => {
    endpoints.overrideAnalytics.mockResolvedValue({ overrides: [{ bundle_id: 'bundle-1', override_reason_category: 'pricing', override_reason: 'Competitive quote', decision: 'quote' }] });
    endpoints.overridePatterns.mockResolvedValue({ patterns: [] });
    render(<OverrideAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText('bundle-1')).toBeInTheDocument();
    });
    expect(screen.getByText('Competitive quote')).toBeInTheDocument();
  });

  it('renders detected patterns when present', async () => {
    endpoints.overrideAnalytics.mockResolvedValue({ overrides: [] });
    endpoints.overridePatterns.mockResolvedValue({ patterns: [{ pattern_name: 'Frequent pricing overrides', description: 'UW consistently overrides AI pricing', frequency: 12 }] });
    render(<OverrideAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText('Detected Patterns')).toBeInTheDocument();
    });
    expect(screen.getByText('Frequent pricing overrides')).toBeInTheDocument();
    expect(screen.getByText('Frequency: 12')).toBeInTheDocument();
  });

  it('does not render the patterns section when there are none', async () => {
    setupEmpty();
    render(<OverrideAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText('No overrides recorded')).toBeInTheDocument();
    });
    expect(screen.queryByText('Detected Patterns')).not.toBeInTheDocument();
  });

  it('shows an error message when the parallel loads both fail', async () => {
    endpoints.overrideAnalytics.mockImplementation(() => { throw new Error('boom'); });
    endpoints.overridePatterns.mockResolvedValue({ patterns: [] });
    render(<OverrideAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText('boom')).toBeInTheDocument();
    });
  });

  it('reloads when Refresh is clicked', async () => {
    setupEmpty();
    render(<OverrideAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText('No overrides recorded')).toBeInTheDocument();
    });
    expect(endpoints.overrideAnalytics).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('Refresh'));
    expect(endpoints.overrideAnalytics).toHaveBeenCalledTimes(2);
  });
});
