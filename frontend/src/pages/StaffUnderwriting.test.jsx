import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import StaffUnderwriting from './StaffUnderwriting';

vi.mock('../lib/api', () => ({
  endpoints: {
    staffOverview: vi.fn(),
    staffSection: vi.fn(),
    staffMarketResearch: vi.fn(),
    staffCoverageDev: vi.fn(),
    staffExperience: vi.fn(),
    staffRatingPlans: vi.fn(),
    staffGuides: vi.fn(),
    staffAudits: vi.fn(),
    staffTraining: vi.fn(),
  },
}));

import { endpoints } from '../lib/api';

function renderPage() {
  return render(
    <MemoryRouter>
      <StaffUnderwriting />
    </MemoryRouter>
  );
}

describe('StaffUnderwriting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    endpoints.staffOverview.mockResolvedValue({
      counts: { market_research: 3, coverage_development: 1 },
      tasks: ['Review Q3 loss ratios', 'Publish updated CGL guide'],
    });
    endpoints.staffSection.mockResolvedValue({ items: [] });
  });

  it('renders overview counts and tasks by default', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    expect(screen.getByText('Review Q3 loss ratios')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('switches to the market research tab and loads its section items', async () => {
    endpoints.staffSection.mockResolvedValue({
      items: [{ note_id: 'n1', title: 'Cyber appetite expansion', topic: 'product_mix', summary: 'Considering broader cyber appetite' }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Market'));

    await waitFor(() => {
      expect(endpoints.staffSection).toHaveBeenCalledWith('market_research');
    });
    await waitFor(() => {
      expect(screen.getByText('Cyber appetite expansion')).toBeInTheDocument();
    });
  });

  it('submits a market research note', async () => {
    endpoints.staffMarketResearch.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Market'));

    await waitFor(() => {
      expect(screen.getByText('Research the market')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText('Title'), { target: { value: 'New market note' } });
    fireEvent.change(screen.getByPlaceholderText('Summary'), { target: { value: 'A summary' } });
    fireEvent.click(screen.getByText('Save research note'));

    await waitFor(() => {
      expect(endpoints.staffMarketResearch).toHaveBeenCalledWith(expect.objectContaining({ title: 'New market note', summary: 'A summary' }));
    });
  });

  it('shows an error when saving a market research note fails', async () => {
    endpoints.staffMarketResearch.mockRejectedValue(new Error('Save failed'));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Market'));

    await waitFor(() => {
      expect(screen.getByText('Research the market')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText('Title'), { target: { value: 'X' } });
    fireEvent.change(screen.getByPlaceholderText('Summary'), { target: { value: 'Y' } });
    fireEvent.click(screen.getByText('Save research note'));

    await waitFor(() => {
      expect(screen.getByText('Save failed')).toBeInTheDocument();
    });
  });

  it('analyzes underwriting experience and shows the loss-ratio comparison', async () => {
    endpoints.staffExperience.mockResolvedValue({
      strategy: 'monitor', loss_ratio: 0.62, industry_loss_ratio: 0.65, delta_vs_industry: -0.03,
      narrative: 'Book is running better than industry.',
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Experience'));

    await waitFor(() => {
      expect(screen.getByText('Analyze experience')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Analyze experience'));

    await waitFor(() => {
      expect(screen.getByText('LR 62.0%')).toBeInTheDocument();
    });
    expect(screen.getByText('Book is running better than industry.')).toBeInTheDocument();
  });

  it('shows an empty state for the guides tab before any items exist', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('UW guides'));

    await waitFor(() => {
      expect(screen.getByText('No guides yet')).toBeInTheDocument();
    });
  });

  it('shows readable status badges instead of blank ones for coverage items', async () => {
    endpoints.staffSection.mockResolvedValue({
      items: [{ item_id: 'c1', title: 'Add cyber endorsement', change_type: 'endorsement', status: 'in_review', description: 'Draft cyber endorsement language' }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Coverages'));

    await waitFor(() => {
      expect(screen.getByText('Add cyber endorsement')).toBeInTheDocument();
    });
    expect(screen.getByText('In review')).toBeInTheDocument();
  });

  it('shows the rating action badge and advisory org for rating reviews', async () => {
    endpoints.staffSection.mockResolvedValue({
      items: [{ review_id: 'r1', line_of_business: 'commercial_property', advisory_org: 'ISO', action: 'revise', summary: 'Loss costs trending up' }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Rating plans'));

    await waitFor(() => {
      expect(screen.getByText('commercial_property')).toBeInTheDocument();
    });
    expect(screen.getByText('Revise')).toBeInTheDocument();
    expect(screen.getAllByText('ISO').length).toBeGreaterThan(0);
  });

  it('shows the finding count and compliance score for audits', async () => {
    endpoints.staffSection.mockResolvedValue({
      items: [{
        audit_id: 'a1', office: 'Southwest Regional', scope: 'Documentation review', files_reviewed: 12,
        compliant_pct: 83, findings: [{ severity: 'minor', category: 'documentation', detail: 'Missing signature' }],
      }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('UW audits'));

    await waitFor(() => {
      expect(screen.getByText('Southwest Regional')).toBeInTheDocument();
    });
    expect(screen.getByText('83%')).toBeInTheDocument();
    expect(screen.getByText(/12 files reviewed/)).toBeInTheDocument();
    expect(screen.getByText(/1 finding\(s\)/)).toBeInTheDocument();
  });

  it('submits an underwriting audit with parsed findings', async () => {
    endpoints.staffAudits.mockResolvedValue({ ok: true });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Staff underwriting tasks')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('UW audits'));

    await waitFor(() => {
      expect(screen.getByText('Record audit')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText('Findings (one per line)'), { target: { value: 'Missing signed application\nRating class mismatch' } });
    fireEvent.click(screen.getByText('Record audit'));

    await waitFor(() => {
      expect(endpoints.staffAudits).toHaveBeenCalledWith(expect.objectContaining({
        findings: [
          { severity: 'minor', category: 'documentation', detail: 'Missing signed application' },
          { severity: 'minor', category: 'documentation', detail: 'Rating class mismatch' },
        ],
      }));
    });
  });
});
