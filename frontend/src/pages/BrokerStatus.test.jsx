import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import BrokerStatus from './BrokerStatus';

vi.mock('../lib/api', () => ({
  publicApi: vi.fn(),
}));

import { publicApi } from '../lib/api';

function renderPage(token = 'tok-123') {
  return render(
    <MemoryRouter initialEntries={[`/broker/status/${token}`]}>
      <Routes>
        <Route path="/broker/status/:token" element={<BrokerStatus />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('BrokerStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading state before data arrives', () => {
    publicApi.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText('Loading submission status...')).toBeInTheDocument();
  });

  it('shows an error state when the token is invalid', async () => {
    publicApi.mockRejectedValue(new Error('Link expired'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Status Unavailable')).toBeInTheDocument();
    });
    expect(screen.getByText('Link expired')).toBeInTheDocument();
  });

  it('fetches status using the token from the URL', async () => {
    publicApi.mockResolvedValue({ status: 'completed', bundle_id: 'bundle-1' });
    renderPage('tok-abc');

    await waitFor(() => {
      expect(publicApi).toHaveBeenCalledWith('/broker/status/tok-abc');
    });
  });

  it('renders the status banner and bundle id', async () => {
    publicApi.mockResolvedValue({ status: 'completed', bundle_id: 'bundle-1', decision: 'accept' });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Completed')).toBeInTheDocument();
    });
    expect(screen.getByText('bundle-1')).toBeInTheDocument();
    expect(screen.getByText('Accepted')).toBeInTheDocument();
  });

  it('shows pending info requests and submits a response', async () => {
    const initial = {
      status: 'processing',
      bundle_id: 'bundle-1',
      awaiting_broker_info: true,
      pending_info_requests: [{ request_id: 'req-1', documents: ['Loss run'], notes: 'Last 3 years' }],
    };
    const afterRespond = { status: 'processing', bundle_id: 'bundle-1', awaiting_broker_info: false };
    publicApi.mockImplementation((path) => {
      if (path.includes('/respond')) return Promise.resolve({ ok: true });
      return Promise.resolve(afterRespond);
    });
    publicApi.mockImplementationOnce(() => Promise.resolve(initial));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Action required — information requested')).toBeInTheDocument();
    });
    expect(screen.getByText('Loss run')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Mark requests fulfilled'));

    await waitFor(() => {
      expect(publicApi).toHaveBeenCalledWith('/broker/status/tok-123/respond', expect.objectContaining({
        method: 'POST',
        body: expect.objectContaining({ mark_all_pending: true }),
      }));
    });
    // Once the follow-up fetch reports no more pending requests, the whole
    // "action required" panel (success message included) unmounts.
    await waitFor(() => {
      expect(screen.queryByText('Action required — information requested')).not.toBeInTheDocument();
    });
  });

  it('renders workflow state when present', async () => {
    publicApi.mockResolvedValue({ status: 'completed', bundle_id: 'bundle-1', workflow_state: 'approved' });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Workflow')).toBeInTheDocument();
    });
    expect(screen.getByText('approved')).toBeInTheDocument();
  });
});
