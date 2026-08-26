import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import {
  PageBack,
  Badge,
  DecisionBadge,
  StatCard,
  EmptyState,
  DemoCard,
} from './ui';

function withRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('PageBack', () => {
  it('renders with the given label', () => {
    withRouter(<PageBack to="/insurance" label="All insurance" />);
    expect(screen.getByText('All insurance')).toBeInTheDocument();
  });

  it('navigates when clicked', () => {
    withRouter(<PageBack to="/insurance/life" label="Life hub" />);
    const btn = screen.getByText('Life hub');
    expect(btn.closest('button')).toHaveAttribute('type', 'button');
  });

  it('renders the ArrowLeft icon', () => {
    const { container } = withRouter(<PageBack to="/" label="Back" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});

describe('Badge', () => {
  it('renders the status text', () => {
    render(<Badge status="ok" />);
    expect(screen.getByText('ok')).toBeInTheDocument();
  });

  it('renders a custom label', () => {
    render(<Badge status="ok" label="Approved" />);
    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('returns null when no status', () => {
    const { container } = render(<Badge status={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('applies correct color class for "completed"', () => {
    render(<Badge status="completed" />);
    const badge = screen.getByText('completed');
    expect(badge.className).toContain('emerald');
  });

  it('applies correct color class for "failed"', () => {
    render(<Badge status="failed" />);
    const badge = screen.getByText('failed');
    expect(badge.className).toContain('red');
  });

  it('applies correct color class for "pending"', () => {
    render(<Badge status="pending" />);
    const badge = screen.getByText('pending');
    expect(badge.className).toContain('amber');
  });

  it('shows pulse animation when pulse prop is true', () => {
    render(<Badge status="ok" pulse />);
    const badge = screen.getByText('ok');
    expect(badge.querySelector('.animate-pulse-soft')).toBeInTheDocument();
  });

  it('shows pulse animation for processing status', () => {
    render(<Badge status="processing" />);
    const badge = screen.getByText('processing');
    expect(badge.querySelector('.animate-pulse-soft')).toBeInTheDocument();
  });
});

describe('DecisionBadge', () => {
  it('shows processing badge when jobStatus is processing', () => {
    render(<DecisionBadge jobStatus="processing" />);
    expect(screen.getByText('processing')).toBeInTheDocument();
  });

  it('shows dash when jobStatus is failed', () => {
    render(<DecisionBadge jobStatus="failed" />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('shows dash when no decision and jobStatus is not processing', () => {
    render(<DecisionBadge decision={null} jobStatus="completed" />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('renders badge with decision value', () => {
    render(<DecisionBadge decision="approved" jobStatus="completed" />);
    expect(screen.getByText('approved')).toBeInTheDocument();
  });
});

describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="Policies" value="142" />);
    expect(screen.getByText('Policies')).toBeInTheDocument();
    expect(screen.getByText('142')).toBeInTheDocument();
  });

  it('renders sub text when provided', () => {
    render(<StatCard label="Premium" value="$1.2M" sub="Year to date" />);
    expect(screen.getByText('Year to date')).toBeInTheDocument();
  });

  it('does not render sub when not provided', () => {
    render(<StatCard label="Count" value="5" />);
    expect(screen.queryByText(/Year/)).not.toBeInTheDocument();
  });
});

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No results" description="Try adjusting filters" />);
    expect(screen.getByText('No results')).toBeInTheDocument();
    expect(screen.getByText('Try adjusting filters')).toBeInTheDocument();
  });

  it('renders action when provided', () => {
    render(
      <EmptyState
        title="Empty"
        action={<button>Add item</button>}
      />,
    );
    expect(screen.getByText('Add item')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    const MockIcon = () => <svg data-testid="mock-icon" />;
    render(<EmptyState icon={MockIcon} title="No data" />);
    expect(screen.getByTestId('mock-icon')).toBeInTheDocument();
  });
});

describe('DemoCard', () => {
  it('renders name, description, and tag', () => {
    render(
      <DemoCard
        name="Life Demo"
        description="Test the life pipeline"
        tag="LIFE"
        onClick={vi.fn()}
      />,
    );
    expect(screen.getByText('Life Demo')).toBeInTheDocument();
    expect(screen.getByText('Test the life pipeline')).toBeInTheDocument();
    expect(screen.getByText('LIFE')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(
      <DemoCard name="Demo" description="Desc" onClick={onClick} />,
    );
    fireEvent.click(screen.getByText('Demo'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('is disabled when loading', () => {
    render(
      <DemoCard name="Demo" description="Desc" onClick={vi.fn()} loading />,
    );
    expect(screen.getByText('Demo').closest('button')).toBeDisabled();
  });

  it('applies tag color class', () => {
    render(
      <DemoCard name="Demo" description="Desc" tag="INSURANCE" tagColor="insurance" onClick={vi.fn()} />,
    );
    const tag = screen.getByText('INSURANCE');
    expect(tag.className).toContain('text-insurance');
  });
});
