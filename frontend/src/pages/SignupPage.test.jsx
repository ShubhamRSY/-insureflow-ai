import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SignupPage from './SignupPage';

vi.mock('../lib/api', () => ({
  auth: { isLoggedIn: false, token: null, user: null },
  endpoints: {
    signup: vi.fn(),
    me: vi.fn(),
    startCheckout: vi.fn(),
    confirmCheckout: vi.fn(),
    cancelCheckout: vi.fn(),
  },
}));

import { auth, endpoints } from '../lib/api';

function renderPage(props = {}) {
  return render(
    <MemoryRouter initialEntries={['/dashboard/signup']}>
      <Routes>
        <Route path="/dashboard/signup" element={<SignupPage {...props} />} />
        <Route path="/" element={<div>Dashboard home</div>} />
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

  it('tells the app the new user is signed in', async () => {
    endpoints.signup.mockResolvedValue({ token: 'tok-1', api_key: 'key-123' });
    endpoints.me.mockResolvedValue({ username: 'jdoe' });
    const onSignedIn = vi.fn();
    renderPage({ onSignedIn });
    fillStep1();
    await waitFor(() => expect(screen.getByText('Create Account')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Create Account'));
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledWith({ username: 'jdoe' }));
  });

  it('confirms when the API key is copied', async () => {
    endpoints.signup.mockResolvedValue({ token: 'tok-1', api_key: 'key-123' });
    endpoints.me.mockResolvedValue({ username: 'jdoe' });
    document.execCommand = vi.fn(() => true);
    renderPage();
    fillStep1();
    await waitFor(() => expect(screen.getByText('Create Account')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Create Account'));
    await waitFor(() => expect(screen.getByText('Copy')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Copy'));
    await waitFor(() => expect(screen.getByText('✓ API key copied')).toBeInTheDocument());
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

  it('routes a paid plan through checkout instead of creating it directly', async () => {
    endpoints.signup.mockResolvedValue({ token: 'tok-1', api_key: 'key-123', org_id: 'org-1' });
    endpoints.me.mockResolvedValue({ username: 'jdoe' });
    endpoints.startCheckout.mockResolvedValue({ checkout_id: 'chk_1', tier: 'pro', amount_due: 999, currency: 'USD', status: 'pending' });
    renderPage();
    fillStep1();

    await waitFor(() => {
      expect(screen.getByText('Pro')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Pro').closest('button'));
    fireEvent.click(screen.getByText('Continue to payment'));

    await waitFor(() => {
      expect(screen.getByText('Checkout')).toBeInTheDocument();
    });
    expect(endpoints.startCheckout).toHaveBeenCalledWith({ tier: 'pro' });
    expect(screen.getByText('Pay & create account')).toBeInTheDocument();
  });

  it('completes checkout and activates the paid plan', async () => {
    endpoints.signup.mockResolvedValue({ token: 'tok-1', api_key: 'key-123', org_id: 'org-1' });
    endpoints.me.mockResolvedValue({ username: 'jdoe' });
    endpoints.startCheckout.mockResolvedValue({ checkout_id: 'chk_1', tier: 'pro', amount_due: 999, currency: 'USD', status: 'pending' });
    endpoints.confirmCheckout.mockResolvedValue({ checkout_id: 'chk_1', status: 'completed', tier: 'pro', plan_status: 'active' });
    renderPage();
    fillStep1();

    await waitFor(() => {
      expect(screen.getByText('Pro')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Pro').closest('button'));
    fireEvent.click(screen.getByText('Continue to payment'));

    await waitFor(() => {
      expect(screen.getByText('Pay & create account')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText('Name on card'), { target: { value: 'Jane Buyer' } });
    fireEvent.change(screen.getByPlaceholderText('Card number'), { target: { value: '4242424242424242' } });
    fireEvent.change(screen.getByPlaceholderText('MM/YY'), { target: { value: '12/30' } });
    fireEvent.change(screen.getByPlaceholderText('CVC'), { target: { value: '123' } });
    fireEvent.click(screen.getByText('Pay & create account'));

    await waitFor(() => {
      expect(screen.getByText('Welcome to InsureFlow!')).toBeInTheDocument();
    });
    expect(endpoints.confirmCheckout).toHaveBeenCalledWith('chk_1', expect.objectContaining({ card_number: '4242424242424242' }));
  });

  it('shows a checkout error when the card is rejected', async () => {
    endpoints.signup.mockResolvedValue({ token: 'tok-1', api_key: 'key-123', org_id: 'org-1' });
    endpoints.me.mockResolvedValue({ username: 'jdoe' });
    endpoints.startCheckout.mockResolvedValue({ checkout_id: 'chk_1', tier: 'starter', amount_due: 299, currency: 'USD', status: 'pending' });
    endpoints.confirmCheckout.mockRejectedValue(new Error('Card number is invalid'));
    renderPage();
    fillStep1();

    await waitFor(() => {
      expect(screen.getByText('Starter')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Starter').closest('button'));
    fireEvent.click(screen.getByText('Continue to payment'));

    await waitFor(() => {
      expect(screen.getByText('Pay & create account')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText('Name on card'), { target: { value: 'Jane Buyer' } });
    fireEvent.change(screen.getByPlaceholderText('Card number'), { target: { value: '1111111111111111' } });
    fireEvent.change(screen.getByPlaceholderText('MM/YY'), { target: { value: '12/30' } });
    fireEvent.change(screen.getByPlaceholderText('CVC'), { target: { value: '123' } });
    fireEvent.click(screen.getByText('Pay & create account'));

    await waitFor(() => {
      expect(screen.getByText('Card number is invalid')).toBeInTheDocument();
    });
  });

  it('ignores a second click while the paid-plan request is in flight', async () => {
    let resolveSignup;
    endpoints.signup.mockImplementation(() => new Promise((resolve) => { resolveSignup = resolve; }));
    endpoints.me.mockResolvedValue({ username: 'jdoe' });
    endpoints.startCheckout.mockResolvedValue({ checkout_id: 'chk_1', tier: 'pro', amount_due: 999, currency: 'USD', status: 'pending' });
    renderPage();
    fillStep1();

    await waitFor(() => {
      expect(screen.getByText('Pro')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Pro').closest('button'));
    const continueBtn = screen.getByText('Continue to payment');
    fireEvent.click(continueBtn);
    fireEvent.click(continueBtn);

    await waitFor(() => {
      expect(endpoints.signup).toHaveBeenCalledTimes(1);
    });

    resolveSignup({ token: 'tok-1', api_key: 'key-123', org_id: 'org-1' });
    await waitFor(() => {
      expect(screen.getByText('Checkout')).toBeInTheDocument();
    });
    expect(endpoints.signup).toHaveBeenCalledTimes(1);
    expect(endpoints.startCheckout).toHaveBeenCalledTimes(1);
  });
});
