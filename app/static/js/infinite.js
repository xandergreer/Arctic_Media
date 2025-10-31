// app/static/js/infinite.js
(() => {
  const grid = document.getElementById('infinite-grid');
  const sentinel = document.getElementById('infinite-sentinel');
  if (!grid || !sentinel) return;

  const endpoint = grid.dataset.endpoint || '';
  let page = parseInt(grid.dataset.page || '1', 10) || 1;
  let totalPages = parseInt(grid.dataset.totalPages || '1', 10) || 1;
  const pageSize = parseInt(grid.dataset.pageSize || '60', 10) || 60;
  const kind = grid.dataset.kind || 'movie';
  let loading = false;
  const placeholder = '/static/img/placeholder.png';

  function esc(s) {
    return (s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function pickPoster(item) {
    try {
      const ej = item.extra_json || {};
      return ej.poster || item.poster_url || placeholder;
    } catch { return item.poster_url || placeholder; }
  }

  function cardFor(item) {
    const poster = pickPoster(item);
    const href = kind === 'tv' ? `/show/${item.id}` : `/movie/${item.id}`;
    const year = item.year ? `<div class="sub">${String(item.year)}</div>` : '';
    return `<a class="card" href="${href}" title="${esc(item.title || '')}">`
      + `<img loading="lazy" src="${poster}" alt="${esc(item.title || '')}">`
      + `<div class="card-meta"><div class="title">${esc(item.title || '')}</div>${year}</div>`
      + `</a>`;
  }

  async function loadMore() {
    if (loading) return;
    if (page >= totalPages) return;
    loading = true;
    try {
      const nextPage = page + 1;
      const sep = endpoint.includes('?') ? '&' : '?';
      // Get current sort parameter from URL
      const urlParams = new URLSearchParams(window.location.search);
      const sortParam = urlParams.get('sort') ? `&sort=${urlParams.get('sort')}` : '';
      const url = `${endpoint}${sep}page=${nextPage}&page_size=${pageSize}${sortParam}`;
      const resp = await fetch(url, { headers: { 'Accept': 'application/json' }, cache: 'no-store' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const items = data.items || [];
      const frag = document.createElement('div');
      for (const it of items) frag.insertAdjacentHTML('beforeend', cardFor(it));
      grid.append(...Array.from(frag.children));
      page = data.page || nextPage;
      totalPages = data.total_pages || totalPages;
      grid.dataset.page = String(page);
      grid.dataset.totalPages = String(totalPages);
    } catch (e) {
      try { console.warn('[infinite] load failed', e); } catch { }
      page = totalPages; // stop further attempts
    } finally {
      loading = false;
    }
  }

  const io = new IntersectionObserver(entries => {
    for (const ent of entries) if (ent.isIntersecting) loadMore();
  }, { rootMargin: '800px 0px' });
  io.observe(sentinel);
})();
