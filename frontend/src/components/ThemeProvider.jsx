import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  applyThemeClass,
  persistThemePreference,
  readThemePreference,
  resolvedTheme,
} from '../lib/theme';

const ThemeContext = createContext({
  preference: 'auto',
  resolved: 'dark',
  setPreference: () => {},
});

export function ThemeProvider({ children }) {
  const [preference, setPref] = useState(readThemePreference);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  const resolved = useMemo(() => resolvedTheme(preference, now), [preference, now]);

  useEffect(() => {
    applyThemeClass(resolved);
  }, [resolved]);

  const setPreference = useCallback((next) => {
    setPref(next);
    persistThemePreference(next);
  }, []);

  return (
    <ThemeContext.Provider value={{ preference, resolved, setPreference }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
