import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GeneralInsuranceHub from './GeneralInsurance';

vi.mock('../lib/api', () => ({
  endpoints: {
    generalInsuranceHub: vi.fn(),
  },
}));

vi.mock('../components/RunSelector', () => ({
  default: (props) => <div data-testid="run-selector" data-general-picker={String(!!props.isGeneralProductPicker)}>RunSelector</div>,
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
  title: 'General Insurance',
  summary: 'Upload and underwrite personal-lines packages.',
  taxonomy: [
    {
      id: 'general',
      name: 'General',
      products: [{ id: 'home_structure', name: 'Home Structure', slug: 'home-structure', insurance_line: 'personal_property', checklist_lob: 'personal_property', coverages: [] }],
    },
  ],
};

function renderHub(props = {}) {
  return render(
    <MemoryRouter>
      <GeneralInsuranceHub presets={[]} onRunDemo={vi.fn()} onSubmit={vi.fn()} jobs={[]} onDeleteJob={vi.fn()} onDeleteAllJobs={vi.fn()} {...props} />
    </MemoryRouter>
  );
}

describe('GeneralInsuranceHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching hub data', () => {
    endpoints.generalInsuranceHub.mockReturnValue(new Promise(() => {}));
    const { container } = renderHub();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders hub title and summary after data loads', async () => {
    endpoints.generalInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('General Insurance')).toBeInTheDocument();
    });
    expect(screen.getByText('Upload and underwrite personal-lines packages.')).toBeInTheDocument();
  });

  it('shows the Catalog badge, not Live', async () => {
    endpoints.generalInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('catalog')).toBeInTheDocument();
    });
    expect(screen.queryByText('live')).not.toBeInTheDocument();
  });

  it('renders RunSelector with the general product picker flag', async () => {
    endpoints.generalInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByTestId('run-selector')).toBeInTheDocument();
    });
    expect(screen.getByTestId('run-selector')).toHaveAttribute('data-general-picker', 'true');
  });

  it('renders SubmissionJobsList with fallbackLine "General"', async () => {
    endpoints.generalInsuranceHub.mockResolvedValue(mockHubData);
    renderHub();

    await waitFor(() => {
      expect(screen.getByTestId('fallback-line')).toHaveTextContent('General');
    });
  });

  it('shows an error message when the API call fails', async () => {
    endpoints.generalInsuranceHub.mockRejectedValue(new Error('Network error'));
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('run-selector')).not.toBeInTheDocument();
  });
});
