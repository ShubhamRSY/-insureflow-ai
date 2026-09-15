import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CommercialInsuranceHub from './CommercialInsurance';

vi.mock('../lib/api', () => ({
  endpoints: {
    commercialInsuranceHub: vi.fn(),
  },
}));

vi.mock('../components/RunSelector', () => ({
  default: () => <div data-testid="run-selector">RunSelector</div>,
}));

vi.mock('../components/SubmissionJobsList', () => ({
  default: ({ jobs, fallbackLine, emptyHint }) => (
    <div data-testid="submission-jobs-list">
      <span data-testid="fallback-line">{fallbackLine}</span>
      <span data-testid="jobs-count">{jobs?.length || 0}</span>
      {emptyHint && <div data-testid="empty-hint">{emptyHint}</div>}
    </div>
  ),
}));

import { endpoints } from '../lib/api';

const mockHubData = {
  title: 'Commercial Insurance',
  summary: 'Upload and underwrite commercial packages.',
  taxonomy: [
    {
      id: 'commercial',
      name: 'Commercial',
      products: [{ id: 'workers_comp', name: 'Workers Comp', slug: 'workers-comp', insurance_line: 'workers_comp', checklist_lob: 'workers_comp', coverages: [] }],
    },
  ],
};

function renderHub(props = {}) {
  return render(
    <MemoryRouter>
      <CommercialInsuranceHub presets={[]} onRunDemo={vi.fn()} onSubmit={vi.fn()} jobs={[]} onDeleteJob={vi.fn()} onDeleteAllJobs={vi.fn()} {...props} />
    </MemoryRouter>
  );
}

describe('CommercialInsuranceHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching hub data', () => {
    endpoints.commercialInsuranceHub.mockReturnValue(new Promise(() => {}));
    const { container } = renderHub();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders hub title and summary after data loads', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Commercial Insurance')).toBeInTheDocument();
    });
  });

  it('shows the Live badge', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Live')).toBeInTheDocument();
    });
  });

  it('renders a link to the commercial reference notebook', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Open reference notebook')).toBeInTheDocument();
    });
    expect(screen.getByText('Open reference notebook')).toHaveAttribute('href', '/reference/commercial');
  });

  it('renders RunSelector and SubmissionJobsList with fallbackLine "Commercial"', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByTestId('run-selector')).toBeInTheDocument();
    });
    expect(screen.getByTestId('fallback-line')).toHaveTextContent('Commercial');
  });

  it('shows an error message when the API call fails', async () => {
    endpoints.commercialInsuranceHub.mockRejectedValue(new Error('Network error'));
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('run-selector')).not.toBeInTheDocument();
  });
});
