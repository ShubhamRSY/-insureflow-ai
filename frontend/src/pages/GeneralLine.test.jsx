import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import GeneralLinePage from './GeneralLine';

vi.mock('../lib/api', () => ({
  endpoints: {
    generalInsuranceLine: vi.fn(),
  },
}));

vi.mock('../components/RunSelector', () => ({
  default: () => <div data-testid="run-selector">RunSelector</div>,
}));

import { endpoints } from '../lib/api';

const mockLineData = {
  id: 'home_structure',
  name: 'Homeowners — Structure Cover',
  short_name: 'Home Structure',
  slug: 'home-structure',
  description: 'Covers the physical structure of the home against covered perils.',
  insurance_line: 'personal_property',
  checklist_lob: 'personal_property',
  category_id: 'general',
  acord_forms: ['ACORD 4'],
  documents: ['Application', 'Property Inspection Report'],
  base_packet: ['Signed application', 'Proof of ownership'],
  coverages: [{ id: 'dwelling', name: 'Dwelling' }],
  uw_focus: 'Assess structural risk based on construction type, age, and location.',
  uw_question: 'Is the structure insurable at standard rates given its condition?',
  uw_responsibilities: [
    { id: 'prop', title: 'Property UW', summary: 'Review inspection report and construction details.' },
  ],
  checklist_template: { missing: ['Application', 'Property Inspection Report'] },
};

function renderLine(slug = 'home_structure', props = {}) {
  return render(
    <MemoryRouter initialEntries={[`/insurance/general/${slug}`]}>
      <Routes>
        <Route path="/insurance/general/:lobSlug" element={<GeneralLinePage presets={[]} onRunDemo={vi.fn()} onSubmit={vi.fn()} {...props} />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('GeneralLinePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching line data', () => {
    endpoints.generalInsuranceLine.mockReturnValue(new Promise(() => {}));
    const { container } = renderLine();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders the line name and description after data loads', async () => {
    endpoints.generalInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Homeowners — Structure Cover')).toBeInTheDocument();
    });
    expect(screen.getByText('Covers the physical structure of the home against covered perils.')).toBeInTheDocument();
  });

  it('renders the "Personal Lines" eyebrow label', async () => {
    endpoints.generalInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Personal Lines')).toBeInTheDocument();
    });
  });

  it('fetches the line by its slug param', async () => {
    endpoints.generalInsuranceLine.mockResolvedValue(mockLineData);
    renderLine('home_structure');

    await waitFor(() => {
      expect(endpoints.generalInsuranceLine).toHaveBeenCalledWith('home_structure');
    });
  });

  it('renders ACORD forms when present', async () => {
    endpoints.generalInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('ACORD 4')).toBeInTheDocument();
    });
  });

  it('renders the Document pack tab by default', async () => {
    endpoints.generalInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Document pack')).toBeInTheDocument();
    });
    expect(screen.getByText('Application')).toBeInTheDocument();
    expect(screen.getByText('Property Inspection Report')).toBeInTheDocument();
  });

  it('switches to the Underwriter Focus tab and shows its content', async () => {
    endpoints.generalInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /underwriter focus/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('tab', { name: /underwriter focus/i }));

    expect(screen.getByText(/Assess structural risk/)).toBeInTheDocument();
    expect(screen.getByText('Property UW')).toBeInTheDocument();
    // Document Pack content is hidden once we've switched tabs.
    expect(screen.queryByText('Application')).not.toBeInTheDocument();
  });

  it('renders the Checklist tab with the correct present/required count', async () => {
    endpoints.generalInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /checklist/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('tab', { name: /checklist/i }));

    expect(screen.getByText('0 / 2')).toBeInTheDocument();
  });

  it('renders the Start Submission section and RunSelector', async () => {
    endpoints.generalInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText(/Start submission — Home Structure/)).toBeInTheDocument();
    });
    expect(screen.getByTestId('run-selector')).toBeInTheDocument();
  });

  it('shows an error state and a link back to the general hub when the line fails to load', async () => {
    endpoints.generalInsuranceLine.mockRejectedValue(new Error('Line not found'));
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Line not found')).toBeInTheDocument();
    });
    const link = screen.getByText('Back to general hub');
    expect(link).toHaveAttribute('href', '/insurance/general');
  });

  it('falls back to a generic error message when none is provided', async () => {
    endpoints.generalInsuranceLine.mockRejectedValue(new Error());
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Line not found')).toBeInTheDocument();
    });
  });
});
