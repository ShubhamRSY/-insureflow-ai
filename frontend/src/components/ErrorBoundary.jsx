import { Component } from 'react';

/** Keeps chrome mounted when a page throws (otherwise React blanks the whole screen). */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error) {
    // eslint-disable-next-line no-console
    console.error('Page render failed', error);
  }

  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  render() {
    if (this.state.error) {
      const message = this.state.error?.message || String(this.state.error);
      return (
        <div
          className="mx-auto flex min-h-[40vh] max-w-lg flex-col items-center justify-center rounded-2xl border border-red-500/30 bg-red-950/40 p-8 text-center"
          style={{ color: '#e2e8f0' }}
        >
          <p className="text-sm font-semibold text-red-400">This page could not be displayed</p>
          <p className="mt-2 text-sm text-slate-300">
            The submission loaded, but the desk view hit a display error. Your data is still saved — go back and reopen, or try again.
          </p>
          <p className="mt-3 break-all font-mono text-[11px] text-slate-400">{message}</p>
          <button
            type="button"
            className="btn-secondary btn-sm mt-5"
            onClick={() => this.setState({ error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
