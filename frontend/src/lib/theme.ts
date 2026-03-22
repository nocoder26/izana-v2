export type Theme = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'izana_theme';

/**
 * Read the saved theme preference from localStorage.
 * Falls back to 'system' when storage is unavailable or empty.
 */
export function getTheme(): Theme {
  if (typeof window === 'undefined') return 'system';
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
  } catch {
    // localStorage unavailable (SSR, private browsing edge cases)
  }
  return 'system';
}

/**
 * Persist theme preference and apply it immediately.
 */
export function setTheme(theme: Theme): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // silently fail
  }
  applyTheme(theme);
}

/**
 * Resolve the effective color mode and set data-theme on <html>.
 */
export function applyTheme(theme?: Theme): void {
  if (typeof window === 'undefined') return;

  const resolved = theme ?? getTheme();
  const root = document.documentElement;

  if (resolved === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
  } else {
    root.setAttribute('data-theme', resolved);
  }
}

/**
 * Listen for OS-level color-scheme changes so 'system' stays in sync.
 * Returns an unsubscribe function.
 */
export function listenForSystemThemeChanges(onResolvedChange?: (resolved: 'light' | 'dark') => void): () => void {
  if (typeof window === 'undefined') return () => {};

  const mq = window.matchMedia('(prefers-color-scheme: dark)');

  const handler = (e: MediaQueryListEvent) => {
    const current = getTheme();
    if (current === 'system') {
      const resolved = e.matches ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', resolved);
      onResolvedChange?.(resolved);
    }
  };

  mq.addEventListener('change', handler);
  return () => mq.removeEventListener('change', handler);
}
