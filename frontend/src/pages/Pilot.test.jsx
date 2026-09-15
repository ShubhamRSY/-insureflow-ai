import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PilotPage from './Pilot';

vi.mock('../lib/api', () => ({
  endpoints: {
    pilotSandboxStatus: vi.fn(),
    pilotPackages: vi.fn(),
    pilotCalibration: vi.fn(),
    pilotSeed: vi.fn(),
    pilotRun: vi.fn(),
    pilotCalibrate: vi.fn(),
    pilotRedact: vi.fn(),
    pilotIngestEmail: vi.fn(),
  },
}));

import { endpoints } from '../lib/api';

const readiness = {
  overall: 'not_ready',
  shadow_mode: true,
  required_ready: 2,
  required_total: 4,
  feeds: [{ name: 'CLUE', category: 'oracle', status: 'simulated', next_action: 'Request sandbox creds', required_for_pilot: true }],
  bind_cutover: { steps: [{ id: 's1', title: 'Import filed rate book', done: false, required: true }], cutover_ready: false, bind_allowed: false },
};

function setupEmpty() {
  endpoints.pilotSandboxStatus.mockResolvedValue(readiness);
  endpoints.pilotPackages.mockResolvedValue({ packages: [] });
  endpoints.pilotCalibration.mockResolvedValue(null);
}

describe('PilotPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching pilot data', () => {
    endpoints.pilotSandboxStatus.mockReturnValue(new Promise(() => {}));
    endpoints.pilotPackages.mockReturnValue(new Promise(() => {}));
    endpoints.pilotCalibration.mockReturnValue(new Promise(() => {}));
    const { container } = render(<PilotPage />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders readiness stat cards', async () => {
    setupEmpty();
    render(<PilotPage />);

    await waitFor(() => {
      expect(screen.getByText('Readiness')).toBeInTheDocument();
    });
    expect(screen.getByText('not ready')).toBeInTheDocument();
    expect(screen.getByText('2/4')).toBeInTheDocument();
  });

  it('shows the shadow-mode banner when shadow mode is on', async () => {
    setupEmpty();
    render(<PilotPage />);

    await waitFor(() => {
      expect(screen.getByText(/Bind is disabled while shadow mode is on/)).toBeInTheDocument();
    });
  });

  it('renders the bind cutover checklist', async () => {
    setupEmpty();
    render(<PilotPage />);

    await waitFor(() => {
      expect(screen.getByText('Import filed rate book')).toBeInTheDocument();
    });
    expect(screen.getByText(/Cutover ready: no/)).toBeInTheDocument();
  });

  it('renders integration feeds', async () => {
    setupEmpty();
    render(<PilotPage />);

    await waitFor(() => {
      expect(screen.getByText('Integration feeds')).toBeInTheDocument();
    });
    expect(screen.getByText('CLUE *')).toBeInTheDocument();
    expect(screen.getByText('Request sandbox creds')).toBeInTheDocument();
  });

  it('shows an empty state for packages and seeds demos', async () => {
    setupEmpty();
    endpoints.pilotSeed.mockResolvedValue({ seeded: 5 });
    render(<PilotPage />);

    await waitFor(() => {
      expect(screen.getByText('No pilot packages')).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText('Seed demos')[0]);

    await waitFor(() => {
      expect(screen.getByText('Seeded 5 demo packages')).toBeInTheDocument();
    });
  });

  it('renders a pilot package row and runs it', async () => {
    endpoints.pilotSandboxStatus.mockResolvedValue(readiness);
    endpoints.pilotPackages.mockResolvedValue({
      packages: [{ partner: 'acme-mga', submission_id: 'sub-1', insured_name: 'Acme Corp', has_acord: true }],
    });
    endpoints.pilotCalibration.mockResolvedValue(null);
    endpoints.pilotRun.mockResolvedValue({ job_id: 'job-1' });
    render(<PilotPage />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Run'));

    await waitFor(() => {
      expect(endpoints.pilotRun).toHaveBeenCalledWith({ partner: 'acme-mga', submission_id: 'sub-1' });
    });
    await waitFor(() => {
      expect(screen.getByText(/Started sub-1 → job job-1/)).toBeInTheDocument();
    });
  });

  it('redacts a pilot package', async () => {
    endpoints.pilotSandboxStatus.mockResolvedValue(readiness);
    endpoints.pilotPackages.mockResolvedValue({
      packages: [{ partner: 'acme-mga', submission_id: 'sub-1', insured_name: 'Acme Corp' }],
    });
    endpoints.pilotCalibration.mockResolvedValue(null);
    endpoints.pilotRedact.mockResolvedValue({ before: { blocking_count: 3 }, after: { blocking_count: 0 }, files_changed: ['a.pdf'] });
    render(<PilotPage />);

    await waitFor(() => {
      expect(screen.getByText('Redact')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Redact'));

    await waitFor(() => {
      expect(screen.getByText(/Redacted sub-1: blocking 3→0/)).toBeInTheDocument();
    });
  });

  it('calibrates all packages', async () => {
    setupEmpty();
    endpoints.pilotCalibrate.mockResolvedValue({ summary: { match_rate: 0.9, sample_size: 1 }, ran: 10, blocked_pii: 1 });
    render(<PilotPage />);

    await waitFor(() => {
      expect(screen.getByText('Calibrate all')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Calibrate all'));

    await waitFor(() => {
      expect(screen.getByText(/Calibrated 10 packages \(1 blocked by PII\)/)).toBeInTheDocument();
    });
  });

  it('shows an error message when a pilot action fails', async () => {
    setupEmpty();
    endpoints.pilotSeed.mockRejectedValue(new Error('Seeding failed'));
    render(<PilotPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Seed demos').length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getAllByText('Seed demos')[0]);

    await waitFor(() => {
      expect(screen.getByText('Seeding failed')).toBeInTheDocument();
    });
  });
});
