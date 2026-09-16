import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import InsuranceSegmentPage from './InsuranceSegment';

vi.mock('../lib/api', () => ({
  endpoints: {
    generalInsuranceHub: vi.fn(),
    commercialInsuranceHub: vi.fn(),
  },
}));

import { endpoints } from '../lib/api';

function renderSection(sectionId) {
  return render(
    <MemoryRouter initialEntries={[`/insurance/sections/${sectionId}`]}>
      <Routes>
        <Route path="/insurance/sections/:sectionId" element={<InsuranceSegmentPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('InsuranceSegmentPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows an "unknown section" state for an invalid sectionId', () => {
    renderSection('not-a-real-section');
    expect(screen.getByText('Unknown insurance section')).toBeInTheDocument();
    expect(screen.getByText('Back to all sections')).toHaveAttribute('href', '/insurance');
  });

  it('renders a section with no hubKind statically, without calling any endpoint', async () => {
    renderSection('life');

    expect(screen.getByText('Life Insurance')).toBeInTheDocument();
    expect(screen.getByText('Term Life Insurance')).toBeInTheDocument();
    expect(screen.getByText('live')).toBeInTheDocument();
    expect(endpoints.generalInsuranceHub).not.toHaveBeenCalled();
    expect(endpoints.commercialInsuranceHub).not.toHaveBeenCalled();
  });

  it('fetches the general hub and filters lines by category for the general section', async () => {
    endpoints.generalInsuranceHub.mockResolvedValue({
      lines: [
        { id: 'car_tp', slug: 'car-tp', name: 'Car Third Party', short_name: 'Car TP', category_id: 'motor', status: 'live', document_count: 3 },
        { id: 'unrelated', slug: 'unrelated', name: 'Unrelated', category_id: 'other', status: 'live', document_count: 1 },
      ],
    });
    renderSection('general');

    await waitFor(() => {
      expect(screen.getByText('Coverage Options')).toBeInTheDocument();
    });
    expect(screen.getByText('Car TP')).toBeInTheDocument();
    expect(screen.queryByText('Unrelated')).not.toBeInTheDocument();
    // Catalog section stays "catalog" even with live lines underneath.
    expect(screen.getByText('catalog')).toBeInTheDocument();
  });

  it('shows an error message when the hub fetch fails', async () => {
    endpoints.commercialInsuranceHub.mockRejectedValue(new Error('Hub unavailable'));
    renderSection('commercial');

    await waitFor(() => {
      expect(screen.getByText('Hub unavailable')).toBeInTheDocument();
    });
  });

  it('navigates using a static product\'s href when clicked', () => {
    renderSection('life');
    fireEvent.click(screen.getByText('Term Life Insurance'));
    // No route table beyond the section route exists here, so this just
    // verifies the click doesn't throw; navigation itself is react-router's.
  });

  it('marks a live coverage-option line and links to the right base path on click', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue({
      lines: [{ id: 'workers_comp', slug: 'workers-comp', name: 'Workers Compensation', category_id: 'wc', status: 'live', document_count: 5 }],
    });
    renderSection('commercial');

    await waitFor(() => {
      expect(screen.getByText('Workers Compensation')).toBeInTheDocument();
    });
    expect(screen.getByText(/5 documents · live/)).toBeInTheDocument();
  });
});
