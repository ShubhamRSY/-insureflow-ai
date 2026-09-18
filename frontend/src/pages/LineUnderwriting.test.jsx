import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LineUnderwriting from './LineUnderwriting';

vi.mock('../lib/api', () => ({
  endpoints: {
    underwritingDesks: vi.fn(),
    lineServiceTickets: vi.fn(),
    lineCoverageAssist: vi.fn(),
    createLineServiceTicket: vi.fn(),
    updateLineServiceTicket: vi.fn(),
  },
}));

import { endpoints } from '../lib/api';

const desksData = {
  desks: { line: { capabilities: [{ id: 'cap1', title: 'Coverage assist', description: 'Recommend broaden/narrow actions' }] } },
};

function setupEmpty() {
  endpoints.underwritingDesks.mockResolvedValue(desksData);
  endpoints.lineServiceTickets.mockResolvedValue({ tickets: [] });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <LineUnderwriting />
    </MemoryRouter>
  );
}

describe('LineUnderwriting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading state, then renders desk capabilities', async () => {
    setupEmpty();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Recommend broaden/narrow actions')).toBeInTheDocument();
    });
  });

  it('shows an empty state when there are no service tickets', async () => {
    setupEmpty();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No open service work')).toBeInTheDocument();
    });
  });

  it('renders an open service ticket with readable type/status badges and detail', async () => {
    endpoints.underwritingDesks.mockResolvedValue(desksData);
    endpoints.lineServiceTickets.mockResolvedValue({
      tickets: [{
        ticket_id: 't1', request_type: 'policyholder_inquiry', status: 'in_progress', subject: 'New quote request',
        requester: 'producer', detail: 'Needs a certificate of insurance by Friday', created_at: new Date().toISOString(),
      }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('New quote request')).toBeInTheDocument();
    });
    expect(screen.getAllByText('Policyholder inquiry').length).toBeGreaterThan(0);
    expect(screen.getByText('In progress')).toBeInTheDocument();
    expect(screen.getByText('Needs a certificate of insurance by Friday')).toBeInTheDocument();
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  it('runs coverage assist and renders recommendations', async () => {
    setupEmpty();
    endpoints.lineCoverageAssist.mockResolvedValue({
      summary: 'Broaden coverage for transit exposure',
      recommendations: [{ title: 'Add inland marine', action: 'broaden', priority: 'high', rationale: 'Weekly transit exposure not covered', suggested_form: 'CM 00 20', suggested_endorsements: ['Cargo transit endorsement'] }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Recommend coverage')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Recommend coverage'));

    await waitFor(() => {
      expect(screen.getByText('Broaden coverage for transit exposure')).toBeInTheDocument();
    });
    expect(screen.getByText('Add inland marine')).toBeInTheDocument();
    expect(screen.getByText('high priority')).toBeInTheDocument();
    expect(screen.getByText(/Cargo transit endorsement/)).toBeInTheDocument();
  });

  it('shows an error when coverage assist fails', async () => {
    setupEmpty();
    endpoints.lineCoverageAssist.mockRejectedValue(new Error('Assist unavailable'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Recommend coverage')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Recommend coverage'));

    await waitFor(() => {
      expect(screen.getByText('Assist unavailable')).toBeInTheDocument();
    });
  });

  it('opens a new service ticket', async () => {
    setupEmpty();
    endpoints.createLineServiceTicket.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Subject')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText('Subject'), { target: { value: 'Endorsement request' } });
    fireEvent.click(screen.getByText('Open ticket'));

    await waitFor(() => {
      expect(endpoints.createLineServiceTicket).toHaveBeenCalledWith(expect.objectContaining({ subject: 'Endorsement request', request_type: 'quote' }));
    });
  });

  it('completes an open ticket', async () => {
    endpoints.underwritingDesks.mockResolvedValue(desksData);
    endpoints.lineServiceTickets.mockResolvedValue({
      tickets: [{ ticket_id: 't1', request_type: 'quote', status: 'open', subject: 'New quote request', requester: 'producer' }],
    });
    endpoints.updateLineServiceTicket.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Complete')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Complete'));

    await waitFor(() => {
      expect(endpoints.updateLineServiceTicket).toHaveBeenCalledWith('t1', expect.objectContaining({ status: 'completed' }));
    });
  });
});
