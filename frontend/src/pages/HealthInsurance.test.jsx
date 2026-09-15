import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import HealthInsuranceHub from './HealthInsurance';

vi.mock('../lib/api', () => ({
  endpoints: {
    healthInsuranceHub: vi.fn(),
  },
}));

vi.mock('../components/RunSelector', () => ({
  default: (props) => <div data-testid="run-selector" data-health-picker={String(!!props.isHealthProductPicker)}>RunSelector</div>,
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
  title: 'Health Insurance',
  summary: 'Upload and underwrite health insurance packages.',
  taxonomy: [
    {
      id: 'health',
      name: 'Health',
      products: [{ id: 'individual_basic', name: 'Individual Basic', slug: 'individual-basic', insurance_line: 'health', checklist_lob: 'health', coverages: [] }],
    },
  ],
};

function renderHub(props = {}) {
  return render(
    <HealthInsuranceHub presets={[]} onRunDemo={vi.fn()} onSubmit={vi.fn()} jobs={[]} onDeleteJob={vi.fn()} onDeleteAllJobs={vi.fn()} {...props} />
  );
}

describe('HealthInsuranceHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching hub data', () => {
    endpoints.healthInsuranceHub.mockReturnValue(new Promise(() => {}));
    const { container } = renderHub();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders hub title and summary after data loads', async () => {
    endpoints.healthInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Health Insurance')).toBeInTheDocument();
    });
    expect(screen.getByText('Upload and underwrite health insurance packages.')).toBeInTheDocument();
  });

  it('shows the Live badge', async () => {
    endpoints.healthInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Live')).toBeInTheDocument();
    });
  });

  it('renders RunSelector with the health product picker flag', async () => {
    endpoints.healthInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByTestId('run-selector')).toBeInTheDocument();
    });
    expect(screen.getByTestId('run-selector')).toHaveAttribute('data-health-picker', 'true');
  });

  it('renders SubmissionJobsList with fallbackLine "Health" and passes jobs through', async () => {
    endpoints.healthInsuranceHub.mockResolvedValue(mockHubData);
    renderHub({ jobs: [{ id: '1' }, { id: '2' }] });

    await waitFor(() => {
      expect(screen.getByTestId('submission-jobs-list')).toBeInTheDocument();
    });
    expect(screen.getByTestId('fallback-line')).toHaveTextContent('Health');
    expect(screen.getByTestId('jobs-count')).toHaveTextContent('2');
  });

  it('shows an error message when the API call fails and does not render hub content', async () => {
    endpoints.healthInsuranceHub.mockRejectedValue(new Error('Network error'));
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('run-selector')).not.toBeInTheDocument();
  });

  it('renders the empty hint with a product-selection label', async () => {
    endpoints.healthInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByTestId('empty-hint')).toBeInTheDocument();
    });
    expect(screen.getByTestId('empty-hint')).toHaveTextContent(/Individual Basic/);
  });
});
