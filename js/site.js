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

  let searchIndexPromise;

  function loadSearchIndex() {
    if (searchIndexPromise) return searchIndexPromise;
    searchIndexPromise = fetch('/search.xml')
      .then(response => {
        if (!response.ok) throw new Error('Search index unavailable');
        return response.text();
      })
      .then(text => {
        const xml = new DOMParser().parseFromString(text, 'application/xml');
        if (xml.querySelector('parsererror')) throw new Error('Invalid search index');
        return Array.from(xml.querySelectorAll('entry')).flatMap(entry => {
          const title = entry.querySelector('title')?.textContent || '';
          const content = new DOMParser().parseFromString(entry.querySelector('content')?.textContent || '', 'text/html').body.textContent.replace(/\s+/g, ' ').trim();
          let url;
          try { url = decodeURIComponent(entry.querySelector('url')?.textContent || ''); }
          catch { return []; }
          if (!/^\/20\d{2}\/\d{2}\/\d{2}\/[^/]+\/$/.test(url)) return [];
          return [{ title, content, url, date: url.slice(1, 11).replaceAll('/', '-') }];
        });
      })
      .catch(error => {
        searchIndexPromise = undefined;
        throw error;
      });
    return searchIndexPromise;
  }

  function mountSearch(widget) {
    const input = widget.querySelector('[data-search-input]');
    const status = widget.querySelector('[data-search-status]');
    const results = widget.querySelector('[data-search-results]');
    let requestNumber = 0;

    async function search() {
      const request = ++requestNumber;
      const query = input.value.trim();
      results.replaceChildren();
      if (!query) {
        status.textContent = '输入关键词，查找开发手记。';
        return;
      }
      status.textContent = '正在查找…';
      try {
        const entries = await loadSearchIndex();
        if (request !== requestNumber) return;
        const words = query.toLowerCase().split(/\s+/).filter(Boolean);
        const matches = entries.filter(entry => words.every(word => (entry.title + ' ' + entry.content).toLowerCase().includes(word)));
        status.textContent = matches.length ? '找到 ' + matches.length + ' 篇手记' : '没有找到相关手记，试试其他关键词。';
        for (const entry of matches) {
          const link = document.createElement('a');
          link.className = 'search-result';
          link.href = entry.url;
          const time = document.createElement('time');
          time.dateTime = entry.date;
          time.textContent = entry.date;
          const title = document.createElement('h3');
          title.textContent = entry.title;
          const snippet = document.createElement('p');
          const position = entry.content.toLowerCase().indexOf(words[0]);
          const start = Math.max(0, position - 28);
          snippet.textContent = (start ? '…' : '') + entry.content.slice(start, start + 125) + (entry.content.length > start + 125 ? '…' : '');
          link.append(time, title, snippet);
          results.append(link);
        }
      } catch {
        if (request === requestNumber) status.textContent = '搜索暂时没有加载成功，请稍后再试。';
      }
    }

    input.addEventListener('input', search);
    if (input.id === 'page-search') {
      input.value = new URLSearchParams(location.search).get('q') || '';
      if (input.value) search();
    }
    return { input, search };
  }

  document.querySelectorAll('[data-search-widget]').forEach(mountSearch);
  const dialog = document.getElementById('site-search');
  let searchOpener;
  function openSearch(opener) {
    if (!dialog || dialog.open) return;
    if (themePicker) themePicker.open = false;
    searchOpener = opener || document.activeElement;
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

  document.querySelectorAll('.article-body figure.highlight').forEach((figure, index) => {
    const pre = figure.querySelector('.code pre, pre');
    if (!pre) return;
    const scrollArea = pre.closest('table');
    if (scrollArea) {
      scrollArea.tabIndex = 0;
      scrollArea.setAttribute('role', 'region');
      scrollArea.setAttribute('aria-label', '代码，可横向滚动');
    }
    const toolbar = document.createElement('div');
    toolbar.className = 'code-toolbar';
    const language = document.createElement('span');
    language.textContent = (Array.from(figure.classList).find(name => name !== 'highlight') || 'code').toUpperCase();
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = '复制代码';
    button.setAttribute('aria-label', '复制第 ' + (index + 1) + ' 段代码');
    button.setAttribute('aria-live', 'polite');
    let reset;
    button.addEventListener('click', async () => {
      const lines = pre.querySelectorAll('.line');
      const code = lines.length ? Array.from(lines, line => line.textContent).join('\n') : pre.innerText;
      clearTimeout(reset);
      try {
        await navigator.clipboard.writeText(code);
        button.textContent = '已复制';
      } catch {
        button.textContent = '请选中复制';
      }
      reset = setTimeout(() => { button.textContent = '复制代码'; }, 2000);
    });
    toolbar.append(language, button);
    figure.prepend(toolbar);
  });

  document.querySelectorAll('.article-body img').forEach(image => {
    if (image.closest('a')) return;
    const link = document.createElement('a');
    link.href = image.currentSrc || image.src;
    link.className = 'article-image-link';
    link.target = '_blank';
    link.rel = 'noopener';
    link.setAttribute('aria-label', '查看大图' + (image.alt ? '：' + image.alt : ''));
    image.before(link);
    link.append(image);
  });

  document.querySelectorAll('.article-body table').forEach(table => {
    if (table.closest('.highlight')) return;
    const container = document.createElement('div');
    container.className = 'table-scroll';
    container.tabIndex = 0;
    container.setAttribute('role', 'region');
    container.setAttribute('aria-label', '文章表格，可横向滚动');
    table.before(container);
    container.append(table);
  });

  const progress = document.getElementById('reading-progress');
  const progressLabels = document.querySelectorAll('[data-reading-percent]');
  const headings = Array.from(document.querySelectorAll('.article-body h2[id], .article-body h3[id], .article-body h4[id]'));
  const tocLinks = Array.from(document.querySelectorAll('.toc-list a'));
  if (progress) {
    let requested = false;
    function updateReadingPosition() {
      requested = false;
      const distance = document.documentElement.scrollHeight - innerHeight;
      const percent = distance > 0 ? Math.min(100, Math.max(0, scrollY / distance * 100)) : 100;
      progress.style.transform = 'scaleX(' + percent / 100 + ')';
      progressLabels.forEach(label => { label.textContent = Math.round(percent) + '%'; });
      let current = headings[0];
      for (const heading of headings) {
        if (heading.getBoundingClientRect().top <= 135) current = heading;
      }
      for (const link of tocLinks) {
        const active = current && decodeURIComponent(link.hash.slice(1)) === current.id;
        if (active) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      }
    }
    function requestReadingUpdate() {
      if (requested) return;
      requested = true;
      requestAnimationFrame(updateReadingPosition);
    }
    addEventListener('scroll', requestReadingUpdate, { passive: true });
    addEventListener('resize', requestReadingUpdate);
    addEventListener('load', requestReadingUpdate);
    updateReadingPosition();
  }

  document.querySelectorAll('.mobile-toc a').forEach(link => link.addEventListener('click', () => {
    link.closest('details').open = false;
  }));

  const alphaInput = document.getElementById('wt_input');
  if (alphaInput) {
    const output = document.getElementById('wt_result');
    const toggle = document.getElementById('wt_switch');
    const label = document.getElementById('wt_input_label');
    let percent = true;
    function convertAlpha() {
      if (!alphaInput.value.trim()) {
        output.textContent = '—';
        alphaInput.setCustomValidity('');
        return;
      }
      const value = Number(alphaInput.value);
      const max = percent ? 100 : 255;
      if (!Number.isFinite(value) || value < 0 || value > max) {
        output.textContent = '超出范围';
        alphaInput.setCustomValidity('请输入 0–' + max + ' 范围的数值');
        return;
      }
      alphaInput.setCustomValidity('');
      output.textContent = Math.round(percent ? value / 100 * 255 : value).toString(16).padStart(2, '0').toUpperCase();
    }
    alphaInput.addEventListener('input', convertAlpha);
    toggle.addEventListener('click', () => {
      const value = alphaInput.value.trim() ? Number(alphaInput.value) : null;
      const wasPercent = percent;
      percent = !percent;
      alphaInput.max = percent ? '100' : '255';
      label.textContent = percent ? '百分比（0–100）' : '数值（0–255）';
      toggle.textContent = percent ? '切换为 0–255 数值' : '切换为百分比';
      alphaInput.placeholder = percent ? '例如 50' : '例如 128';
      if (value !== null && Number.isFinite(value) && value >= 0 && value <= (wasPercent ? 100 : 255)) {
        alphaInput.value = String(percent ? Math.round(value / 255 * 10000) / 100 : Math.round(value / 100 * 255));
      } else alphaInput.value = '';
      convertAlpha();
    });
  }
})();
