import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import RegistryPage from './Registry';

vi.mock('../lib/api', () => ({
  endpoints: {
    registryVersions: vi.fn(),
    registrySnapshots: vi.fn(),
    releaseChecklist: vi.fn(),
    releaseExperiments: vi.fn(),
    registryContexts: vi.fn(),
    createRegistryEntry: vi.fn(),
    submitRegistryEntry: vi.fn(),
    approveRegistryEntry: vi.fn(),
    rejectRegistryEntry: vi.fn(),
    registrySnapshot: vi.fn(),
    registryBootstrap: vi.fn(),
    registryDiff: vi.fn(),
  },
}));

vi.mock('../lib/toast', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
}));

import { endpoints } from '../lib/api';
import { toast } from '../lib/toast';

const draftEntry = {
  entry_id: 'entry-1', component_type: 'prompt', prompt_key: 'uw_decision',
  version_label: '1.0.0', status: 'draft', updated_at: '2026-01-01T00:00:00Z',
};
const reviewEntry = {
  entry_id: 'entry-2', component_type: 'llm_config', model_tier: 'default',
  version_label: '2.0.0', status: 'review', updated_at: '2026-01-02T00:00:00Z',
};

function emptyResponses() {
  endpoints.registryVersions.mockResolvedValue({ entries: [] });
  endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
  endpoints.releaseChecklist.mockResolvedValue(null);
  endpoints.releaseExperiments.mockResolvedValue(null);
  endpoints.registryContexts.mockResolvedValue(null);
}

describe('RegistryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a loading spinner while fetching registry data', () => {
    endpoints.registryVersions.mockReturnValue(new Promise(() => {}));
    endpoints.registrySnapshots.mockReturnValue(new Promise(() => {}));
    endpoints.releaseChecklist.mockReturnValue(new Promise(() => {}));
    endpoints.releaseExperiments.mockReturnValue(new Promise(() => {}));
    endpoints.registryContexts.mockReturnValue(new Promise(() => {}));
    const { container } = render(<RegistryPage />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows an empty state with a Bootstrap action when there are no entries', async () => {
    emptyResponses();
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('No registry entries')).toBeInTheDocument();
    });
    expect(screen.getByText('Bootstrap registry')).toBeInTheDocument();
  });

  it('renders a draft entry with a Submit action', async () => {
    endpoints.registryVersions.mockResolvedValue({ entries: [draftEntry] });
    endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
    endpoints.releaseChecklist.mockResolvedValue(null);
    endpoints.releaseExperiments.mockResolvedValue(null);
    endpoints.registryContexts.mockResolvedValue(null);
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('uw_decision')).toBeInTheDocument();
    });
    expect(screen.getByText('Submit')).toBeInTheDocument();
  });

  it('submits a draft entry for review', async () => {
    endpoints.registryVersions.mockResolvedValue({ entries: [draftEntry] });
    endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
    endpoints.releaseChecklist.mockResolvedValue(null);
    endpoints.releaseExperiments.mockResolvedValue(null);
    endpoints.registryContexts.mockResolvedValue(null);
    endpoints.submitRegistryEntry.mockResolvedValue({ ok: true });
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('Submit')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Submit'));

    await waitFor(() => {
      expect(endpoints.submitRegistryEntry).toHaveBeenCalledWith('entry-1');
    });
  });

  it('renders a review entry with Approve/Reject actions and approves it', async () => {
    endpoints.registryVersions.mockResolvedValue({ entries: [reviewEntry] });
    endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
    endpoints.releaseChecklist.mockResolvedValue(null);
    endpoints.releaseExperiments.mockResolvedValue(null);
    endpoints.registryContexts.mockResolvedValue(null);
    endpoints.approveRegistryEntry.mockResolvedValue({ ok: true });
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('Approve')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Approve'));

    await waitFor(() => {
      expect(endpoints.approveRegistryEntry).toHaveBeenCalledWith('entry-2');
    });
  });

  it('shows a toast error when an entry action fails', async () => {
    endpoints.registryVersions.mockResolvedValue({ entries: [reviewEntry] });
    endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
    endpoints.releaseChecklist.mockResolvedValue(null);
    endpoints.releaseExperiments.mockResolvedValue(null);
    endpoints.registryContexts.mockResolvedValue(null);
    endpoints.rejectRegistryEntry.mockRejectedValue(new Error('Cannot reject'));
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('Reject')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Reject'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Cannot reject');
    });
  });

  it('filters entries by component type', async () => {
    endpoints.registryVersions.mockResolvedValue({ entries: [draftEntry, reviewEntry] });
    endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
    endpoints.releaseChecklist.mockResolvedValue(null);
    endpoints.releaseExperiments.mockResolvedValue(null);
    endpoints.registryContexts.mockResolvedValue(null);
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('uw_decision')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /^LLM Configs/ }));

    expect(screen.queryByText('uw_decision')).not.toBeInTheDocument();
    expect(screen.getByText('default config')).toBeInTheDocument();
  });

  it('takes a snapshot', async () => {
    emptyResponses();
    endpoints.registrySnapshot.mockResolvedValue({ ok: true });
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('Take snapshot')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Take snapshot'));

    await waitFor(() => {
      expect(endpoints.registrySnapshot).toHaveBeenCalled();
    });
  });

  it('bootstraps the registry from the empty state action', async () => {
    emptyResponses();
    endpoints.registryBootstrap.mockResolvedValue({ ok: true });
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('Bootstrap registry')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Bootstrap registry'));

    await waitFor(() => {
      expect(endpoints.registryBootstrap).toHaveBeenCalled();
    });
  });

  it('opens the create-entry form and submits it', async () => {
    emptyResponses();
    endpoints.createRegistryEntry.mockResolvedValue({ ok: true });
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('No registry entries')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('New Entry'));
    expect(screen.getByText('Create registry entry')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('prompt key, e.g. uw_decision'), { target: { value: 'my_prompt' } });
    fireEvent.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(endpoints.createRegistryEntry).toHaveBeenCalledWith(expect.objectContaining({ key: 'my_prompt', component: 'prompt' }));
    });
    await waitFor(() => {
      expect(screen.queryByText('Create registry entry')).not.toBeInTheDocument();
    });
  });

  it('renders release checklist steps when present', async () => {
    endpoints.registryVersions.mockResolvedValue({ entries: [] });
    endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
    endpoints.releaseChecklist.mockResolvedValue({
      summary: 'Ship safely',
      checklist: { steps: [{ id: 's1', step: 1, title: 'Classify change', owner: 'engineer', detail: 'Pick a risk class', required: true }] },
    });
    endpoints.releaseExperiments.mockResolvedValue(null);
    endpoints.registryContexts.mockResolvedValue(null);
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('Classify change')).toBeInTheDocument();
    });
    expect(screen.getByText('Ship safely')).toBeInTheDocument();
    expect(screen.getByText('required')).toBeInTheDocument();
  });

  it('renders experiment runs when present', async () => {
    endpoints.registryVersions.mockResolvedValue({ entries: [] });
    endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
    endpoints.releaseChecklist.mockResolvedValue(null);
    endpoints.releaseExperiments.mockResolvedValue({
      experiment_name: 'uw-decision-v2',
      summary: { total_runs: 1, by_class: { minor: 1 } },
      runs: [{ run_id: 'run-1', name: 'Prompt tweak', experiment_class: 'minor', stage: 'canary', metrics: { accuracy: 0.91 }, created_at: '2026-01-01T00:00:00Z' }],
    });
    endpoints.registryContexts.mockResolvedValue(null);
    render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('Prompt tweak')).toBeInTheDocument();
    });
    expect(screen.getByText('accuracy=0.910')).toBeInTheDocument();
  });

  it('opens the diff viewer and compares two versions', async () => {
    endpoints.registryVersions.mockResolvedValue({ entries: [draftEntry, reviewEntry] });
    endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
    endpoints.releaseChecklist.mockResolvedValue(null);
    endpoints.releaseExperiments.mockResolvedValue(null);
    endpoints.registryContexts.mockResolvedValue(null);
    endpoints.registryDiff.mockResolvedValue({ component_type: 'prompt', from_version: '1.0.0', to_version: '2.0.0' });
    const { container } = render(<RegistryPage />);

    await waitFor(() => {
      expect(screen.getByText('uw_decision')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Diff'));
    expect(screen.getByText('Diff viewer')).toBeInTheDocument();

    const [selectA, selectB] = container.querySelectorAll('.glass-card select');
    fireEvent.change(selectA, { target: { value: 'entry-1' } });
    fireEvent.change(selectB, { target: { value: 'entry-2' } });
    fireEvent.click(screen.getByText('Compare'));

    await waitFor(() => {
      expect(endpoints.registryDiff).toHaveBeenCalledWith('entry-1', 'entry-2');
    });
    await waitFor(() => {
      expect(screen.getByText('v1.0.0 → v2.0.0')).toBeInTheDocument();
    });
  });

  it('recovers gracefully when one of the parallel feeds rejects', async () => {
    endpoints.registryVersions.mockReturnValue(Promise.reject(new Error('feed down')));
    endpoints.registrySnapshots.mockResolvedValue({ snapshots: [] });
    endpoints.releaseChecklist.mockResolvedValue(null);
    endpoints.releaseExperiments.mockResolvedValue(null);
    endpoints.registryContexts.mockResolvedValue(null);
    render(<RegistryPage />);

    // Each feed has its own .catch() fallback, so one failing feed doesn't blank the page.
    await waitFor(() => {
      expect(screen.getByText('No registry entries')).toBeInTheDocument();
    });
  });
});
