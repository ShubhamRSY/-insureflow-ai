import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useOutletContext } from 'react-router-dom';
import SettingsPage from './Settings';

vi.mock('react-router-dom', () => ({
  useOutletContext: vi.fn(),
}));

vi.mock('../components/ThemeToggle', () => ({
  default: () => <div data-testid="theme-toggle">ThemeToggle</div>,
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

vi.mock('../lib/api', () => ({
  auth: {
    clear: vi.fn(),
    wipeSession: vi.fn(),
  },
  endpoints: {
    roles: vi.fn(),
    insuranceCompanies: vi.fn(),
    addInsuranceCompany: vi.fn(),
    authReset: vi.fn(),
  },
}));

import { auth, endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const mockUser = { username: 'jdoe', role: 'underwriter', org_id: 'org-123' };

function renderSettings(props = {}) {
  return render(<SettingsPage {...props} />);
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useOutletContext.mockReturnValue({ user: mockUser });
    endpoints.roles.mockResolvedValue({ roles: [] });
    endpoints.insuranceCompanies.mockResolvedValue({ companies: [] });
  });

  it('renders the page heading and appearance section', () => {
    renderSettings();
    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.getByText('Appearance')).toBeInTheDocument();
    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
  });

  it('renders the signed-in user\'s username, role, and org', async () => {
    renderSettings();
    await waitFor(() => {
      expect(screen.getByText('jdoe')).toBeInTheDocument();
    });
    expect(screen.getByText('underwriter')).toBeInTheDocument();
    expect(screen.getByText('org-123')).toBeInTheDocument();
  });

  it('shows "Not signed in" and a Sign In button when there is no user', () => {
    useOutletContext.mockReturnValue({ user: null });
    const onLogin = vi.fn();
    renderSettings({ onLogin });

    expect(screen.getByText('Not signed in')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Sign In'));
    expect(onLogin).toHaveBeenCalled();
  });

  it('does not render account fields or sign out when there is no user', () => {
    useOutletContext.mockReturnValue({ user: null });
    renderSettings();

    expect(screen.queryByText('Username')).not.toBeInTheDocument();
    expect(screen.queryByText('Sign Out')).not.toBeInTheDocument();
  });

  it('renders the RBAC section only when roles are returned', async () => {
    endpoints.roles.mockResolvedValue({
      roles: [{ role: 'admin', level: 5, description: 'Full access' }],
    });
    renderSettings();

    await waitFor(() => {
      expect(screen.getByText('Role-Based Access Control')).toBeInTheDocument();
    });
    expect(screen.getByText('Full access')).toBeInTheDocument();
    expect(screen.getByText('Lv.5')).toBeInTheDocument();
  });

  it('does not render the RBAC section when no roles are returned', async () => {
    renderSettings();
    await waitFor(() => {
      expect(screen.getByText('jdoe')).toBeInTheDocument();
    });
    expect(screen.queryByText('Role-Based Access Control')).not.toBeInTheDocument();
  });

  it('renders appointed companies and a fallback message when empty', async () => {
    renderSettings();
    await waitFor(() => {
      expect(screen.getByText('No companies loaded.')).toBeInTheDocument();
    });
  });

  it('renders a loaded company with its NAIC number', async () => {
    endpoints.insuranceCompanies.mockResolvedValue({
      companies: [{ id: 'c1', name: 'Acme Mutual', kind: 'appointed', naic: '12345' }],
    });
    renderSettings();

    await waitFor(() => {
      expect(screen.getByText('Acme Mutual')).toBeInTheDocument();
    });
    expect(screen.getByText(/Appointed panel/)).toBeInTheDocument();
    expect(screen.getByText(/NAIC 12345/)).toBeInTheDocument();
  });

  it('labels a demo-kind company as "Demo book"', async () => {
    endpoints.insuranceCompanies.mockResolvedValue({
      companies: [{ id: 'c1', name: 'Practice Co', kind: 'demo' }],
    });
    renderSettings();

    await waitFor(() => {
      expect(screen.getByText('Demo book')).toBeInTheDocument();
    });
  });

  it('adds a new appointed company through the form', async () => {
    endpoints.addInsuranceCompany.mockResolvedValue({ id: 'new-1', name: 'New Co', kind: 'appointed' });
    renderSettings();

    await waitFor(() => {
      expect(screen.getByText('No companies loaded.')).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText('Add appointed company');
    fireEvent.change(input, { target: { value: 'New Co' } });
    fireEvent.click(screen.getByText('Add'));

    await waitFor(() => {
      expect(endpoints.addInsuranceCompany).toHaveBeenCalledWith({ name: 'New Co' });
    });
    await waitFor(() => {
      expect(screen.getByText('New Co')).toBeInTheDocument();
    });
  });

  it('shows an inline error when adding a company fails', async () => {
    endpoints.addInsuranceCompany.mockRejectedValue(new Error('Company name taken'));
    renderSettings();

    await waitFor(() => {
      expect(screen.getByText('No companies loaded.')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText('Add appointed company'), { target: { value: 'Dup Co' } });
    fireEvent.click(screen.getByText('Add'));

    await waitFor(() => {
      expect(screen.getByText('Company name taken')).toBeInTheDocument();
    });
  });

  it('disables the Add button until a company name is entered', async () => {
    renderSettings();
    await waitFor(() => {
      expect(screen.getByText('No companies loaded.')).toBeInTheDocument();
    });
    expect(screen.getByText('Add')).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText('Add appointed company'), { target: { value: 'X' } });
    expect(screen.getByText('Add')).not.toBeDisabled();
  });

  it('signs out and reloads when Sign Out is clicked', async () => {
    const reloadSpy = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, reload: reloadSpy },
    });

    renderSettings();
    await waitFor(() => {
      expect(screen.getByText('Sign Out')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Sign Out'));

    expect(auth.clear).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
  });

  it('does not reset credentials when the confirm dialog is dismissed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderSettings();

    await waitFor(() => {
      expect(screen.getByText('Clear all login accounts')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Clear all login accounts'));

    expect(endpoints.authReset).not.toHaveBeenCalled();
  });

  it('resets credentials when confirmed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    endpoints.authReset.mockResolvedValue({ ok: true });
    const onAuthReset = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, href: '' },
    });

    renderSettings({ onAuthReset });
    await waitFor(() => {
      expect(screen.getByText('Clear all login accounts')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Clear all login accounts'));

    await waitFor(() => {
      expect(endpoints.authReset).toHaveBeenCalled();
    });
    expect(auth.wipeSession).toHaveBeenCalled();
    expect(onAuthReset).toHaveBeenCalled();
  });

  it('shows a toast error when reset credentials fails', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    endpoints.authReset.mockRejectedValue(new Error('Server unavailable'));

    renderSettings();
    await waitFor(() => {
      expect(screen.getByText('Clear all login accounts')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Clear all login accounts'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Server unavailable');
    });
  });
});
