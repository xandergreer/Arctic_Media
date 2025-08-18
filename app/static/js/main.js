(() => {
    const btn = document.getElementById('menu-btn');
    const sidebar = document.getElementById('sidebar');
    const closeBtn = document.getElementById('sidebar-close');
    const backdrop = document.getElementById('sidebar-backdrop');
    const list = document.getElementById('sidebar-list');

    if (!btn || !sidebar || !backdrop || !list) return; // pages without chrome

    let loaded = false;

    function openSidebar() {
        document.body.classList.add('sidebar-open');
        btn.setAttribute('aria-expanded', 'true');
        if (!loaded) {
            loaded = true;
            loadSidebar();
        }
    }

    function closeSidebar() {
        document.body.classList.remove('sidebar-open');
        btn.setAttribute('aria-expanded', 'false');
    }

    btn.addEventListener('click', openSidebar);
    closeBtn.addEventListener('click', closeSidebar);
    backdrop.addEventListener('click', closeSidebar);
    window.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeSidebar();
    });

    async function loadSidebar() {
        try {
            const res = await fetch('/ui/sidebar');
            if (!res.ok) throw new Error('failed');
            const data = await res.json();
            renderSidebar(data);
        } catch (e) {
            list.innerHTML = `<div class="s-section"><div class="s-title">Error</div><div class="s-item">Could not load libraries</div></div>`;
        }
    }

    const icons = {
        movie: '🎬',
        tv: '📺',
    };

    function section(title, inner) {
        return `
      <div class="s-section">
        <div class="s-title">${title}</div>
        ${inner}
      </div>`;
    }

    function item(icon, label, href) {
        return `<a class="s-item" href="${href}">
      <span class="ic">${icon}</span> <span>${label}</span>
    </a>`;
    }

    function renderSidebar(data) {
        const local = (data.local || [])
            .map(l => item(icons[l.type] || '📁', l.name, l.href))
            .join('');

        const friends = (data.servers || [])
            .map(s => section(
                s.name,
                (s.items || []).map(i => item(icons[i.type] || '📁', i.name, i.href)).join('') || `<div class="s-item">No libraries</div>`
            ))
            .join('');

        list.innerHTML =
            section('This Server', local || `<div class="s-item">No libraries</div>`) +
            (friends ? section('Friends', '') + friends : '');
    }
})();
