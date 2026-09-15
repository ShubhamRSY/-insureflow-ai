import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SignupPage from './SignupPage';

vi.mock('../lib/api', () => ({
  auth: { isLoggedIn: false, token: null, user: null },
  endpoints: {
    signup: vi.fn(),
    me: vi.fn(),
  },
}));

import { auth, endpoints } from '../lib/api';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/dashboard/signup']}>
      <Routes>
        <Route path="/dashboard/signup" element={<SignupPage />} />
        <Route path="/dashboard" element={<div>Dashboard home</div>} />
      </Routes>
    </MemoryRouter>
  );
}

function fillStep1() {
  fireEvent.change(screen.getByPlaceholderText('Company / Organization name'), { target: { value: 'Acme Co' } });
  fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'jdoe' } });
  fireEvent.change(screen.getByPlaceholderText('Work email'), { target: { value: 'jdoe@acme.com' } });
  fireEvent.change(screen.getByPlaceholderText(/Password \(min 8 chars/), { target: { value: 'Str0ng!Pass' } });
  fireEvent.click(screen.getByText('Continue'));
}

describe('SignupPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.isLoggedIn = false;
    auth.token = null;
    auth.user = null;
  });

  it('renders the account details step first', () => {
    renderPage();
    expect(screen.getByText('Account Details')).toBeInTheDocument();
  });

  it('redirects to the dashboard when already logged in', async () => {
    auth.isLoggedIn = true;
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Dashboard home')).toBeInTheDocument();
    });
  });

  it('shows an error when required fields are missing on submit', async () => {
    const { container } = renderPage();
    // fireEvent.submit bypasses the browser's native "required" constraint
    // validation (which a real click would honor), exercising the
    // component's own belt-and-suspenders validation check directly.
    fireEvent.submit(container.querySelector('form'));

    await waitFor(() => {
      expect(screen.getByText('All fields are required')).toBeInTheDocument();
    });
  });

  it('advances to the plan-selection step once account details are valid', async () => {
    renderPage();
    fillStep1();

    await waitFor(() => {
      expect(screen.getByText('Choose Your Plan')).toBeInTheDocument();
    });
    expect(screen.getByText('Free')).toBeInTheDocument();
    expect(screen.getByText('Enterprise')).toBeInTheDocument();
  });

  it('selects a plan and goes back to step 1', async () => {
    renderPage();
    fillStep1();

    await waitFor(() => {
      expect(screen.getByText('Pro')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Pro').closest('button'));
    fireEvent.click(screen.getByText('Back'));

    expect(screen.getByText('Account Details')).toBeInTheDocument();
  });

  it('creates the account and shows the API key on success', async () => {
    endpoints.signup.mockResolvedValue({ token: 'tok-1', api_key: 'key-123' });
    endpoints.me.mockResolvedValue({ username: 'jdoe' });
    renderPage();
    fillStep1();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Create Account'));

    await waitFor(() => {
      expect(screen.getByText('Welcome to InsureFlow!')).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue('key-123')).toBeInTheDocument();
    expect(auth.token).toBe('tok-1');
    expect(auth.user).toEqual({ username: 'jdoe' });
  });

  it('shows an error message when account creation fails', async () => {
    endpoints.signup.mockRejectedValue(new Error('Username already taken'));
    renderPage();
    fillStep1();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Create Account'));

    await waitFor(() => {
      expect(screen.getByText('Username already taken')).toBeInTheDocument();
    });
  });

  it('navigates to the dashboard from the success step', async () => {
    endpoints.signup.mockResolvedValue({ token: 'tok-1', api_key: 'key-123' });
    endpoints.me.mockResolvedValue({ username: 'jdoe' });
    renderPage();
    fillStep1();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Create Account'));

    await waitFor(() => {
      expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Go to Dashboard'));

    await waitFor(() => {
      expect(screen.getByText('Dashboard home')).toBeInTheDocument();
    });
  });
});
