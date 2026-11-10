(() => {
  'use strict';

  const themePicker = document.querySelector('[data-theme-picker]');
  if (themePicker && window.siteTheme) {
    const trigger = themePicker.querySelector('summary');
    const options = themePicker.querySelectorAll('[data-theme-option]');
    const labels = { light: '明亮模式', dark: '夜间模式', system: '跟随系统' };
    function syncThemePicker() {
      const label = '外观模式：' + labels[window.siteTheme.mode];
      trigger.setAttribute('aria-label', label);
      trigger.title = label;
      options.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.themeOption === window.siteTheme.mode)));
    }
    options.forEach(button => button.addEventListener('click', () => {
      window.siteTheme.setMode(button.dataset.themeOption);
      themePicker.open = false;
      trigger.focus({ preventScroll: true });
    }));
    document.addEventListener('click', event => {
      if (!themePicker.contains(event.target)) themePicker.open = false;
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && themePicker.open) {
        themePicker.open = false;
        trigger.focus({ preventScroll: true });
      }
    });
    addEventListener('themechange', syncThemePicker);
    syncThemePicker();
  }

  let searchModulePromise;
  function prepareSearch() {
    if (!searchModulePromise) {
      searchModulePromise = import(document.body.dataset.searchModule)
        .then(module => module.initSearch())
        .catch(() => {
          searchModulePromise = undefined;
          document.querySelectorAll('[data-search-status]').forEach(status => {
            status.textContent = '搜索暂时无法使用，请刷新页面后重试。';
          });
        });
    }
    return searchModulePromise;
  }
  if (document.getElementById('page-search')) prepareSearch();
  const dialog = document.getElementById('site-search');
  let searchOpener;
  function openSearch(opener) {
    if (!dialog || dialog.open) return;
    if (themePicker) themePicker.open = false;
    searchOpener = opener || document.activeElement;
    prepareSearch();
    dialog.showModal();
    dialog.querySelector('input').focus();
  }
  document.querySelectorAll('[data-open-search]').forEach(button => button.addEventListener('click', () => openSearch(button)));
  if (dialog) {
    dialog.addEventListener('close', () => searchOpener?.focus());
    dialog.addEventListener('click', event => {
      const rect = dialog.getBoundingClientRect();
      if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
    });
  }
  document.addEventListener('keydown', event => {
    const editing = event.target instanceof Element && event.target.closest('input, textarea, [contenteditable="true"]');
    if ((event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey)) || (event.key === '/' && !editing && !event.metaKey && !event.ctrlKey && !event.altKey)) {
      event.preventDefault();
      openSearch();
    }
  });

  const planet = document.querySelector('[data-planet-module]');
  if (planet) {
    const load = () => import(planet.dataset.planetModule).catch(error => console.warn('星球效果暂时未加载', error));
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if ('requestIdleCallback' in window) requestIdleCallback(load, { timeout: 1200 });
      else setTimeout(load, 0);
    }));
  }
})();
