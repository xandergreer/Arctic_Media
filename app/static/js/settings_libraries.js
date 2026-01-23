// app/static/js/settings_libraries.js
console.log('[fs] settings_libraries.js LIVE no-cache', new Date().toISOString());

/* ---------- tiny utils ---------- */
const $ = (id) => document.getElementById(id);
const isWin = (p) => /^[A-Za-z]:[\\/]/.test(p);
const sepOf = (p) => (isWin(p) ? "\\" : "/");

/* ---------- normalize API shapes ---------- */
function normalizeRoots(data) {
    const arr = Array.isArray(data) ? data : (Array.isArray(data?.roots) ? data.roots : []);
    return arr.map(r => (typeof r === "string"
        ? { path: r, label: r.replace(/[:/\\]+$/, "") }
        : { path: r.path || "", label: r.label || (r.path || "").replace(/[:/\\]+$/, "") }
    )).filter(r => r.path);
}
function normalizeList(raw) {
    const list = Array.isArray(raw?.entries) ? raw.entries
        : Array.isArray(raw?.items) ? raw.items
            : [];
    const items = list.map(e => ({
        name: e.name || (e.path ? e.path.split(/[\\/]/).pop() : ""),
        path: e.path || "",
        is_dir: e.type ? e.type === "dir" : (e.is_dir !== false)
    })).filter(e => e.path && e.is_dir);
    return { path: raw?.path || "", parent: raw?.parent ?? null, items };
}

/* ---------- talk to backend ---------- */
async function getRoots() {
    const r = await fetch('/fs/roots', { headers: { 'Accept': 'application/json' }, credentials: 'same-origin', cache: 'no-store' });
    const text = await r.text();
    console.log('[fs] /fs/roots', r.status, text.slice(0, 200));
    if (!r.ok) throw new Error(text || `roots HTTP ${r.status}`);
    return normalizeRoots(JSON.parse(text));
}
async function getList(path) {
    const url = new URL('/fs/list', location.origin);
    url.searchParams.set('path', path);
    url.searchParams.set('include_files', 'false');
    const r = await fetch(url, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin', cache: 'no-store' });
    const text = await r.text();
    console.log('[fs] /fs/list', r.status, 'path=', path, text.slice(0, 200));
    if (!r.ok) throw new Error(text || `list HTTP ${r.status}`);
    return normalizeList(JSON.parse(text));
}

/* ---------- renderers (match your HTML) ---------- */
function renderBreadcrumb(path, bc) {
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
        b.onclick = () => openPath(target, true);
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
function renderRootsUI(roots, sel) {
    sel.innerHTML = '';
    for (const r of roots) {
        const o = document.createElement('option');
        o.value = r.path; o.textContent = r.label || r.path;
        sel.appendChild(o);
    }
}
function renderListUI(items, listEl) {
    listEl.innerHTML = '';
    if (!items.length) {
        listEl.innerHTML = `<div class="muted" style="padding:10px;">(No subfolders)</div>`;
        return;
    }
    for (const it of items) {
        const row = document.createElement('div');
        row.className = 'fs-row';
        row.style.cssText = 'display:flex;gap:8px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--border,#333)';
        const icon = document.createElement('span'); icon.textContent = '📁'; row.appendChild(icon);
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'link';
        btn.style.cssText = 'background:none;border:0;color:var(--link,#7fb0ff);cursor:pointer;padding:0;font:inherit;text-align:left;';
        btn.textContent = it.name || it.path;
        btn.onclick = () => openPath(it.path, true);
        row.appendChild(btn);
        listEl.appendChild(row);
    }
}

/* ---------- state + nav ---------- */
const FS = { curPath: '', history: [], hIndex: -1 };
async function openPath(path, push = true) {
    const listEl = document.getElementById('fs-list');
    const bc = document.getElementById('fs-bc');
    const pathInp = document.getElementById('fs-path');
    if (!listEl) return;

    listEl.innerHTML = `<div class="muted" style="padding:10px;">Loading…</div>`;
    try {
        const data = await getList(path);
        console.log('[fs] items=', data.items.length, 'at', data.path);
        FS.curPath = data.path || path;
        if (push) { FS.history = FS.history.slice(0, FS.hIndex + 1); FS.history.push(FS.curPath); FS.hIndex = FS.history.length - 1; }
        if (pathInp) pathInp.value = FS.curPath;
        if (bc) renderBreadcrumb(FS.curPath, bc);
        renderListUI(data.items, listEl);
    } catch (e) {
        console.error('[fs] openPath error', e);
        listEl.innerHTML = `<pre style="padding:10px;white-space:pre-wrap">${String(e)}</pre>`;
    }
}


function ensureModalParts() {
    // 1) ensure outer modal exists
    let modal = document.getElementById('fs-modal');
    if (!modal) {
        document.body.insertAdjacentHTML('beforeend',
            `<div id="fs-modal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="fs-title"></div>`
        );
        modal = document.getElementById('fs-modal');
    }

    // 2) if inner parts are missing, inject the exact markup from your HTML
    const need = ['fs-roots', 'fs-path', 'fs-go', 'fs-close', 'fs-select', 'fs-list', 'fs-bc'];
    const hasAll = need.every(id => modal.querySelector('#' + id) || document.getElementById(id));
    if (!hasAll) {
        modal.innerHTML = `
      <div class="modal-card" style="max-width:820px; width:100%;">
        <header class="modal-header" style="display:flex;align-items:center;justify-content:space-between;gap:12px;">
          <h3 id="fs-title" class="h3">Choose a folder</h3>
          <button id="fs-close" type="button" class="btn btn-ghost">Close</button>
        </header>

        <div class="modal-toolbar" style="display:flex;gap:8px;margin:8px 0;">
          <select id="fs-roots" class="input" style="width:160px"></select>
          <input id="fs-path" class="input" type="text" placeholder="C:/  or  F:/Media/Movies" style="flex:1;">
          <button id="fs-go" type="button" class="btn btn-secondary">Go</button>
        </div>

        <nav id="fs-bc" class="fs-bc" style="margin:6px 0;display:flex;flex-wrap:wrap;gap:4px;"></nav>

        <div id="fs-list" class="fs-list" style="margin-top:6px;max-height:50vh;overflow:auto;">
          <div class="muted">Loading…</div>
        </div>

        <footer class="modal-footer" style="margin-top:12px;display:flex;justify-content:flex-end;gap:8px;">
          <button id="fs-select" type="button" class="btn btn-primary">Select folder</button>
        </footer>
      </div>`;
    }

    // 3) return refs (query inside modal first; fall back to document)
    const q = (id) => modal.querySelector('#' + id) || document.getElementById(id);
    return {
        modal,
        rootsSel: q('fs-roots'),
        pathInp: q('fs-path'),
        goBtn: q('fs-go'),
        closeBtn: q('fs-close'),
        selectBtn: q('fs-select'),
        listEl: q('fs-list'),
        bcEl: q('fs-bc'),
    };
}

/* ---------- boot ---------- */
async function bootPicker() {
    const parts = ensureModalParts();

    // sanity: bail early if something’s still missing
    const missing = [];
    if (!parts.rootsSel) missing.push('#fs-roots');
    if (!parts.pathInp) missing.push('#fs-path');
    if (!parts.goBtn) missing.push('#fs-go');
    if (!parts.closeBtn) missing.push('#fs-close');
    if (!parts.selectBtn) missing.push('#fs-select');
    if (!parts.listEl) missing.push('#fs-list');
    if (!parts.bcEl) missing.push('#fs-bc');
    if (missing.length) {
        console.error('[fs] bootPicker: required modal parts missing:', missing.join(', '));
        if (parts.listEl) parts.listEl.innerHTML = `<div class="muted" style="padding:10px;">Missing: ${missing.join(', ')}</div>`;
        return;
    }

    // show modal
    parts.modal.classList.remove('hidden');

    // wire events
    parts.closeBtn.addEventListener('click', () => parts.modal.classList.add('hidden'));
    parts.goBtn.addEventListener('click', () => openPath(parts.pathInp.value.trim(), true));
    parts.pathInp.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); parts.goBtn.click(); } });
    parts.rootsSel.addEventListener('change', (e) => openPath(e.target.value, true));
    parts.selectBtn.addEventListener('click', () => {
        const t = document.getElementById('path-input');
        if (t) t.value = FS.curPath || '';
        parts.modal.classList.add('hidden');
    });

    // fetch roots + open first
    try {
        const roots = await getRoots();
        console.log('[fs] roots=', roots.length, roots);
        if (!roots.length) {
            parts.listEl.innerHTML = `<div class="muted" style="padding:10px;">No drives found</div>`;
            return;
        }
        // fill <select>
        parts.rootsSel.innerHTML = '';
        roots.forEach(r => {
            const o = document.createElement('option');
            o.value = r.path; o.textContent = r.label || r.path;
            parts.rootsSel.appendChild(o);
        });
        await openPath(roots[0].path, true);
    } catch (e) {
        console.error('[fs] boot error', e);
        parts.listEl.innerHTML = `<pre style="padding:10px;white-space:pre-wrap">${String(e)}</pre>`;
    }
}

/* ---------- page hook ---------- */
document.addEventListener('DOMContentLoaded', () => {
    const browseBtn = document.getElementById('browse-btn');
    if (browseBtn) browseBtn.addEventListener('click', bootPicker);
    const scanAllBtn = document.getElementById('scan-all-btn');
    if (scanAllBtn) {
        scanAllBtn.addEventListener('click', async () => {
            const prev = scanAllBtn.textContent;
            scanAllBtn.disabled = true; scanAllBtn.textContent = 'Queued…'; scanAllBtn.setAttribute('aria-busy', 'true');
            try {
                const r = await fetch('/libraries/scan_all?background=true&refresh_metadata=true', { method: 'POST', credentials: 'same-origin' });
                const jr = await r.json().catch(() => ({}));
                if (r.ok && jr?.queued && jr?.job_id) {
                    const jobId = jr.job_id;
                    let stop = false;
                    async function poll() {
                        if (stop) return;
                        try {
                            const pj = await fetch(`/jobs/${jobId}`, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin', cache: 'no-store' });
                            if (pj.ok) {
                                const j = await pj.json();
                                if (j?.status === 'done') {
                                    stop = true;
                                    alert('All libraries scanned.');
                                    scanAllBtn.removeAttribute('aria-busy'); scanAllBtn.disabled = false; scanAllBtn.textContent = prev || 'Scan All (scan + refresh)';
                                    return;
                                }
                                if (j?.status === 'failed') {
                                    stop = true;
                                    alert('Scan-all failed');
                                    scanAllBtn.removeAttribute('aria-busy'); scanAllBtn.disabled = false; scanAllBtn.textContent = prev || 'Scan All (scan + refresh)';
                                    return;
                                }
                                const p = (j.total && j.total > 0) ? `${j.progress || 0}/${j.total}` : (j.status || '…');
                                scanAllBtn.textContent = `Scanning… ${p}`;
                            }
                        } catch (_) { }
                        setTimeout(poll, 1000);
                    }
                    poll();
                } else if (r.ok) {
                    alert('Scanning all libraries in foreground…');
                    scanAllBtn.removeAttribute('aria-busy'); scanAllBtn.disabled = false; scanAllBtn.textContent = prev || 'Scan All (scan + refresh)';
                } else {
                    throw new Error('Scan-all request failed');
                }
            } catch (e) {
                alert(e?.message || 'Scan-all failed');
                scanAllBtn.removeAttribute('aria-busy'); scanAllBtn.disabled = false; scanAllBtn.textContent = prev || 'Scan All (scan + refresh)';
            }
        });
    }
});

// --- Libraries CRUD wiring (submit, table reload, scan, delete) ---
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('lib-form');
    const table = document.getElementById('lib-table');
    const msg = document.getElementById('lib-msg');

    async function reloadLibraries() {
        if (!table) return;
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="4">Loading…</td></tr>`;
        try {
            const r = await fetch('/libraries', { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const libs = await r.json();
            tbody.innerHTML = '';
            if (!Array.isArray(libs) || !libs.length) {
                tbody.innerHTML = `<tr><td colspan="4">No libraries yet.</td></tr>`;
                return;
            }
            for (const lib of libs) {
                const tr = document.createElement('tr');
                tr.innerHTML = `
          <td>${lib.name ?? ''}</td>
          <td style="text-align:center">${(lib.type ?? '').toString().toUpperCase()}</td>
          <td>${lib.path ?? ''}</td>
          <td style="text-align:center;white-space:nowrap">
            <button class="btn btn-secondary" data-act="scan" data-id="${lib.id}">Scan</button>
            <button class="btn btn-primary" data-act="refresh" data-id="${lib.id}">Refresh Metadata</button>
            <button class="btn btn-ghost" data-act="del"  data-id="${lib.id}">Delete</button>
          </td>`;
                tbody.appendChild(tr);
            }
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="4">Failed to load libraries.</td></tr>`;
        }
    }

    form?.addEventListener('submit', async (e) => {
        e.preventDefault(); // stop the default GET /settings/libraries?name=...
        const fd = new FormData(form);
        const payload = Object.fromEntries(fd.entries()); // {name, type, path}

        // ---- fallback name if blank ----
        let name = (payload.name || "").trim();
        if (!name) {
            const cleanPath = (payload.path || "").toString().replace(/[\\/]+$/, "");
            const last = cleanPath.split(/[\\/]/).pop() || "";
            name = last || (payload.type ? String(payload.type).charAt(0).toUpperCase() + String(payload.type).slice(1) : "Library");
            payload.name = name;
        }

        try {
            const r = await fetch('/libraries', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(payload),
            });
            if (!r.ok) {
                let detail = '';
                try { detail = (await r.json()).detail; } catch { }
                throw new Error(detail || `Add failed (${r.status})`);
            }
            msg && (msg.textContent = 'Library added.');
            form.reset();
            reloadLibraries();
        } catch (err) {
            msg && (msg.textContent = err.message || 'Failed to add library');
        }
    });

    table?.addEventListener('click', async (e) => {
        const btn = e.target.closest('button');
        if (!btn) return;
        const id = btn.getAttribute('data-id');
        const act = btn.getAttribute('data-act');
        if (!id || !act) return;

        if (act === 'scan') {
            const prev = btn.textContent;
            btn.disabled = true; btn.textContent = 'Queued…'; btn.setAttribute('aria-busy', 'true');
            try {
                // queue background job and poll
                const rq = await fetch(`/libraries/${id}/scan?background=true`, { method: 'POST', credentials: 'same-origin' });
                const jr = await rq.json().catch(() => ({}));
                if (rq.ok && jr?.queued && jr?.job_id) {
                    const jobId = jr.job_id;
                    let stop = false;
                    async function poll() {
                        if (stop) return;
                        try {
                            const r = await fetch(`/jobs/${jobId}`, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin', cache: 'no-store' });
                            if (!r.ok) throw new Error('poll failed');
                            const j = await r.json();
                            const p = (j.total && j.total > 0) ? Math.min(100, Math.floor((j.progress || 0) * 100 / j.total)) : 0;
                            btn.textContent = (j.status === 'running') ? `Scanning ${p}%` : (j.status === 'queued' ? 'Queued…' : (j.status || '…'));
                            if (j.status === 'done') {
                                stop = true;
                                const stats = j.result || {};
                                const { added = 0, updated = 0, skipped = 0, discovered = 0, known_paths = 0, note = '' } = stats;
                                alert(note === 'path_missing'
                                    ? 'Scan aborted: library path not found.'
                                    : `Scan complete: +${added} added, ${updated} updated, ${skipped} skipped (saw ${discovered}, known ${known_paths})`);
                                reloadLibraries();
                                btn.removeAttribute('aria-busy'); btn.disabled = false; btn.textContent = prev || 'Scan';
                                return;
                            }
                        } catch (_) { }
                        setTimeout(poll, 1000);
                    }
                    poll();
                } else {
                    // fallback to synchronous scan
                    const r = await fetch(`/libraries/${id}/scan`, { method: 'POST', credentials: 'same-origin' });
                    const data = await r.json().catch(() => ({}));
                    if (!r.ok) throw new Error('Scan failed');
                    const { added = 0, updated = 0, skipped = 0, discovered = 0, known_paths = 0, note = '' } = data;
                    alert(note === 'path_missing'
                        ? 'Scan aborted: library path not found.'
                        : `Scan complete: +${added} added, ${updated} updated, ${skipped} skipped (saw ${discovered}, known ${known_paths})`);
                    reloadLibraries();
                    btn.removeAttribute('aria-busy'); btn.disabled = false; btn.textContent = prev || 'Scan';
                }
            } catch (err) {
                alert(err?.message || 'Scan failed');
                btn.removeAttribute('aria-busy'); btn.disabled = false; btn.textContent = prev || 'Scan';
            }
        }

        if (act === 'del') {
            if (!confirm('Delete this library?')) return;
            try {
                const r = await fetch(`/libraries/${id}`, { method: 'DELETE', credentials: 'same-origin' });
                if (r.ok) reloadLibraries();
            } catch { }
        }

        if (act === 'refresh') {
            const prev = btn.textContent;
            btn.disabled = true; btn.textContent = 'Refreshing…'; btn.setAttribute('aria-busy', 'true');
            try {
                // queue background metadata refresh job and poll
                const rq = await fetch(`/libraries/${id}/refresh_metadata?background=true&force=true&only_missing=false`, { method: 'POST', credentials: 'same-origin' });
                const jr = await rq.json().catch(() => ({}));
                if (rq.ok && jr?.queued && jr?.job_id) {
                    const jobId = jr.job_id;
                    let stop = false;
                    async function poll() {
                        if (stop) return;
                        try {
                            const r = await fetch(`/jobs/${jobId}`, { credentials: 'same-origin' });
                            const j = await r.json();
                            if (j?.status === 'done') {
                                stop = true;
                                const stats = j?.result?.stats || {};
                                const { matched = 0, skipped = 0, episodes = 0 } = stats;
                                alert(`Metadata refresh complete: ${matched} matched, ${episodes} episodes enriched, ${skipped} skipped`);
                                reloadLibraries();
                                btn.removeAttribute('aria-busy'); btn.disabled = false; btn.textContent = prev || 'Refresh Metadata';
                                return;
                            }
                            if (j?.status === 'failed') {
                                stop = true;
                                alert('Metadata refresh failed');
                                btn.removeAttribute('aria-busy'); btn.disabled = false; btn.textContent = prev || 'Refresh Metadata';
                                return;
                            }
                            // Update progress if available
                            if (j?.progress !== undefined && j?.total !== undefined) {
                                btn.textContent = `Refreshing… ${j.progress}/${j.total}`;
                            }
                        } catch (_) { }
                        setTimeout(poll, 1000);
                    }
                    poll();
                } else {
                    // fallback to synchronous refresh
                    const r = await fetch(`/libraries/${id}/refresh_metadata?force=true&only_missing=false`, { method: 'POST', credentials: 'same-origin' });
                    const data = await r.json().catch(() => ({}));
                    if (!r.ok) throw new Error('Metadata refresh failed');
                    const stats = data?.stats || {};
                    const { matched = 0, skipped = 0, episodes = 0 } = stats;
                    alert(`Metadata refresh complete: ${matched} matched, ${episodes} episodes enriched, ${skipped} skipped`);
                    reloadLibraries();
                    btn.removeAttribute('aria-busy'); btn.disabled = false; btn.textContent = prev || 'Refresh Metadata';
                }
            } catch (err) {
                alert(err?.message || 'Metadata refresh failed');
                btn.removeAttribute('aria-busy'); btn.disabled = false; btn.textContent = prev || 'Refresh Metadata';
            }
        }
    });

    // initial load
    reloadLibraries();
});
