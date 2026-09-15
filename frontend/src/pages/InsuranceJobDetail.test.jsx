import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import InsuranceJobDetail from './InsuranceJobDetail';

vi.mock('../lib/api', () => ({
  endpoints: {
    insuranceJob: vi.fn(),
    insuranceReport: vi.fn(),
    insuranceQuote: vi.fn(),
    createBrokerShare: vi.fn(),
    deleteJob: vi.fn(),
    retryJob: vi.fn(),
  },
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

vi.mock('../components/MemoReportView', () => ({
  default: ({ job }) => <div data-testid="memo-report-view">MemoReportView:{job?.status}</div>,
  Collapsible: ({ title, children }) => (
    <details>
      <summary>{title}</summary>
      {children}
    </details>
  ),
}));

vi.mock('../components/SubmissionJourney', () => ({
  default: () => <div data-testid="submission-journey">SubmissionJourney</div>,
}));
vi.mock('../components/UwWorksheetView', () => ({ default: () => <div>UwWorksheetView</div> }));
vi.mock('../components/UwPolicyValidator', () => ({ default: () => <div>UwPolicyValidator</div> }));
vi.mock('../components/RateProvenance', () => ({ default: () => <div>RateProvenance</div> }));
vi.mock('../components/BindReadinessPanel', () => ({ default: () => <div data-testid="bind-readiness-panel">BindReadinessPanel</div> }));
vi.mock('../components/ActuarialView', () => ({ default: () => <div>ActuarialView</div> }));
vi.mock('../components/MibOrderView', () => ({ default: () => <div>MibOrderView</div> }));
vi.mock('../components/ApsOrderView', () => ({ default: () => <div>ApsOrderView</div> }));
vi.mock('../components/PolicyIssuanceView', () => ({ default: () => <div>PolicyIssuanceView</div> }));
vi.mock('../components/PremiumCalculator', () => ({ default: () => <div>PremiumCalculator</div> }));
vi.mock('../components/RenewalTrackerView', () => ({ default: () => <div>RenewalTrackerView</div> }));
vi.mock('../components/BeneficiaryReviewView', () => ({ default: () => <div>BeneficiaryReviewView</div> }));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const completedJob = {
  status: 'completed',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:05:00Z',
  results: { bundle_id: 'bundle-1', insured_name: 'Acme Corp', memo: { summary: 'ok' } },
};

function renderPage(jobId = 'job-1', props = {}) {
  return render(
    <MemoryRouter initialEntries={[`/insurance/${jobId}`]}>
      <Routes>
        <Route path="/insurance/:jobId" element={<InsuranceJobDetail onDeleted={vi.fn()} onDeleteJob={vi.fn()} {...props} />} />
        <Route path="/insurance" element={<div>Insurance hub</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('InsuranceJobDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
  });

  it('shows a loading state while fetching the job', () => {
    endpoints.insuranceJob.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
    expect(screen.getByText('Loading submission…')).toBeInTheDocument();
  });

  it('shows an error state when the job fails to load', async () => {
    endpoints.insuranceJob.mockRejectedValue(new Error('Job not found'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Job not found')).toBeInTheDocument();
    });
    expect(screen.getByText('Back to Insurance')).toBeInTheDocument();
  });

  it('renders the header with insured name and job id', async () => {
    endpoints.insuranceJob.mockResolvedValue(completedJob);
    renderPage('job-1');

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    expect(screen.getByText(/job-1/)).toBeInTheDocument();
  });

  it('renders MemoReportView when the job is completed', async () => {
    endpoints.insuranceJob.mockResolvedValue(completedJob);
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('memo-report-view')).toBeInTheDocument();
    });
    expect(screen.getByTestId('bind-readiness-panel')).toBeInTheDocument();
  });

  it('shows SubmissionJourney instead of the memo while processing', async () => {
    endpoints.insuranceJob.mockResolvedValue({ status: 'processing', created_at: '2026-01-01T00:00:00Z', results: {} });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('submission-journey')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('memo-report-view')).not.toBeInTheDocument();
  });

  it('shows a pipeline-not-run banner and retries it', async () => {
    endpoints.insuranceJob.mockResolvedValue({ status: 'completed', created_at: '2026-01-01T00:00:00Z', results: {} });
    endpoints.retryJob.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Pipeline has not run yet')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Run Pipeline'));

    await waitFor(() => {
      expect(endpoints.retryJob).toHaveBeenCalledWith('job-1');
    });
  });

  it('downloads the indication PDF', async () => {
    endpoints.insuranceJob.mockResolvedValue(completedJob);
    endpoints.insuranceQuote.mockResolvedValue({ blob: new Blob(['x']), filename: 'quote.pdf' });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Indication PDF')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Indication PDF'));

    await waitFor(() => {
      expect(endpoints.insuranceQuote).toHaveBeenCalledWith('job-1');
    });
  });

  it('shows a toast error when the quote download fails', async () => {
    endpoints.insuranceJob.mockResolvedValue(completedJob);
    endpoints.insuranceQuote.mockRejectedValue(new Error('Quote not ready'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Indication PDF')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Indication PDF'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Quote not ready');
    });
  });

  it('downloads the full report', async () => {
    endpoints.insuranceJob.mockResolvedValue(completedJob);
    endpoints.insuranceReport.mockResolvedValue({ blob: new Blob(['x']), filename: 'report.pdf' });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Full Report')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Full Report'));

    await waitFor(() => {
      expect(endpoints.insuranceReport).toHaveBeenCalledWith('job-1');
    });
  });

  it('copies a broker share link', async () => {
    endpoints.insuranceJob.mockResolvedValue(completedJob);
    endpoints.createBrokerShare.mockResolvedValue({ token: 'tok-123' });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Broker Share')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Broker Share'));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining('/dashboard/broker/status/tok-123'));
    });
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('Share link copied!'));
    });
  });

  it('deletes the job after confirmation using the provided onDeleteJob handler', async () => {
    endpoints.insuranceJob.mockResolvedValue(completedJob);
    const onDeleteJob = vi.fn().mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage('job-1', { onDeleteJob });

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Delete'));

    await waitFor(() => {
      expect(onDeleteJob).toHaveBeenCalledWith('job-1');
    });
  });

  it('falls back to endpoints.deleteJob when no onDeleteJob handler is provided', async () => {
    endpoints.insuranceJob.mockResolvedValue(completedJob);
    endpoints.deleteJob.mockResolvedValue({ ok: true });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage('job-1', { onDeleteJob: undefined });

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Delete'));

    await waitFor(() => {
      expect(endpoints.deleteJob).toHaveBeenCalledWith('job-1');
    });
  });

  it('does not delete when the confirm dialog is dismissed', async () => {
    endpoints.insuranceJob.mockResolvedValue(completedJob);
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Delete'));

    expect(endpoints.deleteJob).not.toHaveBeenCalled();
  });

  it('shows the archived banner for archived jobs', async () => {
    endpoints.insuranceJob.mockResolvedValue({ ...completedJob, archived: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Archived from the landing-zone disk/)).toBeInTheDocument();
    });
  });
});
