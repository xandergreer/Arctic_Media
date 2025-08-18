(() => {
    const modal = document.getElementById('fs-modal');
    const btnOpen = document.getElementById('browse-btn');
    const btnClose = document.getElementById('fs-close');
    const btnGo = document.getElementById('fs-go');
    const btnSelect = document.getElementById('fs-select');
    const rootsSel = document.getElementById('fs-roots');
    const pathInp = document.getElementById('fs-path');
    const listEl = document.getElementById('fs-list');
    const bcEl = document.getElementById('fs-bc');
    const targetInput = document.getElementById('path-input');

    let curPath = '';

    const set = (el, html) => { if (el) el.innerHTML = html; };
    const show = () => modal?.classList.remove('hidden');
    const hide = () => modal?.classList.add('hidden');

    const normRoots = (data) => {
        const arr = Array.isArray(data) ? data : (data && data.roots) || [];
        return arr.map(r => typeof r === 'string'
            ? ({ path: r, label: r.replace(/[:/\\]+$/, '') })
            : ({ path: r.path || '', label: r.label || (r.path || '').replace(/[:/\\]+$/, '') })
        );
    };

    const normList = (data) => {
        const raw = Array.isArray(data?.entries) ? data.entries
            : (Array.isArray(data?.items) ? data.items : []);
        const entries = raw.map(e => ({
            name: e.name || (e.path ? e.path.split(/[\\/]/).pop() : ''),
            path: e.path || '',
            type: e.type || (e.is_dir === false ? 'file' : 'dir'),
            is_dir: e.is_dir !== false
        })).filter(e => e.type === 'dir' || e.is_dir);
        return { path: data?.path || '', parent: data?.parent || null, entries };
    };

    async function loadRoots() {
        set(listEl, '<div class="muted">Loading…</div>');
        try {
            const res = await fetch('/fs/roots', { headers: { 'Accept': 'application/json' } });
            const data = await res.json();
            const roots = normRoots(data);
            if (!roots.length) { set(listEl, '<div class="muted">No drives found</div>'); return; }

            rootsSel.innerHTML = '';
            roots.forEach(r => {
                const opt = document.createElement('option');
                opt.value = r.path; opt.textContent = r.label || r.path;
                rootsSel.appendChild(opt);
            });
            curPath = roots[0].path;
            pathInp.value = curPath;
            await list(curPath);
        } catch (e) {
            console.error('roots error', e);
            set(listEl, '<div class="muted">Couldn’t load drives</div>');
        }
    }

    function breadcrumb(path) {
        if (!bcEl) return;
        bcEl.innerHTML = '';
        if (!path) return;
        const sep = path.match(/^[A-Za-z]:[\\/]/) ? '\\' : '/';
        const parts = path.split(/[\\/]+/).filter(Boolean);
        let root = path.match(/^[A-Za-z]:[\\/]/) ? parts[0] + sep : '/';
        const rootBtn = document.createElement('button');
        rootBtn.textContent = root;
        rootBtn.onclick = () => list(root);
        bcEl.appendChild(rootBtn);

        let acc = root === '/' ? '' : root;
        const start = root === '/' ? 0 : 1;
        for (let i = start; i < parts.length; i++) {
            bcEl.appendChild(Object.assign(document.createElement('span'), { textContent: ' › ' }));
            acc = acc ? (acc.endsWith(sep) ? acc + parts[i] : acc + sep + parts[i]) : parts[i];
            const b = document.createElement('button');
            b.textContent = parts[i];
            b.onclick = () => list(acc);
            bcEl.appendChild(b);
        }
    }

    async function list(path) {
        set(listEl, '<div class="muted">Loading…</div>');
        try {
            const url = new URL('/fs/list', location.origin);
            url.searchParams.set('path', path);
            url.searchParams.set('include_files', 'false');
            const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const raw = await res.json();
            const data = normList(raw);

            curPath = data.path || path;
            pathInp.value = curPath;
            breadcrumb(curPath);

            listEl.innerHTML = '';
            if (data.parent) {
                const up = document.createElement('div');
                up.className = 'fs-row';
                up.innerHTML = `<span class="icon">📁</span><button class="link">.. (Up)</button>`;
                up.querySelector('button').onclick = () => list(data.parent);
                listEl.appendChild(up);
            }

            if (!data.entries.length) {
                set(listEl, '<div class="muted">No subfolders</div>');
                return;
            }

            for (const e of data.entries) {
                const row = document.createElement('div');
                row.className = 'fs-row';
                row.innerHTML = `<span class="icon">📁</span><button class="link">${e.name || e.path}</button>`;
                row.querySelector('button').onclick = () => list(e.path);
                listEl.appendChild(row);
            }
        } catch (e) {
            console.error('list error', e);
            set(listEl, '<div class="muted">Couldn’t load folder</div>');
        }
    }

    // wire up
    document.addEventListener('DOMContentLoaded', () => {
        btnOpen?.addEventListener('click', async () => { show(); await loadRoots(); });
        btnClose?.addEventListener('click', hide);
        btnGo?.addEventListener('click', async () => list(pathInp.value.trim()));
        rootsSel?.addEventListener('change', (e) => list(e.target.value));
        btnSelect?.addEventListener('click', () => { if (targetInput) targetInput.value = curPath; hide(); });
        pathInp?.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); btnGo?.click(); } });
    });
})();
