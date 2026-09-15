import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import LendingPage from './Lending';

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual('../lib/api');
  return {
    ...actual,
    endpoints: {
      lendingProducts: vi.fn(),
      runLending: vi.fn(),
    },
  };
});

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

vi.mock('../lib/useStateContext', () => ({
  useStateContext: () => ({ selectedState: null }),
}));

vi.mock('../components/RunSelector', () => ({
  default: ({ onSubmit, onRunResult }) => (
    <div>
      <button type="button" onClick={() => onSubmit({ some: 'body' })}>SubmitRunSelector</button>
      <button type="button" onClick={() => onRunResult({ application_id: 'app-connect', result: { decision: 'approve' }, documents_ingested: 2 })}>ConnectRunSelector</button>
    </div>
  ),
}));

vi.mock('../components/StageStrip', () => ({
  default: () => <div data-testid="stage-strip">StageStrip</div>,
  stagesFromProgress: () => [],
}));

import { endpoints } from '../lib/api';

function renderPage(props = {}) {
  return render(<LendingPage presets={{ lending: [] }} demoResult={null} onRunDemo={vi.fn()} {...props} />);
}

describe('LendingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    endpoints.lendingProducts.mockResolvedValue({});
  });

  it('renders the page heading', () => {
    renderPage();
    expect(screen.getByText('Lending Underwriting')).toBeInTheDocument();
  });

  it('shows an empty state when there are no results', () => {
    renderPage();
    expect(screen.getByText('No lending runs yet')).toBeInTheDocument();
  });

  it('adds a demoResult to the results table on mount', () => {
    renderPage({ demoResult: { application_id: 'app-demo', decision: 'approve', documents_ingested: 3 } });
    expect(screen.getByText('app-demo')).toBeInTheDocument();
  });

  it('submits via RunSelector and shows the decision result', async () => {
    endpoints.runLending.mockResolvedValue({ application_id: 'app-1', result: { decision: 'approve', approved_rate: 6.5, approved_amount: 50000 }, documents_ingested: 2 });
    renderPage();

    fireEvent.click(screen.getByText('SubmitRunSelector'));

    await waitFor(() => {
      expect(screen.getByText('app-1')).toBeInTheDocument();
    });
    expect(screen.getByText('6.50%')).toBeInTheDocument();
    expect(screen.getByText(/Underwrite: approve/)).toBeInTheDocument();
  });

  it('shows an error message when submit fails', async () => {
    endpoints.runLending.mockRejectedValue(new Error('Underwriting failed'));
    renderPage();

    fireEvent.click(screen.getByText('SubmitRunSelector'));

    await waitFor(() => {
      expect(screen.getByText('Underwriting failed')).toBeInTheDocument();
    });
  });

  it('adds a Connect & pull result to the results table', async () => {
    renderPage();
    fireEvent.click(screen.getByText('ConnectRunSelector'));

    await waitFor(() => {
      expect(screen.getByText('app-connect')).toBeInTheDocument();
    });
    expect(screen.getByText(/Connect & pull: approve/)).toBeInTheDocument();
  });

  it('loads and displays lending products', async () => {
    endpoints.lendingProducts.mockResolvedValue({ products: [{ name: 'SBA 7(a)', description: 'Small business loan' }] });
    renderPage();

    fireEvent.click(screen.getByText('Products'));

    await waitFor(() => {
      expect(screen.getByText('SBA 7(a)')).toBeInTheDocument();
    });
    expect(screen.getByText('Small business loan')).toBeInTheDocument();
  });

  it('shows curated quick samples when present in presets', () => {
    renderPage({ presets: { lending: [{ id: 'blue-harbor-bakery', name: 'Blue Harbor Bakery', description: 'Sample', product_type: 'business_term_loan' }] } });
    expect(screen.getByText('Blue Harbor Bakery')).toBeInTheDocument();
  });

  it('runs a quick sample demo on click', () => {
    const onRunDemo = vi.fn();
    renderPage({ onRunDemo, presets: { lending: [{ id: 'keller-logistics', name: 'Keller Logistics', description: 'Sample', product_type: 'business_term_loan' }] } });
    fireEvent.click(screen.getByText('Keller Logistics'));
    expect(onRunDemo).toHaveBeenCalledWith('lending', 'keller-logistics');
  });
});
