const THEME_KEY = 'rytera-theme';

export const THEME_OPTIONS = [
  { id: 'dark', label: 'Dark' },
  { id: 'light', label: 'Light' },
  { id: 'auto', label: 'Default (time of day)' },
];

export function readThemePreference() {
  try {
    const value = localStorage.getItem(THEME_KEY);
    if (value === 'light' || value === 'dark' || value === 'auto') return value;
  } catch {
    /* ignore */
  }
  return 'auto';
}

export function resolvedTheme(preference, date = new Date()) {
  if (preference === 'light' || preference === 'dark') return preference;
  const hour = date.getHours();
  return hour >= 7 && hour < 19 ? 'light' : 'dark';
}

export function applyThemeClass(resolved) {
  const root = document.documentElement;
  root.classList.toggle('theme-light', resolved === 'light');
  root.classList.toggle('theme-dark', resolved === 'dark');
  root.classList.toggle('dark', resolved === 'dark');
  root.dataset.theme = resolved;
  root.style.colorScheme = resolved;
}

export function persistThemePreference(preference) {
  try {
    localStorage.setItem(THEME_KEY, preference);
  } catch {
    /* ignore */
  }
}
