import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import InsurancePage from './Insurance';

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { toast } from '../lib/toast';

const job = {
  id: 'bundle-1',
  job: { status: 'completed', results: { insured_name: 'Acme Corp', bundle_id: 'bundle-1' } },
};

function renderPage(props = {}) {
  return render(
    <MemoryRouter>
      <InsurancePage jobs={[]} queueStats={null} onRefresh={vi.fn()} onDeleteJob={vi.fn()} onDeleteAllJobs={vi.fn()} {...props} />
    </MemoryRouter>
  );
}

describe('InsurancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the first 4 active sections by default', () => {
    renderPage();
    expect(screen.getByText('Life Insurance')).toBeInTheDocument();
    expect(screen.getByText('Commercial Lines')).toBeInTheDocument();
    expect(screen.queryByText('Aviation')).not.toBeInTheDocument();
  });

  it('shows all sections after clicking "Show all"', () => {
    renderPage();
    fireEvent.click(screen.getByText(/Show all/));
    expect(screen.getByText('Aviation')).toBeInTheDocument();
  });

  it('collapses back to 4 sections after clicking "Show fewer"', () => {
    renderPage();
    fireEvent.click(screen.getByText(/Show all/));
    expect(screen.getByText('Aviation')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Show fewer'));
    expect(screen.queryByText('Aviation')).not.toBeInTheDocument();
  });

  it('shows an empty state when there are no recent jobs', () => {
    renderPage();
    expect(screen.getByText('No jobs yet. Open a section and run a package.')).toBeInTheDocument();
  });

  it('renders a recent job row', () => {
    renderPage({ jobs: [job] });
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
  });

  it('calls onRefresh when Refresh jobs is clicked', () => {
    const onRefresh = vi.fn();
    renderPage({ onRefresh });
    fireEvent.click(screen.getByText('Refresh jobs'));
    expect(onRefresh).toHaveBeenCalled();
  });

  it('deletes a single job after confirmation', async () => {
    const onDeleteJob = vi.fn().mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage({ jobs: [job], onDeleteJob });

    fireEvent.click(screen.getByLabelText('Delete bundle-1'));

    expect(onDeleteJob).toHaveBeenCalledWith('bundle-1');
  });

  it('shows a toast error when deleting a job fails', async () => {
    const onDeleteJob = vi.fn().mockRejectedValue(new Error('Could not delete'));
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage({ jobs: [job], onDeleteJob });

    fireEvent.click(screen.getByLabelText('Delete bundle-1'));

    await vi.waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Could not delete');
    });
  });

  it('deletes all listed jobs after confirmation', () => {
    const onDeleteAllJobs = vi.fn();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage({ jobs: [job], onDeleteAllJobs });

    fireEvent.click(screen.getByText('Delete all'));

    expect(onDeleteAllJobs).toHaveBeenCalledWith(['bundle-1']);
  });

  it('does not delete all when the confirm dialog is dismissed', () => {
    const onDeleteAllJobs = vi.fn();
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderPage({ jobs: [job], onDeleteAllJobs });

    fireEvent.click(screen.getByText('Delete all'));

    expect(onDeleteAllJobs).not.toHaveBeenCalled();
  });
});
