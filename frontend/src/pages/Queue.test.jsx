import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import QueuePage from './Queue';

const queueStats = {
  queue: [
    { bundle_id: 'bundle-hot', insured_name: 'Acme Corp', priority: 'hot', score: 88 },
    { bundle_id: 'bundle-warm', insured_name: 'Beta LLC', priority: 'warm', score: 55 },
    { bundle_id: 'bundle-cold', insured_name: 'Cold Co', priority: 'cold', score: 20 },
    { bundle_id: 'bundle-nofit', insured_name: 'No Fit Inc', priority: 'no_fit', score: 5 },
  ],
};

const insuranceJobs = [];

describe('QueuePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the submission count and each queued insured', () => {
    render(<QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={vi.fn()} onRefresh={vi.fn()} />);

    expect(screen.getAllByText('4').length).toBeGreaterThan(0);
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Beta LLC')).toBeInTheDocument();
    expect(screen.getByText('Cold Co')).toBeInTheDocument();
    expect(screen.getByText('No Fit Inc')).toBeInTheDocument();
  });

  it('renders hot/warm stat counts', () => {
    render(<QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={vi.fn()} onRefresh={vi.fn()} />);

    expect(screen.getByText('Hot')).toBeInTheDocument();
    expect(screen.getByText('Warm')).toBeInTheDocument();
    const hotCard = screen.getByText('Hot').closest('div');
    expect(hotCard).toHaveTextContent('1');
  });

  it('shows an empty state when there are no queue items', () => {
    render(<QueuePage queueStats={{ queue: [] }} insuranceJobs={[]} onOpenJob={vi.fn()} onRefresh={vi.fn()} />);
    expect(screen.getByText('No submissions match')).toBeInTheDocument();
  });

  it('calls onRefresh when Refresh is clicked', () => {
    const onRefresh = vi.fn();
    render(<QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={vi.fn()} onRefresh={onRefresh} />);
    fireEvent.click(screen.getByText('Refresh'));
    expect(onRefresh).toHaveBeenCalled();
  });

  it('opens a job when a row is clicked', () => {
    const onOpenJob = vi.fn();
    render(<QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={onOpenJob} onRefresh={vi.fn()} />);
    fireEvent.click(screen.getByText('Acme Corp'));
    expect(onOpenJob).toHaveBeenCalledWith('insurance', 'bundle-hot', 'bundle-hot');
  });

  it('filters rows by priority', () => {
    render(<QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={vi.fn()} onRefresh={vi.fn()} />);
    fireEvent.click(screen.getByText('hot'));

    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.queryByText('Beta LLC')).not.toBeInTheDocument();
  });

  it('filters rows by search query across insured name', () => {
    render(<QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={vi.fn()} onRefresh={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText('Search insured, ID, or LOB…'), { target: { value: 'beta' } });

    expect(screen.getByText('Beta LLC')).toBeInTheDocument();
    expect(screen.queryByText('Acme Corp')).not.toBeInTheDocument();
  });

  it('shows a "no submissions match" empty state when filters exclude everything', () => {
    render(<QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={vi.fn()} onRefresh={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText('Search insured, ID, or LOB…'), { target: { value: 'nonexistent-xyz' } });
    expect(screen.getByText('No submissions match')).toBeInTheDocument();
  });

  it('sorts rows by insured name A-Z when selected', () => {
    render(<QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={vi.fn()} onRefresh={vi.fn()} />);
    fireEvent.change(screen.getByDisplayValue('Score (high to low)'), { target: { value: 'insured' } });

    const rows = screen.getAllByRole('row').slice(1); // drop header row
    expect(rows[0]).toHaveTextContent('Acme Corp');
  });

  it('maps no_fit priority rows to the Appetite Check Failed status count', () => {
    render(<QueuePage queueStats={queueStats} insuranceJobs={insuranceJobs} onOpenJob={vi.fn()} onRefresh={vi.fn()} />);
    const [label] = screen.getAllByText('Appetite Check Failed');
    expect(label.closest('div')).toHaveTextContent('1');
  });
});
