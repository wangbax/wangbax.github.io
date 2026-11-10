let searchIndexPromise;

function loadSearchIndex() {
  if (searchIndexPromise) return searchIndexPromise;
  searchIndexPromise = fetch(document.body.dataset.searchIndex)
    .then(response => {
      if (!response.ok) throw new Error('Search index unavailable');
      return response.json();
    })
    .then(entries => {
      if (!Array.isArray(entries)) throw new Error('Invalid search index');
      return entries.filter(entry => typeof entry.title === 'string' && typeof entry.content === 'string'
        && typeof entry.url === 'string' && /^\/20\d{2}\/\d{2}\/\d{2}\/[^/]+\/$/.test(entry.url));
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
  }
  if (input.value) search();
}

export function initSearch() {
  document.querySelectorAll('[data-search-widget]').forEach(mountSearch);
}
