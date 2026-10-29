import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import { ThemeProvider } from './components/ThemeProvider';
import { applyThemeClass, readThemePreference, resolvedTheme } from './lib/theme';
import './index.css';

applyThemeClass(resolvedTheme(readThemePreference()));

// After a deploy, a tab opened earlier asks for page files that no longer exist.
// Reload once to pick up the new version; the 10s guard stops a reload loop.
window.addEventListener('vite:preloadError', (event) => {
  let last = 0;
  try { last = Number(sessionStorage.getItem('rytera:chunk-reload')) || 0; } catch { /* storage blocked */ }
  if (Date.now() - last < 10000) return;
  try { sessionStorage.setItem('rytera:chunk-reload', String(Date.now())); } catch { /* storage blocked */ }
  event.preventDefault();
  window.location.reload();
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </ThemeProvider>
  </React.StrictMode>,
);
