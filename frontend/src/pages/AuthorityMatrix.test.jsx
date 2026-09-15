import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useOutletContext } from 'react-router-dom';
import AuthorityMatrix from './AuthorityMatrix';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useOutletContext: vi.fn() };
});

vi.mock('../lib/api', () => ({
  endpoints: {
    authorityMatrix: vi.fn(),
    upsertAuthority: vi.fn(),
    deleteAuthority: vi.fn(),
  },
  fmtCurrency: (n) => (n == null || isNaN(n) ? '—' : `$${Number(n).toLocaleString('en-US')}`),
}));

import { endpoints } from '../lib/api';

const record = {
  username: 'jdoe', display_name: 'Jane Doe', tier: 'senior', desk: 'line', license_number: 'PC-1',
  binding_authority: { max_premium: 250000, max_tiv: 10000000, max_aggregate_exposure: 25000000, requires_co_sign: false, co_sign_threshold_premium: 150000 },
};

function renderPage(role = 'admin') {
  useOutletContext.mockReturnValue({ user: { username: 'me', role } });
  return render(<AuthorityMatrix />);
}

describe('AuthorityMatrix', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching the matrix', () => {
    endpoints.authorityMatrix.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state when there are no authority records', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No authority records')).toBeInTheDocument();
    });
  });

  it('renders an authority record row', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [record] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    });
    expect(screen.getByText('jdoe')).toBeInTheDocument();
    expect(screen.getByText('$250,000')).toBeInTheDocument();
  });

  it('hides admin-only controls for a non-admin user', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [record] });
    renderPage('underwriter');

    await waitFor(() => {
      expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    });
    expect(screen.queryByText('Add Underwriter')).not.toBeInTheDocument();
    expect(screen.queryByText('Admin mode')).not.toBeInTheDocument();
  });

  it('shows admin-only controls for an admin user', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [record] });
    renderPage('admin');

    await waitFor(() => {
      expect(screen.getByText('Add Underwriter')).toBeInTheDocument();
    });
    expect(screen.getByText(/Admin mode/)).toBeInTheDocument();
  });

  it('opens the add-underwriter modal with tier defaults applied', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [] });
    renderPage('admin');

    await waitFor(() => {
      expect(screen.getByText('No authority records')).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText('Add Underwriter')[0]);

    expect(screen.getByRole('heading', { name: 'Add Underwriter' })).toBeInTheDocument();
    expect(screen.getByPlaceholderText('jdoe')).toHaveValue('');
  });

  it('creates a new underwriter', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [] });
    endpoints.upsertAuthority.mockResolvedValue({ ok: true });
    renderPage('admin');

    await waitFor(() => {
      expect(screen.getByText('No authority records')).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText('Add Underwriter')[0]);
    fireEvent.change(screen.getByPlaceholderText('jdoe'), { target: { value: 'newuw' } });
    fireEvent.change(screen.getByPlaceholderText('Jane Doe'), { target: { value: 'New UW' } });
    fireEvent.click(screen.getByText('Add Underwriter', { selector: 'button[type="submit"]' }));

    await waitFor(() => {
      expect(endpoints.upsertAuthority).toHaveBeenCalledWith(expect.objectContaining({ username: 'newuw', display_name: 'New UW', tier: 'junior' }));
    });
  });

  it('opens the edit modal pre-filled with an existing record', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [record] });
    renderPage('admin');

    await waitFor(() => {
      expect(screen.getByTitle('Edit')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTitle('Edit'));

    expect(screen.getByText('Edit Underwriter')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('jdoe')).toHaveValue('jdoe');
    expect(screen.getByPlaceholderText('jdoe')).toBeDisabled();
  });

  it('deletes an authority record after confirmation', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [record] });
    endpoints.deleteAuthority.mockResolvedValue({ ok: true });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage('admin');

    await waitFor(() => {
      expect(screen.getByTitle('Delete')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTitle('Delete'));

    await waitFor(() => {
      expect(endpoints.deleteAuthority).toHaveBeenCalledWith('jdoe');
    });
  });

  it('does not delete when the confirm dialog is dismissed', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [record] });
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderPage('admin');

    await waitFor(() => {
      expect(screen.getByTitle('Delete')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTitle('Delete'));

    expect(endpoints.deleteAuthority).not.toHaveBeenCalled();
  });

  it('shows a tier overview card with the underwriter count', async () => {
    endpoints.authorityMatrix.mockResolvedValue({ authorities: [record, { ...record, username: 'jdoe2' }] });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('underwriters')).toBeInTheDocument();
    });
    expect(screen.getByText('2')).toBeInTheDocument();
  });
});
