import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import MortgagePage from './Mortgage';

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual('../lib/api');
  return {
    ...actual,
    endpoints: {
      mortgageProducts: vi.fn(),
      mortgageAudit: vi.fn(),
    },
  };
});

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

vi.mock('../lib/useStateContext', () => ({
  useStateContext: () => ({ selectedState: null }),
}));

vi.mock('../components/RunSelector', () => ({
  default: ({ onSubmit }) => (
    <button type="button" onClick={() => onSubmit({ some: 'body' })}>SubmitRunSelector</button>
  ),
}));

vi.mock('../components/StageStrip', () => ({
  default: () => <div data-testid="stage-strip">StageStrip</div>,
  stagesFromProgress: () => [],
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const job = {
  status: 'completed',
  results: { summary: { decision: 'approve' }, rate_quote: { adjusted_rate: 6.25 } },
};

function renderPage(props = {}) {
  return render(
    <MortgagePage presets={{ mortgage: [] }} jobs={[]} onRunDemo={vi.fn()} onOpenJob={vi.fn()} onRunConnect={vi.fn()} onSubmit={vi.fn()} {...props} />
  );
}

describe('MortgagePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page heading', () => {
    renderPage();
    expect(screen.getByText('Mortgage Underwriting')).toBeInTheDocument();
  });

  it('shows an empty state when there are no jobs', () => {
    renderPage({ jobs: [] });
    expect(screen.getByText('No mortgage jobs')).toBeInTheDocument();
  });

  it('renders a job row with its decision and rate', () => {
    renderPage({ jobs: [{ id: 'job-1', job }] });
    expect(screen.getByText('job-1')).toBeInTheDocument();
    expect(screen.getByText('6.25%')).toBeInTheDocument();
  });

  it('opens a job when its row is clicked', () => {
    const onOpenJob = vi.fn();
    renderPage({ jobs: [{ id: 'job-1', job }], onOpenJob });
    fireEvent.click(screen.getByText('job-1'));
    expect(onOpenJob).toHaveBeenCalledWith('mortgage', 'job-1');
  });

  it('loads and displays mortgage products', async () => {
    endpoints.mortgageProducts.mockResolvedValue({ products: [{ name: 'Conforming 30yr', rate: 6.5 }] });
    renderPage();

    fireEvent.click(screen.getByText('Products'));

    await waitFor(() => {
      expect(screen.getByText('Conforming 30yr')).toBeInTheDocument();
    });
    expect(screen.getByText('Rate: 6.5%')).toBeInTheDocument();
  });

  it('shows a toast error when loading products fails', async () => {
    endpoints.mortgageProducts.mockRejectedValue(new Error('Products unavailable'));
    renderPage();

    fireEvent.click(screen.getByText('Products'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Products unavailable');
    });
  });

  it('closes the products panel', async () => {
    endpoints.mortgageProducts.mockResolvedValue({ products: [{ name: 'Conforming 30yr' }] });
    renderPage();
    fireEvent.click(screen.getByText('Products'));

    await waitFor(() => {
      expect(screen.getByText('Conforming 30yr')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Close'));
    expect(screen.queryByText('Conforming 30yr')).not.toBeInTheDocument();
  });

  it('loads and displays the audit trail for a job', async () => {
    endpoints.mortgageAudit.mockResolvedValue({ trail: ['step1', 'step2'] });
    renderPage({ jobs: [{ id: 'job-1', job: { ...job, results: { ...job.results, bundle_id: 'bundle-1' } } }] });

    fireEvent.click(screen.getByText('Audit'));

    await waitFor(() => {
      expect(screen.getByText(/step1/)).toBeInTheDocument();
    });
  });

  it('shows a toast error when loading the audit trail fails', async () => {
    endpoints.mortgageAudit.mockRejectedValue(new Error('not found'));
    renderPage({ jobs: [{ id: 'job-1', job: { ...job, results: { ...job.results, bundle_id: 'bundle-1' } } }] });

    fireEvent.click(screen.getByText('Audit'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No audit data: not found');
    });
  });

  it('submits via RunSelector and shows an error message on failure', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('Submission failed'));
    renderPage({ onSubmit });

    fireEvent.click(screen.getByText('SubmitRunSelector'));

    await waitFor(() => {
      expect(screen.getByText('Submission failed')).toBeInTheDocument();
    });
  });

  it('shows curated quick samples when present in presets', () => {
    renderPage({
      presets: {
        mortgage: [{ id: 'johnson-residential', name: 'Johnson Residential', description: 'Sample', product_line: 'residential_mortgage' }],
      },
    });
    expect(screen.getByText('Johnson Residential')).toBeInTheDocument();
    expect(screen.getByText('Residential')).toBeInTheDocument();
  });

  it('runs a quick sample demo on click', () => {
    const onRunDemo = vi.fn();
    renderPage({
      onRunDemo,
      presets: {
        mortgage: [{ id: 'chen-residential', name: 'Chen Residential', description: 'Sample', product_line: 'residential_mortgage' }],
      },
    });
    fireEvent.click(screen.getByText('Chen Residential'));
    expect(onRunDemo).toHaveBeenCalledWith('mortgage', 'chen-residential');
  });
});
