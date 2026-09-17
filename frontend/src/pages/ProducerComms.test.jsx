import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useOutletContext } from 'react-router-dom';
import ProducerCommsPage from './ProducerComms';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useOutletContext: vi.fn() };
});

vi.mock('../lib/api', () => ({
  endpoints: {
    producerNotifications: vi.fn(),
    acknowledgeNotification: vi.fn(),
  },
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const sentNotification = {
  notification_id: 'notif-1', bundle_id: 'bundle-1', kind: 'uw_decision', status: 'sent',
  producer_name: 'Jane Broker', decision: 'approve', message: 'Your submission has been approved.',
  created_at: '2026-01-01T00:00:00Z',
};

const ackedNotification = {
  notification_id: 'notif-2', bundle_id: 'bundle-2', kind: 'bind', status: 'acknowledged',
  producer_name: 'Jane Broker', decision: 'bound', message: 'Coverage is now in force.',
  created_at: '2026-01-01T00:00:00Z', acknowledged_by: 'jane', acknowledged_at: '2026-01-02T00:00:00Z',
};

function renderPage() {
  useOutletContext.mockReturnValue({ user: { username: 'jdoe' } });
  return render(<ProducerCommsPage />);
}

describe('ProducerCommsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching notifications', () => {
    endpoints.producerNotifications.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an error message when loading fails', async () => {
    endpoints.producerNotifications.mockRejectedValue(new Error('Could not load notifications'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Could not load notifications')).toBeInTheDocument();
    });
  });

  it('shows an empty state when there are no notifications', async () => {
    endpoints.producerNotifications.mockResolvedValue({ notifications: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No producer communications yet')).toBeInTheDocument();
    });
  });

  it('renders a sent notification with an Acknowledge button', async () => {
    endpoints.producerNotifications.mockResolvedValue({ notifications: [sentNotification] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Your submission has been approved.')).toBeInTheDocument();
    });
    expect(screen.getByText('to Jane Broker', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('Acknowledge')).toBeInTheDocument();
  });

  it('renders an acknowledged notification without an Acknowledge button', async () => {
    endpoints.producerNotifications.mockResolvedValue({ notifications: [ackedNotification] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Coverage is now in force.')).toBeInTheDocument();
    });
    expect(screen.queryByText('Acknowledge')).not.toBeInTheDocument();
    expect(screen.getByText(/acknowledged by/)).toBeInTheDocument();
  });

  it('acknowledges a sent notification', async () => {
    endpoints.producerNotifications.mockResolvedValue({ notifications: [sentNotification] });
    endpoints.acknowledgeNotification.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acknowledge')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Acknowledge'));

    await waitFor(() => {
      expect(endpoints.acknowledgeNotification).toHaveBeenCalledWith('bundle-1', 'notif-1', 'jdoe');
    });
  });

  it('shows a toast error when acknowledging fails', async () => {
    endpoints.producerNotifications.mockResolvedValue({ notifications: [sentNotification] });
    endpoints.acknowledgeNotification.mockRejectedValue(new Error('Already acknowledged'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Acknowledge')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Acknowledge'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Already acknowledged');
    });
  });

  it('filters notifications by acknowledgement status', async () => {
    endpoints.producerNotifications.mockResolvedValue({ notifications: [sentNotification, ackedNotification] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Your submission has been approved.')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('tab', { name: /^Acknowledged/ }));

    expect(screen.queryByText('Your submission has been approved.')).not.toBeInTheDocument();
    expect(screen.getByText('Coverage is now in force.')).toBeInTheDocument();
  });

  it('renders total/acknowledged/awaiting stat cards', async () => {
    endpoints.producerNotifications.mockResolvedValue({ notifications: [sentNotification, ackedNotification] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Total communications')).toBeInTheDocument();
    });
    expect(screen.getAllByText('Acknowledged').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Awaiting ack').length).toBeGreaterThan(0);
  });
});
