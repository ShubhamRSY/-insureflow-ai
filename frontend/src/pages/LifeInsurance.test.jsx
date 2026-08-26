import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LifeInsuranceHub from './LifeInsurance';

vi.mock('../lib/api', () => ({
  endpoints: {
    lifeInsuranceHub: vi.fn(),
  },
}));

vi.mock('../components/RunSelector', () => ({
  default: (props) => (
    <div data-testid="run-selector" data-guided={String(!!props.guidedFlow)}>
      RunSelector
    </div>
  ),
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
  title: 'Life Insurance',
  summary: 'Upload and underwrite life insurance packages.',
  taxonomy: [
    {
      id: 'life',
      name: 'Life',
      products: [
        {
          id: 'level_term',
          name: 'Level Term Life',
          slug: 'level-term',
          insurance_line: 'term_life',
          checklist_lob: 'term_life',
          coverages: [{ id: '50k', name: '$50,000' }],
        },
      ],
    },
  ],
};

function renderHub(props = {}) {
  return render(
    <MemoryRouter>
      <LifeInsuranceHub
        presets={[]}
        onRunDemo={vi.fn()}
        onSubmit={vi.fn()}
        jobs={[]}
        onDeleteJob={vi.fn()}
        onDeleteAllJobs={vi.fn()}
        {...props}
      />
    </MemoryRouter>
  );
}

describe('LifeInsuranceHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching hub data', () => {
    endpoints.lifeInsuranceHub.mockReturnValue(new Promise(() => {}));
    const { container } = renderHub();

    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders hub title and summary after data loads', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Life Insurance')).toBeInTheDocument();
    });
    expect(screen.getByText('Upload and underwrite life insurance packages.')).toBeInTheDocument();
  });

  it('shows the Live badge', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Live')).toBeInTheDocument();
    });
  });

  it('renders the PageBack link to /insurance', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('All insurance')).toBeInTheDocument();
    });
  });

  it('renders RunSelector with guidedFlow prop', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByTestId('run-selector')).toBeInTheDocument();
    });
    expect(screen.getByTestId('run-selector')).toHaveAttribute('data-guided', 'true');
  });

  it('renders SubmissionJobsList with fallbackLine "Life"', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByTestId('submission-jobs-list')).toBeInTheDocument();
    });
    expect(screen.getByTestId('fallback-line')).toHaveTextContent('Life');
  });

  it('passes jobs prop to SubmissionJobsList', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    const jobs = [{ id: '1', job: { name: 'Test Job' } }];
    renderHub({ jobs });

    await waitFor(() => {
      expect(screen.getByTestId('jobs-count')).toHaveTextContent('1');
    });
  });

  it('displays the "Start a New Review" section', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Start a New Review')).toBeInTheDocument();
    });
    expect(screen.getByText(/Upload your life insurance package/)).toBeInTheDocument();
  });

  it('shows error message when API call fails', async () => {
    endpoints.lifeInsuranceHub.mockRejectedValue(new Error('Network error'));
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('does not render hub content when there is an error', async () => {
    endpoints.lifeInsuranceHub.mockRejectedValue(new Error('fail'));
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('fail')).toBeInTheDocument();
    });
    expect(screen.queryByText('Life Insurance')).not.toBeInTheDocument();
    expect(screen.queryByTestId('run-selector')).not.toBeInTheDocument();
  });

  it('renders empty hint with default text when selection has no label', async () => {
    const hubNoProducts = {
      title: 'Life',
      summary: 'Test',
      taxonomy: [],
    };
    endpoints.lifeInsuranceHub.mockResolvedValue(hubNoProducts);
    renderHub();

    await waitFor(() => {
      expect(screen.getAllByText('Life').length).toBeGreaterThan(0);
    });
    const hint = screen.getByTestId('empty-hint');
    expect(hint).toHaveTextContent('a life product');
  });

  it('renders empty hint with selection label when taxonomy has products', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Life Insurance')).toBeInTheDocument();
    });
    const hint = screen.getByTestId('empty-hint');
    expect(hint).toHaveTextContent(/Level Term Life/);
  });

  it('renders HeartPulse icon via the hub icon container', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    const { container } = renderHub();

    await waitFor(() => {
      expect(screen.getByText('Life Insurance')).toBeInTheDocument();
    });
    const iconContainer = container.querySelector('.bg-rose-500\\/15');
    expect(iconContainer).toBeInTheDocument();
  });

  it('renders the submissions section via SubmissionJobsList', async () => {
    endpoints.lifeInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByTestId('submission-jobs-list')).toBeInTheDocument();
    });
  });
});
