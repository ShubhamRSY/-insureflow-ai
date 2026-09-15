import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import SsoCallback from './SsoCallback';

vi.mock('../lib/api', () => ({
  auth: { token: null, user: null },
  endpoints: {
    ssoCallback: vi.fn(),
    me: vi.fn(),
  },
}));

import { auth, endpoints } from '../lib/api';

describe('SsoCallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.token = null;
    auth.user = null;
  });

  afterEach(() => {
    window.history.pushState({}, '', '/');
  });

  it('shows an error when no authorization code is present', async () => {
    window.history.pushState({}, '', '/sso/callback');
    render(<SsoCallback />);

    await waitFor(() => {
      expect(screen.getByText('Missing authorization code from the identity provider.')).toBeInTheDocument();
    });
    expect(endpoints.ssoCallback).not.toHaveBeenCalled();
  });

  it('shows a "signing you in" message while exchanging the code', () => {
    window.history.pushState({}, '', '/sso/callback?code=abc123&state=xyz');
    endpoints.ssoCallback.mockReturnValue(new Promise(() => {}));
    render(<SsoCallback />);
    expect(screen.getByText('Signing you in…')).toBeInTheDocument();
  });

  it('exchanges the code and sets the session on success', async () => {
    window.history.pushState({}, '', '/sso/callback?code=abc123&state=xyz');
    endpoints.ssoCallback.mockResolvedValue({ access_token: 'tok-1' });
    endpoints.me.mockResolvedValue({ username: 'jdoe' });
    render(<SsoCallback />);

    await waitFor(() => {
      expect(endpoints.ssoCallback).toHaveBeenCalledWith({ code: 'abc123', state: 'xyz' });
    });
    await waitFor(() => {
      expect(auth.token).toBe('tok-1');
    });
    expect(auth.user).toEqual({ username: 'jdoe' });
  });

  it('shows an error when the provider does not issue a session', async () => {
    window.history.pushState({}, '', '/sso/callback?code=abc123');
    endpoints.ssoCallback.mockResolvedValue({ error: 'invalid_grant' });
    render(<SsoCallback />);

    await waitFor(() => {
      expect(screen.getByText('invalid_grant')).toBeInTheDocument();
    });
    expect(screen.getByText('Back to sign in')).toBeInTheDocument();
  });

  it('shows an error when the exchange request fails', async () => {
    window.history.pushState({}, '', '/sso/callback?code=abc123');
    endpoints.ssoCallback.mockRejectedValue(new Error('Network error'));
    render(<SsoCallback />);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });
});
