export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'theme';

/** Read the saved theme, defaulting to dark. */
export function getStoredTheme(): Theme {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === 'light' ? 'light' : 'dark';
}

/** Apply a theme to the document root and persist it. */
export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(STORAGE_KEY, theme);
}

/** Initialise the theme on first load (call before render). */
export function initTheme(): void {
  document.documentElement.setAttribute('data-theme', getStoredTheme());
}
