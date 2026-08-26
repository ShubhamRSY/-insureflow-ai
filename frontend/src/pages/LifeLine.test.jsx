import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import LifeLinePage from './LifeLine';

vi.mock('../lib/api', () => ({
  endpoints: {
    lifeInsuranceLine: vi.fn(),
  },
}));

vi.mock('../components/RunSelector', () => ({
  default: (props) => (
    <div data-testid="run-selector">
      RunSelector
    </div>
  ),
}));

import { endpoints } from '../lib/api';

const mockLineData = {
  id: 'level_term',
  name: 'Level Term Life Insurance',
  short_name: 'Level Term',
  slug: 'level-term',
  description: 'Coverage for a fixed period at a fixed premium.',
  insurance_line: 'term_life',
  checklist_lob: 'term_life',
  category_id: 'life',
  acord_forms: ['AT161', 'AT162'],
  documents: ['Application', 'Paramedical Exam', 'APS', 'MIB Report'],
  base_packet: ['Signed application', 'Premium payment'],
  coverages: [{ id: '50k', name: '$50,000' }],
  uw_focus: 'Evaluate mortality risk based on age, health, and lifestyle.',
  uw_question: 'Is the applicant insurable at standard rates?',
  uw_responsibilities: [
    { id: 'med', title: 'Medical UW', summary: 'Review health history and exam results.' },
    { id: 'fin', title: 'Financial UW', summary: 'Verify income and coverage need.' },
  ],
  checklist_template: { missing: ['Application', 'Paramedical Exam'] },
};

function renderLine(slug = 'level_term', props = {}) {
  return render(
    <MemoryRouter initialEntries={[`/insurance/life/${slug}`]}>
      <Routes>
        <Route path="/insurance/life/:lobSlug" element={<LifeLinePage presets={[]} onRunDemo={vi.fn()} onSubmit={vi.fn()} {...props} />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('LifeLinePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching line data', () => {
    endpoints.lifeInsuranceLine.mockReturnValue(new Promise(() => {}));
    const { container } = renderLine();

    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders the line name and description after data loads', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Level Term Life Insurance')).toBeInTheDocument();
    });
    expect(screen.getByText('Coverage for a fixed period at a fixed premium.')).toBeInTheDocument();
  });

  it('renders the "Life Insurance" label above the name', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Level Term Life Insurance')).toBeInTheDocument();
    });
    expect(screen.getByText('Life Insurance')).toBeInTheDocument();
  });

  it('renders PageBack link to life hub', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Life insurance hub')).toBeInTheDocument();
    });
  });

  it('renders ACORD forms when present', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('AT161 · AT162')).toBeInTheDocument();
    });
  });

  it('does not render ACORD forms section when empty', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue({ ...mockLineData, acord_forms: [] });
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Level Term Life Insurance')).toBeInTheDocument();
    });
    expect(screen.queryByText(/AT16/)).not.toBeInTheDocument();
  });

  it('renders the Document pack section with numbered items', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Document pack')).toBeInTheDocument();
    });
    expect(screen.getByText('Application')).toBeInTheDocument();
    expect(screen.getByText('Paramedical Exam')).toBeInTheDocument();
    expect(screen.getByText('APS')).toBeInTheDocument();
    expect(screen.getByText('MIB Report')).toBeInTheDocument();
  });

  it('renders the Base packet section', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Base packet (keep ready)')).toBeInTheDocument();
    });
    expect(screen.getByText('Signed application')).toBeInTheDocument();
    expect(screen.getByText('Premium payment')).toBeInTheDocument();
  });

  it('renders the Underwriter focus section', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Underwriter focus')).toBeInTheDocument();
    });
    expect(screen.getByText('Evaluate mortality risk based on age, health, and lifestyle.')).toBeInTheDocument();
  });

  it('renders the UW question in italics', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText(/Is the applicant insurable at standard rates\?/)).toBeInTheDocument();
    });
  });

  it('renders UW responsibilities', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Medical UW')).toBeInTheDocument();
    });
    expect(screen.getByText('Review health history and exam results.')).toBeInTheDocument();
    expect(screen.getByText('Financial UW')).toBeInTheDocument();
    expect(screen.getByText('Verify income and coverage need.')).toBeInTheDocument();
  });

  it('renders the Checklist template section with correct count', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Checklist template')).toBeInTheDocument();
    });
    expect(screen.getByText('0 / 2')).toBeInTheDocument();
  });

  it('renders Start submission section with short_name', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByText(/Start submission — Level Term/)).toBeInTheDocument();
    });
  });

  it('renders RunSelector when selection is ready', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue(mockLineData);
    renderLine();

    await waitFor(() => {
      expect(screen.getByTestId('run-selector')).toBeInTheDocument();
    });
  });

  it('shows error state when API fails', async () => {
    endpoints.lifeInsuranceLine.mockRejectedValue(new Error('Line not found'));
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Line not found')).toBeInTheDocument();
    });
    expect(screen.getByText('Back to life hub')).toBeInTheDocument();
  });

  it('error state links back to life hub', async () => {
    endpoints.lifeInsuranceLine.mockRejectedValue(new Error('fail'));
    renderLine();

    await waitFor(() => {
      const link = screen.getByText('Back to life hub');
      expect(link).toHaveAttribute('href', '/insurance/life');
    });
  });

  it('uses HeartPulse icon as default when line id is not in LOB_ICONS', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue({ ...mockLineData, id: 'unknown_product' });
    const { container } = renderLine();

    await waitFor(() => {
      expect(screen.getByText('Level Term Life Insurance')).toBeInTheDocument();
    });
    const iconContainer = container.querySelector('.bg-rose-500\\/15');
    expect(iconContainer).toBeInTheDocument();
  });

  it('uses Shield icon for whole_life product', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue({ ...mockLineData, id: 'whole_life' });
    const { container } = renderLine('whole_life');

    await waitFor(() => {
      expect(screen.getByText('Level Term Life Insurance')).toBeInTheDocument();
    });
    const iconContainer = container.querySelector('.bg-rose-500\\/15');
    expect(iconContainer).toBeInTheDocument();
  });

  it('renders empty documents gracefully', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue({ ...mockLineData, documents: [] });
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Level Term Life Insurance')).toBeInTheDocument();
    });
    const checklist = screen.getByText('Checklist template').closest('section');
    expect(checklist).toHaveTextContent(/present \/ required for this line/);
  });

  it('renders empty base_packet gracefully', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue({ ...mockLineData, base_packet: [] });
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Base packet (keep ready)')).toBeInTheDocument();
    });
  });

  it('renders empty uw_responsibilities gracefully', async () => {
    endpoints.lifeInsuranceLine.mockResolvedValue({ ...mockLineData, uw_responsibilities: [] });
    renderLine();

    await waitFor(() => {
      expect(screen.getByText('Underwriter focus')).toBeInTheDocument();
    });
  });
});
