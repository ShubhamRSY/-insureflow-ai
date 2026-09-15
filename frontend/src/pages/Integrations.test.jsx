import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import IntegrationsPage from './Integrations';

vi.mock('../lib/api', () => ({
  endpoints: {
    integrationStatus: vi.fn(),
    connectSource: vi.fn(),
    disconnectSource: vi.fn(),
  },
}));

vi.mock('../components/ConnectorLogo', () => ({
  default: ({ name }) => <div data-testid="connector-logo">{name}</div>,
}));

import { endpoints } from '../lib/api';

const adapter = {
  id: 'lexisnexis', name: 'LexisNexis', category: 'Other', kind: 'needs_config',
  connected: false, config_fields: [{ key: 'api_key', label: 'API Key', placeholder: 'sk-...' }],
};

const connectedAdapter = {
  id: 'clue', name: 'CLUE', category: 'Other', kind: 'live', connected: true, connection_label: 'Connected via sandbox',
};

function renderPage(sourceId) {
  const path = sourceId ? `/integrations/${sourceId}` : '/integrations';
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/integrations" element={<IntegrationsPage />} />
        <Route path="/integrations/:sourceId" element={<IntegrationsPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('IntegrationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching integration status', () => {
    endpoints.integrationStatus.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state when there are no connectors', async () => {
    endpoints.integrationStatus.mockResolvedValue({ adapters: [], systems: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No connectors')).toBeInTheDocument();
    });
  });

  it('renders a not-yet-connected adapter with a Connect button', async () => {
    endpoints.integrationStatus.mockResolvedValue({ adapters: [adapter], systems: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('LexisNexis').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('Needs creds')).toBeInTheDocument();
    expect(screen.getByText('Connect')).toBeInTheDocument();
  });

  it('renders a connected adapter with a Disconnect control', async () => {
    endpoints.integrationStatus.mockResolvedValue({ adapters: [connectedAdapter], systems: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('CLUE').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('Connected via sandbox', { exact: false })).toBeInTheDocument();
  });

  it('opens the config form and connects a source', async () => {
    endpoints.integrationStatus.mockResolvedValue({ adapters: [adapter], systems: [] });
    endpoints.connectSource.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Connect')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Connect'));
    fireEvent.change(screen.getByPlaceholderText('sk-...'), { target: { value: 'secret-key' } });
    fireEvent.click(screen.getByText('Configure to LexisNexis'));

    await waitFor(() => {
      expect(endpoints.connectSource).toHaveBeenCalledWith('lexisnexis', { api_key: 'secret-key' });
    });
  });

  it('shows an error when connecting fails', async () => {
    endpoints.integrationStatus.mockResolvedValue({ adapters: [adapter], systems: [] });
    endpoints.connectSource.mockRejectedValue(new Error('Invalid API key'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Connect')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Connect'));
    fireEvent.click(screen.getByText('Configure to LexisNexis'));

    await waitFor(() => {
      expect(screen.getByText('Invalid API key')).toBeInTheDocument();
    });
  });

  it('disconnects a connected source', async () => {
    endpoints.integrationStatus.mockResolvedValue({ adapters: [connectedAdapter], systems: [] });
    endpoints.disconnectSource.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('CLUE').length).toBeGreaterThan(0);
    });
    const disconnectBtn = screen.getAllByRole('button').find((b) => b.querySelector('svg.lucide-unplug'));
    fireEvent.click(disconnectBtn);

    await waitFor(() => {
      expect(endpoints.disconnectSource).toHaveBeenCalledWith('clue');
    });
  });

  it('auto-opens the config panel when a sourceId route param matches an adapter', async () => {
    endpoints.integrationStatus.mockResolvedValue({ adapters: [adapter], systems: [] });
    renderPage('lexisnexis');

    await waitFor(() => {
      expect(screen.getByText('Configure to LexisNexis')).toBeInTheDocument();
    });
  });

  it('renders the core systems table', async () => {
    endpoints.integrationStatus.mockResolvedValue({
      adapters: [adapter],
      systems: [{ name: 'Guidewire', mode: 'live' }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Core Systems')).toBeInTheDocument();
    });
    expect(screen.getByText('Guidewire')).toBeInTheDocument();
    expect(screen.getByText('live')).toBeInTheDocument();
  });
});
