import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import WebhooksPage from './Webhooks';

vi.mock('../lib/api', () => ({
  endpoints: {
    insuranceWebhooks: vi.fn(),
    mortgageWebhooks: vi.fn(),
    registerInsuranceWebhook: vi.fn(),
    registerMortgageWebhook: vi.fn(),
    deleteWebhook: vi.fn(),
    deleteMortgageWebhook: vi.fn(),
  },
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

function setupEmpty() {
  endpoints.insuranceWebhooks.mockResolvedValue({ subscriptions: [] });
  endpoints.mortgageWebhooks.mockResolvedValue({ subscriptions: [] });
}

describe('WebhooksPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching webhooks', () => {
    endpoints.insuranceWebhooks.mockReturnValue(new Promise(() => {}));
    endpoints.mortgageWebhooks.mockReturnValue(new Promise(() => {}));
    const { container } = render(<WebhooksPage />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state when there are no webhooks', async () => {
    setupEmpty();
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('No webhooks')).toBeInTheDocument();
    });
  });

  it('renders insurance webhooks in their own table', async () => {
    endpoints.insuranceWebhooks.mockResolvedValue({ subscriptions: [{ id: 'wh-1', url: 'https://example.com/hook', events: ['insurance.completed'] }] });
    endpoints.mortgageWebhooks.mockResolvedValue({ subscriptions: [] });
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('Insurance Webhooks')).toBeInTheDocument();
    });
    expect(screen.getByText('https://example.com/hook')).toBeInTheDocument();
    expect(screen.queryByText('Mortgage Webhooks')).not.toBeInTheDocument();
  });

  it('renders mortgage webhooks in their own table', async () => {
    endpoints.insuranceWebhooks.mockResolvedValue({ subscriptions: [] });
    endpoints.mortgageWebhooks.mockResolvedValue({ subscriptions: [{ id: 'wh-2', url: 'https://example.com/mort-hook', events: ['mortgage.completed'] }] });
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('Mortgage Webhooks')).toBeInTheDocument();
    });
    expect(screen.getByText('https://example.com/mort-hook')).toBeInTheDocument();
  });

  it('opens the registration form with the insurance vertical preselected', async () => {
    setupEmpty();
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('No webhooks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Insurance'));

    expect(screen.getByText('Register Webhook (insurance)')).toBeInTheDocument();
  });

  it('opens the registration form with the mortgage vertical preselected', async () => {
    setupEmpty();
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('No webhooks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Mortgage'));

    expect(screen.getByText('Register Webhook (mortgage)')).toBeInTheDocument();
  });

  it('registers a new insurance webhook and closes the form', async () => {
    setupEmpty();
    endpoints.registerInsuranceWebhook.mockResolvedValue({ ok: true });
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('No webhooks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Insurance'));
    fireEvent.change(screen.getByPlaceholderText('https://example.com/webhook'), { target: { value: 'https://acme.com/hook' } });
    fireEvent.click(screen.getByText('Register'));

    await waitFor(() => {
      expect(endpoints.registerInsuranceWebhook).toHaveBeenCalledWith({ url: 'https://acme.com/hook', events: ['mortgage.completed'] });
    });
    await waitFor(() => {
      expect(screen.queryByText('Register Webhook (insurance)')).not.toBeInTheDocument();
    });
  });

  it('shows a toast error when registration fails', async () => {
    setupEmpty();
    endpoints.registerInsuranceWebhook.mockRejectedValue(new Error('Invalid URL'));
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('No webhooks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Insurance'));
    fireEvent.change(screen.getByPlaceholderText('https://example.com/webhook'), { target: { value: 'bad-url' } });
    fireEvent.click(screen.getByText('Register'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Invalid URL');
    });
  });

  it('cancels the registration form', async () => {
    setupEmpty();
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('No webhooks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Insurance'));
    expect(screen.getByText('Register Webhook (insurance)')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Cancel'));
    expect(screen.queryByText('Register Webhook (insurance)')).not.toBeInTheDocument();
  });

  it('deletes an insurance webhook', async () => {
    endpoints.insuranceWebhooks.mockResolvedValue({ subscriptions: [{ id: 'wh-1', url: 'https://example.com/hook', events: [] }] });
    endpoints.mortgageWebhooks.mockResolvedValue({ subscriptions: [] });
    endpoints.deleteWebhook.mockResolvedValue({ ok: true });
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('https://example.com/hook')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('button').filter((b) => b.querySelector('svg.lucide-trash2'));
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(endpoints.deleteWebhook).toHaveBeenCalledWith('wh-1');
    });
  });

  it('shows a toast error when deleting a webhook fails', async () => {
    endpoints.insuranceWebhooks.mockResolvedValue({ subscriptions: [{ id: 'wh-1', url: 'https://example.com/hook', events: [] }] });
    endpoints.mortgageWebhooks.mockResolvedValue({ subscriptions: [] });
    endpoints.deleteWebhook.mockRejectedValue(new Error('Delete failed'));
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('https://example.com/hook')).toBeInTheDocument();
    });
    const deleteButtons = screen.getAllByRole('button').filter((b) => b.querySelector('svg.lucide-trash2'));
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Delete failed');
    });
  });

  it('reloads webhooks when the refresh button is clicked', async () => {
    setupEmpty();
    render(<WebhooksPage />);

    await waitFor(() => {
      expect(screen.getByText('No webhooks')).toBeInTheDocument();
    });
    expect(endpoints.insuranceWebhooks).toHaveBeenCalledTimes(1);

    const refreshBtn = screen.getAllByRole('button').find((b) => b.querySelector('svg.lucide-refresh-cw'));
    fireEvent.click(refreshBtn);
    expect(endpoints.insuranceWebhooks).toHaveBeenCalledTimes(2);
  });
});
