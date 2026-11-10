(() => {
  'use strict';

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
      const code = pre.innerText;
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
    const media = image.closest('picture') || image;
    link.href = image.dataset.original || image.currentSrc || image.src;
    link.className = 'article-image-link';
    link.target = '_blank';
    link.rel = 'noopener';
    link.setAttribute('aria-label', '查看大图' + (image.alt ? '：' + image.alt : ''));
    media.before(link);
    link.append(media);
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
