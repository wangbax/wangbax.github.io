// Run before stylesheets so the first paint already uses the chosen appearance.
(() => {
  'use strict';
  const key = 'wangbax.theme';
  const modes = ['system', 'light', 'dark'];
  const system = matchMedia('(prefers-color-scheme: dark)');
  const root = document.documentElement;
  let mode = 'system';
  let storage;
  try {
    storage = localStorage;
    const saved = storage.getItem(key);
    if (modes.includes(saved)) mode = saved;
  } catch { /* Storage may be disabled; switching still works for this page. */ }

  function apply() {
    const theme = mode === 'system' ? (system.matches ? 'dark' : 'light') : mode;
    root.dataset.theme = theme;
    root.dataset.themeMode = mode;
    root.style.colorScheme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#25221f' : '#faf7f1');
    dispatchEvent(new CustomEvent('themechange', { detail: { mode, theme } }));
  }

  window.siteTheme = {
    get mode() { return mode; },
    setMode(value) {
      if (!modes.includes(value)) return;
      mode = value;
      try {
        if (mode === 'system') storage?.removeItem(key);
        else storage?.setItem(key, mode);
      } catch { /* Keep the current page usable without persistent storage. */ }
      apply();
    }
  };
  system.addEventListener('change', () => { if (mode === 'system') apply(); });
  addEventListener('storage', event => {
    if (event.storageArea !== storage || (event.key !== key && event.key !== null)) return;
    mode = modes.includes(event.newValue) ? event.newValue : 'system';
    apply();
  });
  apply();
})();
