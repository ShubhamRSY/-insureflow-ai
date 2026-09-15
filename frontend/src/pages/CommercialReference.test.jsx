import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CommercialReference from './CommercialReference';

vi.mock('../lib/api', () => ({
  endpoints: {
    commercialInsuranceHub: vi.fn(),
  },
}));

import { endpoints } from '../lib/api';

const hub = {
  stats: { product_count: 2 },
  lines: [{ insurance_line: 'workers_comp', name: 'Workers Compensation' }],
  taxonomy: [
    {
      id: 'property',
      name: 'Property',
      products: [
        { id: 'workers_comp', name: 'Workers Compensation', short_name: 'Workers Comp', insurance_line: 'workers_comp', slug: 'workers-comp', all_documents: ['Application', 'Payroll report'] },
        { id: 'property_bi', name: 'Property & Business Interruption', insurance_line: 'property_bi', slug: 'property-bi', all_documents: ['SOV'] },
      ],
    },
  ],
  base_packet: ['Signed application', 'Loss runs'],
  uw_responsibilities: [{ id: 'r1', title: 'Financial review', summary: 'Assess financial strength.' }],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <CommercialReference />
    </MemoryRouter>
  );
}

describe('CommercialReference', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching the hub', () => {
    endpoints.commercialInsuranceHub.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an error message when the hub fails to load', async () => {
    endpoints.commercialInsuranceHub.mockRejectedValue(new Error('Hub unavailable'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Hub unavailable')).toBeInTheDocument();
    });
  });

  it('renders the live lines list with the first line pre-selected', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue(hub);
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Workers Compensation').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('Payroll report')).toBeInTheDocument();
  });

  it('switches the document pack when a different live line is selected', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue({
      ...hub,
      lines: [...hub.lines, { insurance_line: 'property_bi', name: 'Property & BI' }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Property & BI')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Property & BI'));

    expect(screen.getByText('SOV')).toBeInTheDocument();
    expect(screen.queryByText('Payroll report')).not.toBeInTheDocument();
  });

  it('filters the product-line taxonomy by search query', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue(hub);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Property')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Property'));
    expect(screen.getByText('Workers Comp')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Search products…'), { target: { value: 'business interruption' } });

    expect(screen.queryByText('Workers Comp')).not.toBeInTheDocument();
  });

  it('expands the base submission packet section', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue(hub);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Base submission packet')).toBeInTheDocument();
    });
    expect(screen.queryByText('Signed application')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Base submission packet'));
    expect(screen.getByText('Signed application')).toBeInTheDocument();
  });

  it('expands the UW responsibilities section', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue(hub);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('UW responsibilities')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('UW responsibilities'));

    expect(screen.getByText('Financial review')).toBeInTheDocument();
    expect(screen.getByText('Assess financial strength.')).toBeInTheDocument();
  });

  it('links to the full line detail page for the selected product', async () => {
    endpoints.commercialInsuranceHub.mockResolvedValue(hub);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Full line detail')).toBeInTheDocument();
    });
    expect(screen.getByText('Full line detail')).toHaveAttribute('href', '/insurance/commercial/workers-comp');
  });
});
