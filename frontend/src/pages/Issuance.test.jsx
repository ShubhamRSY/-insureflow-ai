import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import IssuancePage from './Issuance';

vi.mock('../lib/api', () => ({
  endpoints: {
    issuanceRecords: vi.fn(),
    issuanceDownload: vi.fn(),
  },
  fmtCurrency: (n) => (n == null || isNaN(n) ? '—' : `$${Number(n).toLocaleString('en-US')}`),
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const futureDate = new Date(Date.now() + 1000 * 60 * 60 * 24 * 30).toISOString();
const pastDate = new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString();

const record = {
  issuance_id: 'iss-1',
  bundle_id: 'bundle-1',
  insured_name: 'Acme Corp',
  status: 'bound',
  policy_number: 'POL-1001',
  line_of_business: 'General Liability',
  broker_name: 'Broker Co',
  premium: 15000,
  tiv: 2000000,
  effective_date: pastDate,
  expiry_date: futureDate,
  bound_by: 'jdoe',
  bound_at: pastDate,
  documents: [{ doc_type: 'binder' }, { doc_type: 'certificate' }],
};

describe('IssuancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();
  });

  it('shows a loading spinner while fetching records', () => {
    endpoints.issuanceRecords.mockReturnValue(new Promise(() => {}));
    const { container } = render(<IssuancePage />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an error message when loading fails', async () => {
    endpoints.issuanceRecords.mockRejectedValue(new Error('Could not load issuance records'));
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('Could not load issuance records')).toBeInTheDocument();
    });
  });

  it('shows an empty state when there are no issued packages', async () => {
    endpoints.issuanceRecords.mockResolvedValue({ records: [] });
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('No issued packages yet')).toBeInTheDocument();
    });
  });

  it('renders an issuance card with policy details', async () => {
    endpoints.issuanceRecords.mockResolvedValue({ records: [record] });
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    expect(screen.getByText('Acme Corp').closest('.glass-card')).toHaveTextContent('via Broker Co');
    expect(screen.getAllByText('$15,000').length).toBeGreaterThan(0);
    expect(screen.getByText('$2,000,000')).toBeInTheDocument();
  });

  it('renders summary stat cards from loaded records', async () => {
    endpoints.issuanceRecords.mockResolvedValue({ records: [record] });
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('Packages issued')).toBeInTheDocument();
    });
    expect(screen.getByText('Policies in force')).toBeInTheDocument();
    expect(screen.getByText('Annualized premium')).toBeInTheDocument();
  });

  it('only shows download buttons for documents that exist on the record', async () => {
    endpoints.issuanceRecords.mockResolvedValue({ records: [record] });
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('Binder')).toBeInTheDocument();
    });
    expect(screen.getByText('Certificate of Insurance')).toBeInTheDocument();
    expect(screen.queryByText('Policy Worksheet')).not.toBeInTheDocument();
  });

  it('downloads a document when its button is clicked', async () => {
    endpoints.issuanceRecords.mockResolvedValue({ records: [record] });
    endpoints.issuanceDownload.mockResolvedValue({ blob: new Blob(['x']), filename: 'binder.pdf' });
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('Binder')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Binder'));

    await waitFor(() => {
      expect(endpoints.issuanceDownload).toHaveBeenCalledWith('bundle-1', 'binder');
    });
  });

  it('shows a toast error when a download fails', async () => {
    endpoints.issuanceRecords.mockResolvedValue({ records: [record] });
    endpoints.issuanceDownload.mockRejectedValue(new Error('Document not found'));
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('Binder')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Binder'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Document not found');
    });
  });

  it('renders a raw snake_case line of business as a readable label', async () => {
    endpoints.issuanceRecords.mockResolvedValue({ records: [{ ...record, line_of_business: 'general_liability' }] });
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    expect(screen.getByText(/General Liability/)).toBeInTheDocument();
  });

  it('shows a message when a record has no generated documents yet', async () => {
    endpoints.issuanceRecords.mockResolvedValue({ records: [{ ...record, documents: [] }] });
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('No documents generated yet')).toBeInTheDocument();
    });
  });

  it('reloads records when Refresh is clicked', async () => {
    endpoints.issuanceRecords.mockResolvedValue({ records: [] });
    render(<IssuancePage />);

    await waitFor(() => {
      expect(screen.getByText('No issued packages yet')).toBeInTheDocument();
    });
    expect(endpoints.issuanceRecords).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('Refresh'));
    expect(endpoints.issuanceRecords).toHaveBeenCalledTimes(2);
  });
});
