import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import HealthLinePage from './HealthLine';

vi.mock('../lib/api', () => ({
  endpoints: {
    healthInsuranceLine: vi.fn(),
  },
}));

vi.mock('../components/RunSelector', () => ({
  default: () => <div data-testid="run-selector">RunSelector</div>,
}));

import { endpoints } from '../lib/api';

const mockLineData = {
  id: 'individual_basic',
  name: 'Individual Health — Basic',
  short_name: 'Individual Basic',
  slug: 'individual-basic',
  description: 'Standalone individual health cover with basic hospitalization benefits.',
  insurance_line: 'health',
  checklist_lob: 'health',
  category_id: 'health',
  acord_forms: [],
  documents: ['Application', 'Medical questionnaire'],
  base_packet: ['Signed application'],
  coverages: [{ id: 'basic', name: 'Basic hospitalization' }],
  uw_focus: 'Assess pre-existing conditions and medical history.',
  uw_question: 'Is the applicant insurable at standard rates given disclosed history?',
  uw_responsibilities: [
    { id: 'med', title: 'Medical UW', summary: 'Review medical questionnaire responses.' },
  ],
  checklist_template: { missing: ['Application', 'Medical questionnaire'] },
};

function renderLine(slug = 'individual_basic', props = {}) {
  return render(
    <MemoryRouter initialEntries={[`/insurance/health/${slug}`]}>
      <Routes>
        <Route path="/insurance/health/:lobSlug" element={<HealthLinePage presets={[]} onRunDemo={vi.fn()} onSubmit={vi.fn()} {...props} />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('HealthLinePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching line data', () => {
    endpoints.healthInsuranceLine.mockReturnValue(new Promise(() => {}));
    const { container } = renderLine();
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders the line name and description after data loads', async () => {
    endpoints.healthInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Individual Health — Basic')).toBeInTheDocument();
    });
    expect(screen.getByText('Standalone individual health cover with basic hospitalization benefits.')).toBeInTheDocument();
  });

  it('renders the "Health Insurance" eyebrow label', async () => {
    endpoints.healthInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Health Insurance')).toBeInTheDocument();
    });
  });

  it('fetches the line by its slug param', async () => {
    endpoints.healthInsuranceLine.mockResolvedValue(mockLineData);
    renderLine('individual_basic');

    await waitFor(() => {
      expect(endpoints.healthInsuranceLine).toHaveBeenCalledWith('individual_basic');
    });
  });

  it('does not render an ACORD forms line when none are present', async () => {
    endpoints.healthInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Individual Health — Basic')).toBeInTheDocument();
    });
    expect(screen.queryByText(/ACORD/)).not.toBeInTheDocument();
  });

  it('renders the Document pack tab by default', async () => {
    endpoints.healthInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Document pack')).toBeInTheDocument();
    });
    expect(screen.getByText('Medical questionnaire')).toBeInTheDocument();
  });

  it('switches to the Underwriter Focus tab and shows its content', async () => {
    endpoints.healthInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /underwriter focus/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('tab', { name: /underwriter focus/i }));

    expect(screen.getByText(/Assess pre-existing conditions/)).toBeInTheDocument();
    expect(screen.getByText('Medical UW')).toBeInTheDocument();
  });

  it('renders the Checklist tab with the correct present/required count', async () => {
    endpoints.healthInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /checklist/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('tab', { name: /checklist/i }));

    expect(screen.getByText('0 / 2')).toBeInTheDocument();
  });

  it('renders the Start Submission section and RunSelector', async () => {
    endpoints.healthInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText(/Start submission — Individual Basic/)).toBeInTheDocument();
    });
    expect(screen.getByTestId('run-selector')).toBeInTheDocument();
  });

  it('shows an error state and a link back to the health hub when the line fails to load', async () => {
    endpoints.healthInsuranceLine.mockRejectedValue(new Error('Line not found'));
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Line not found')).toBeInTheDocument();
    });
    const link = screen.getByText('Back to health hub');
    expect(link).toHaveAttribute('href', '/insurance/health');
  });
});
