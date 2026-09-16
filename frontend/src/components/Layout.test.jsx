import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Layout from './Layout';
import { StateProvider } from '../lib/useStateContext';

beforeEach(() => {
  vi.stubGlobal('localStorage', {
    getItem: vi.fn().mockReturnValue(''),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <StateProvider>
        <Layout
          health={null}
          pendingCount={0}
          onRefresh={() => {}}
          onLogin={() => {}}
          user={null}
          setUser={() => {}}
          isLimited={false}
          welcomeMessage={null}
          onDismissWelcome={() => {}}
        />
      </StateProvider>
    </MemoryRouter>
  );
}

describe('Layout nav panel', () => {
  it('shows the UW operations panel with Queue active at /queue', () => {
    renderAt('/queue');
    expect(screen.getByText('UW operations')).toBeInTheDocument();
    const queueLink = screen.getByText('Queue').closest('a');
    expect(queueLink).toHaveClass('nav-link-active');
  });

  it('hub-matches the Life Insurance nav item at /insurance/life', () => {
    renderAt('/insurance/life');
    const lifeLink = screen.getByText('1. Life Insurance').closest('a');
    expect(lifeLink).toHaveClass('nav-link-active');
  });
});
