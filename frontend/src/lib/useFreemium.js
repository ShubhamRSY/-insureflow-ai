import { useState, useCallback, useEffect } from 'react';

const DAILY_LIMIT = 3;
const STORAGE_KEY = 'rytera_freemium_views';

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function loadViews() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { date: todayKey(), count: 0 };
    const data = JSON.parse(raw);
    if (data.date !== todayKey()) return { date: todayKey(), count: 0 };
    return data;
  } catch {
    return { date: todayKey(), count: 0 };
  }
}

function saveViews(data) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch { /* ignore */ }
}

export function useFreemium(isLoggedIn) {
  const [views, setViews] = useState(() => loadViews());

  useEffect(() => {
    if (isLoggedIn) {
      try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
    }
  }, [isLoggedIn]);

  const remaining = isLoggedIn ? Infinity : Math.max(0, DAILY_LIMIT - views.count);
  const isLimited = !isLoggedIn && remaining <= 0;

  const trackView = useCallback(() => {
    if (isLoggedIn) return true;
    const current = loadViews();
    if (current.count >= DAILY_LIMIT) return false;
    const updated = { date: todayKey(), count: current.count + 1 };
    saveViews(updated);
    setViews(updated);
    return true;
  }, [isLoggedIn]);

  return { remaining, isLimited, trackView, DAILY_LIMIT };
}
