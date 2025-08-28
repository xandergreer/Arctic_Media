// app/static/js/settings_cert_picker.js
// Reusable file picker for selecting certificate/key files in Admin Settings

(function() {
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const isWin = (p) => /^[A-Za-z]:[\\/]/.test(p || '');
  const sepOf = (p) => (isWin(p) ? "\\" : "/");

  let TARGET_INPUT_ID = null;
  let CURRENT_PATH = '';
  let SELECTED_FILE = '';

  // Ensure modal markup exists (inject if missing)
  function ensureModalMarkup() {
    let modal = document.getElementById('fs-modal');
    if (!modal) {
      document.body.insertAdjacentHTML('beforeend',
        '<div id="fs-modal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="fs-title">\
          <div class="modal-card" style="max-width:820px; width:100%;">\
            <header class="modal-header" style="display:flex;align-items:center;justify-content:space-between;gap:12px;">\
              <h3 id="fs-title" class="h3">Choose a file</h3>\
              <button id="fs-close" type="button" class="btn btn-ghost">Close</button>\
            </header>\
            <div class="modal-toolbar" style="display:flex;gap:8px;margin:8px 0;">\
              <select id="fs-roots" class="input" style="width:160px"></select>\
              <input id="fs-path" class="input" type="text" placeholder="C:/  or  F:/certs/cert.pem" style="flex:1;">\
              <button id="fs-go" type="button" class="btn btn-secondary">Go</button>\
            </div>\
            <nav id="fs-bc" class="fs-bc" style="margin:6px 0;display:flex;flex-wrap:wrap;gap:4px;"></nav>\
            <div id="fs-list" class="fs-list" style="margin-top:6px;max-height:50vh;overflow:auto;">\
              <div class="muted">Loading…</div>\
            </div>\
            <footer class="modal-footer" style="margin-top:12px;display:flex;justify-content:flex-end;gap:8px;">\
              <button id="fs-select" type="button" class="btn btn-primary">Select</button>\
            </footer>\
          </div>\
        </div>'
      );
      modal = document.getElementById('fs-modal');
    }
    return modal;
  }

  async function apiRoots() {
    const r = await fetch('/fs/roots', { headers: { 'Accept': 'application/json' }, credentials: 'same-origin', cache: 'no-store' });
    if (!r.ok) throw new Error('roots HTTP ' + r.status);
    const data = await r.json();
    const arr = Array.isArray(data) ? data : (Array.isArray(data?.roots) ? data.roots : []);
    return arr.map(r => (typeof r === 'string')
      ? { path: r, label: r.replace(/[:/\\]+$/, '') }
      : { path: r.path || '', label: r.label || (r.path || '').replace(/[:/\\]+$/, '') }
    ).filter(r => r.path);
  }

  async function apiList(path) {
    const url = new URL('/fs/list', location.origin);
    url.searchParams.set('path', path);
    url.searchParams.set('include_files', 'true');
    url.searchParams.set('include_dirs', 'true');
    const r = await fetch(url, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin', cache: 'no-store' });
    if (!r.ok) throw new Error('list HTTP ' + r.status);
    const raw = await r.json();
    const list = Array.isArray(raw?.entries) ? raw.entries : (Array.isArray(raw?.items) ? raw.items : []);
    return {
      path: raw?.path || path,
      items: list.map(e => ({
        name: e.name || (e.path ? e.path.split(/[\\/]/).pop() : ''),
        path: e.path || '',
        is_dir: e.type ? e.type === 'dir' : (e.is_dir !== false)
      }))
    };
  }

  function renderBreadcrumb(path) {
    const bc = qs('#fs-bc');
    if (!bc) return;
    bc.innerHTML = '';
    if (!path) return;
    const sep = sepOf(path);
    const parts = path.split(/[\\/]+/).filter(Boolean);
    const base = isWin(path) ? parts[0] + sep : '/';
    const mk = (label, target) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'btn btn-ghost';
      b.style.padding = '2px 6px';
      b.textContent = label;
      b.onclick = () => openPath(target);
      return b;
    };
    bc.appendChild(mk(base, base));
    let acc = isWin(path) ? base : '';
    for (let i = (isWin(path) ? 1 : 0); i < parts.length; i++) {
      const sepEl = document.createElement('span');
      sepEl.textContent = '›';
      sepEl.style.margin = '0 4px';
      bc.appendChild(sepEl);
      acc = acc ? (acc.endsWith(sep) ? acc + parts[i] : acc + sep + parts[i]) : parts[i];
      bc.appendChild(mk(parts[i], acc));
    }
  }

  function renderList(items) {
    const listEl = qs('#fs-list');
    const pathInp = qs('#fs-path');
    if (!listEl) return;
    listEl.innerHTML = '';
    if (!items.length) {
      listEl.innerHTML = '<div class="muted" style="padding:10px;">(Empty)</div>';
      return;
    }
    for (const it of items) {
      const row = document.createElement('div');
      row.className = 'fs-row';
      row.style.cssText = 'display:flex;gap:8px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--border,#333)';
      const icon = document.createElement('span');
      icon.className = 'icon';
      icon.textContent = it.is_dir ? '📁' : '📄';
      row.appendChild(icon);
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'link';
      btn.style.cssText = 'background:none;border:0;color:var(--link,#7fb0ff);cursor:pointer;padding:0;font:inherit;text-align:left;';
      btn.textContent = it.name || it.path;
      if (it.is_dir) {
        btn.onclick = () => openPath(it.path);
      } else {
        btn.onclick = () => { SELECTED_FILE = it.path; highlightSelection(it.path); };
        btn.ondblclick = () => { SELECTED_FILE = it.path; applySelection(); };
      }
      row.appendChild(btn);
      listEl.appendChild(row);
    }
    // If user typed a path directly, reflect it
    if (pathInp && pathInp.value && !pathInp.value.endsWith('/') && !pathInp.value.endsWith('\\')) {
      SELECTED_FILE = pathInp.value;
      highlightSelection(SELECTED_FILE);
    }
  }

  function highlightSelection(path) {
    const listEl = qs('#fs-list');
    if (!listEl) return;
    [...listEl.querySelectorAll('.fs-row')].forEach(row => row.style.background = '');
    const matchBtn = [...listEl.querySelectorAll('button.link')].find(b => (b.textContent || '') === (path.split(/[\\/]/).pop() || path));
    if (matchBtn) matchBtn.parentElement.style.background = '#1f1f1f';
  }

  async function openPath(path) {
    const listEl = qs('#fs-list');
    const pathInp = qs('#fs-path');
    if (!listEl) return;
    listEl.innerHTML = '<div class="muted" style="padding:10px;">Loading…</div>';
    try {
      const data = await apiList(path);
      CURRENT_PATH = data.path || path;
      if (pathInp) pathInp.value = CURRENT_PATH;
      SELECTED_FILE = '';
      renderBreadcrumb(CURRENT_PATH);
      renderList(data.items);
    } catch (e) {
      listEl.innerHTML = `<pre style="padding:10px;white-space:pre-wrap">${String(e)}</pre>`;
    }
  }

  function showModal() { qs('#fs-modal')?.classList.remove('hidden'); }
  function hideModal() { qs('#fs-modal')?.classList.add('hidden'); }

  async function bootPicker() {
    // Load roots and open first
    const rootsSel = qs('#fs-roots');
    const listEl = qs('#fs-list');
    if (!rootsSel || !listEl) return;
    listEl.innerHTML = '<div class="muted" style="padding:10px;">Loading…</div>';
    try {
      const roots = await apiRoots();
      rootsSel.innerHTML = '';
      for (const r of roots) {
        const o = document.createElement('option');
        o.value = r.path; o.textContent = r.label || r.path;
        rootsSel.appendChild(o);
      }
      if (roots[0]) await openPath(roots[0].path);
    } catch (e) {
      listEl.innerHTML = `<pre style="padding:10px;white-space:pre-wrap">${String(e)}</pre>`;
    }
  }

  function applySelection() {
    const target = TARGET_INPUT_ID && document.getElementById(TARGET_INPUT_ID);
    if (!target) { hideModal(); return; }
    if (SELECTED_FILE) {
      target.value = SELECTED_FILE;
      hideModal();
      return;
    }
    // If no explicit file selected, but an absolute path typed, accept it
    const typed = (qs('#fs-path')?.value || '').trim();
    if (typed) {
      target.value = typed;
      hideModal();
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    ensureModalMarkup();
    // Wire browse buttons
    qsa('.browse-file-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        TARGET_INPUT_ID = btn.getAttribute('data-target');
        SELECTED_FILE = '';
        showModal();
        await bootPicker();
      });
    });

    // Modal controls
    qs('#fs-close')?.addEventListener('click', hideModal);
    qs('#fs-go')?.addEventListener('click', () => {
      const val = (qs('#fs-path')?.value || '').trim();
      if (val) openPath(val);
    });
    qs('#fs-path')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); qs('#fs-go')?.click(); } });
    qs('#fs-roots')?.addEventListener('change', (e) => openPath(e.target.value));
    qs('#fs-select')?.addEventListener('click', applySelection);
  });
})();
