import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CommercialLinePage from './CommercialLine';

vi.mock('../lib/api', () => ({
  endpoints: {
    commercialInsuranceLine: vi.fn(),
  },
}));

vi.mock('../components/RunSelector', () => ({
  default: () => <div data-testid="run-selector">RunSelector</div>,
}));

import { endpoints } from '../lib/api';

const mockLineData = {
  id: 'workers_comp',
  name: 'Workers Compensation',
  short_name: 'Workers Comp',
  slug: 'workers-comp',
  description: 'Covers employee injury and occupational illness claims.',
  insurance_line: 'workers_comp',
  checklist_lob: 'workers_comp',
  category_id: 'commercial',
  acord_forms: ['ACORD 130'],
  documents: ['Application', 'Loss runs', 'Payroll report'],
  base_packet: ['Signed application', 'Experience mod worksheet'],
  coverages: [{ id: 'wc', name: 'Statutory' }],
  uw_focus: 'Evaluate class codes, experience mod, and safety programs.',
  uw_question: 'Is the risk within appetite for this class of business?',
  uw_responsibilities: [
    { id: 'safety', title: 'Safety review', summary: 'Assess workplace safety program.' },
  ],
  checklist_template: { missing: ['Application', 'Loss runs', 'Payroll report'] },
};

function renderLine(slug = 'workers_comp', props = {}) {
  return render(
    <MemoryRouter initialEntries={[`/insurance/commercial/${slug}`]}>
      <Routes>
        <Route path="/insurance/commercial/:lobSlug" element={<CommercialLinePage presets={[]} onRunDemo={vi.fn()} onSubmit={vi.fn()} {...props} />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('CommercialLinePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching line data', () => {
    endpoints.commercialInsuranceLine.mockReturnValue(new Promise(() => {}));
    const { container } = renderLine();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders the line name and description after data loads', async () => {
    endpoints.commercialInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Workers Compensation')).toBeInTheDocument();
    });
    expect(screen.getByText('Covers employee injury and occupational illness claims.')).toBeInTheDocument();
  });

  it('renders the "Business / Commercial" eyebrow label', async () => {
    endpoints.commercialInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Business / Commercial')).toBeInTheDocument();
    });
  });

  it('fetches the line by its slug param', async () => {
    endpoints.commercialInsuranceLine.mockResolvedValue(mockLineData);
    renderLine('workers_comp');

    await waitFor(() => {
      expect(endpoints.commercialInsuranceLine).toHaveBeenCalledWith('workers_comp');
    });
  });

  it('renders the Document pack tab by default', async () => {
    endpoints.commercialInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Document pack')).toBeInTheDocument();
    });
    expect(screen.getByText('Loss runs')).toBeInTheDocument();
    expect(screen.getByText('Payroll report')).toBeInTheDocument();
  });

  it('switches to the Base Packet tab and shows its content', async () => {
    endpoints.commercialInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /base packet/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('tab', { name: /base packet/i }));

    expect(screen.getByText('Experience mod worksheet')).toBeInTheDocument();
  });

  it('renders the Checklist tab with the correct present/required count', async () => {
    endpoints.commercialInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /checklist/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('tab', { name: /checklist/i }));

    expect(screen.getByText('0 / 3')).toBeInTheDocument();
  });

  it('renders the Start Submission section and RunSelector', async () => {
    endpoints.commercialInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText(/Start submission — Workers Comp/)).toBeInTheDocument();
    });
    expect(screen.getByTestId('run-selector')).toBeInTheDocument();
  });

  it('shows an error state and a link back to the commercial hub when the line fails to load', async () => {
    endpoints.commercialInsuranceLine.mockRejectedValue(new Error('Line not found'));
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Line not found')).toBeInTheDocument();
    });
    const link = screen.getByText('Back to commercial hub');
    expect(link).toHaveAttribute('href', '/insurance/commercial');
  });
});
