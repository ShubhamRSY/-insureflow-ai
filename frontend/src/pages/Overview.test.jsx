import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useOutletContext } from 'react-router-dom';
import Overview from './Overview';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useOutletContext: vi.fn() };
});

vi.mock('../components/MarketingShowcase', () => ({
  HeroSection: () => <div data-testid="hero-section">HeroSection</div>,
  SolutionsSection: () => <div data-testid="solutions-section">SolutionsSection</div>,
  AutomationsCatalog: () => <div data-testid="automations-catalog">AutomationsCatalog</div>,
  PlatformStrip: () => <div data-testid="platform-strip">PlatformStrip</div>,
  UnderwriterPlaybook: () => <div data-testid="underwriter-playbook">UnderwriterPlaybook</div>,
}));

vi.mock('../components/JourneyMiniStrip', () => ({
  default: () => <div data-testid="journey-mini-strip">JourneyMiniStrip</div>,
}));

vi.mock('recharts', () => ({
  BarChart: ({ children }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
}));

const baseProps = {
  overview: null,
  health: null,
  presets: { insurance: [], mortgage: [], lending: [] },
  onRunDemo: vi.fn(),
  onOpenJob: vi.fn(),
  onLogin: vi.fn(),
  marketCycle: null,
  queueStats: null,
  insuranceJobs: [],
  isLimited: false,
  remaining: 5,
  trackView: vi.fn(),
};

function renderOverview(props = {}, { user } = { user: null }) {
  useOutletContext.mockReturnValue({ user });
  return render(
    <MemoryRouter>
      <Overview {...baseProps} {...props} />
    </MemoryRouter>
  );
}

describe('Overview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the marketing surface for every visitor', () => {
    renderOverview();
    expect(screen.getByTestId('hero-section')).toBeInTheDocument();
    expect(screen.getByTestId('solutions-section')).toBeInTheDocument();
    expect(screen.getByTestId('automations-catalog')).toBeInTheDocument();
    expect(screen.getByTestId('platform-strip')).toBeInTheDocument();
    expect(screen.getByTestId('underwriter-playbook')).toBeInTheDocument();
  });

  it('calls trackView on mount when provided', () => {
    const trackView = vi.fn();
    renderOverview({ trackView });
    expect(trackView).toHaveBeenCalled();
  });

  it('shows the Preview Mode panel and hides desk shortcuts for a signed-out visitor', () => {
    renderOverview({}, { user: null });
    expect(screen.getByText('Preview Mode')).toBeInTheDocument();
    expect(screen.queryByText('ROI & KPIs')).not.toBeInTheDocument();
    expect(screen.queryByText('Pilot Lab')).not.toBeInTheDocument();
  });

  it('calls onLogin when "Sign in for full access" is clicked', () => {
    const onLogin = vi.fn();
    renderOverview({ onLogin }, { user: null });
    fireEvent.click(screen.getByText('Sign in for full access'));
    expect(onLogin).toHaveBeenCalled();
  });

  it('shows desk shortcuts and Pilot Lab for a signed-in user', () => {
    renderOverview({}, { user: { username: 'jdoe' } });
    expect(screen.getByText('ROI & KPIs')).toBeInTheDocument();
    expect(screen.getByText('Line UW Desk')).toBeInTheDocument();
    expect(screen.getByText('Staff UW Desk')).toBeInTheDocument();
    expect(screen.getByText('Pilot Lab')).toBeInTheDocument();
    expect(screen.queryByText('Preview Mode')).not.toBeInTheDocument();
  });

  it('shows stat cards with overview data for a signed-in user', () => {
    renderOverview(
      {
        overview: { insurance: { total: 12, completed: 9 }, mortgage: { total: 3, completed: 2 }, pending_reviews: 4 },
        health: { overall: 'healthy', llm_mode: 'live' },
      },
      { user: { username: 'jdoe' } }
    );
    expect(screen.getByText('Insurance Jobs')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('9 completed')).toBeInTheDocument();
    expect(screen.getByText('Pending UW')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('shows a sign-in prompt instead of stat cards for a signed-out user', () => {
    renderOverview({}, { user: null });
    expect(screen.getByText('Sign in to access the full dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Insurance Jobs')).not.toBeInTheDocument();
  });

  it('renders the jobs-by-vertical chart only when there is job activity', () => {
    const { rerender } = renderOverview(
      { overview: { insurance: { completed: 0, processing: 0, failed: 0 }, mortgage: { completed: 0, processing: 0, failed: 0 } } },
      { user: { username: 'jdoe' } }
    );
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();

    useOutletContext.mockReturnValue({ user: { username: 'jdoe' } });
    rerender(
      <MemoryRouter>
        <Overview {...baseProps} overview={{ insurance: { completed: 5, processing: 1, failed: 0 }, mortgage: { completed: 0, processing: 0, failed: 0 } }} />
      </MemoryRouter>
    );
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders quick demos for a signed-in user and runs a demo on click', () => {
    const onRunDemo = vi.fn();
    renderOverview(
      { presets: { insurance: [{ id: 'd1', name: 'Sample Submission', description: 'A demo', vertical: 'insurance' }], mortgage: [], lending: [] }, onRunDemo },
      { user: { username: 'jdoe' } }
    );
    expect(screen.getByText('Quick Demos')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Sample Submission'));
    expect(onRunDemo).toHaveBeenCalledWith('insurance', 'd1');
  });

  it('shows "What You Can Do" locked feature list for a signed-out user', () => {
    renderOverview({}, { user: null });
    expect(screen.getByText('What You Can Do')).toBeInTheDocument();
    expect(screen.getByText('Run insurance submissions')).toBeInTheDocument();
  });

  it('renders recent activity and opens a job on click', () => {
    const onOpenJob = vi.fn();
    renderOverview(
      {
        overview: { recent_jobs: [{ job_id: 'job-1', vertical: 'mortgage', status: 'completed' }] },
        onOpenJob,
      },
      { user: { username: 'jdoe' } }
    );
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    fireEvent.click(screen.getByText('job-1'));
    expect(onOpenJob).toHaveBeenCalledWith('mortgage', 'job-1');
  });

  it('shows an empty state when a signed-in user has no recent jobs', () => {
    renderOverview({ overview: { recent_jobs: [] } }, { user: { username: 'jdoe' } });
    expect(screen.getByText('No jobs yet')).toBeInTheDocument();
  });

  it('shows the "Platform Overview" static list for a signed-out user', () => {
    renderOverview({}, { user: null });
    expect(screen.getByText('Platform Overview')).toBeInTheDocument();
    expect(screen.getByText(/14-stage pipeline/)).toBeInTheDocument();
  });

  it('renders the market cycle badge when provided', () => {
    renderOverview({ marketCycle: { phase: 'hard', property_mod: 1.2, liability_mod: 1.1, nuclear_verdict_trend: 'rising' } });
    expect(screen.getByText(/Market: HARD/)).toBeInTheDocument();
  });

  it('renders the queue stats badge when provided', () => {
    renderOverview({ queueStats: { hot_need_review: 2, warm_could_proceed: 3, no_fit_discard: 1 } });
    expect(screen.getByText(/Queue: 2 hot, 3 warm, 1 no-fit/)).toBeInTheDocument();
  });
});
