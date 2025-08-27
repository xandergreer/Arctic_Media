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

(function () {
    async function ensureHls() {
        if (window.Hls) return true;
        await new Promise((res, rej) => {
            const s = document.createElement("script");
            s.src = "https://cdn.jsdelivr.net/npm/hls.js@latest";
            s.onload = res; s.onerror = rej; document.head.appendChild(s);
        });
        return !!window.Hls;
    }

    async function playItem(fileId) {
        const video = document.getElementById("player") || document.querySelector("video");
        if (!video || !fileId) return;
        const m3u8 = `/stream/${encodeURIComponent(fileId)}/master.m3u8?container=fmp4`;
        const mp4 = `/stream/${encodeURIComponent(fileId)}/auto`;

        try {
            if (await ensureHls() && window.Hls.isSupported()) {
                if (video._hls) { try { video._hls.destroy(); } catch { } }
                const hls = new window.Hls({ lowLatencyMode: false, backBufferLength: 30 });
                hls.on(window.Hls.Events.ERROR, (_e, d) => {
                    if (d?.fatal) { try { hls.destroy(); } catch { }; video._hls = null; video.src = mp4; video.play().catch(() => { }); }
                });
                hls.loadSource(m3u8);
                hls.attachMedia(video);
                video._hls = hls;
                video.removeAttribute("src");
                await video.play().catch(() => { });
                return;
            }
        } catch { }

        if (video.canPlayType("application/vnd.apple.mpegurl")) {
            video.src = m3u8; video.play().catch(() => { });
        } else {
            video.src = mp4; video.play().catch(() => { });
        }
    }

    // expose for buttons like <a data-file-id="...">
    window.playItem = playItem;

    document.addEventListener("DOMContentLoaded", () => {
        // auto-boot if <video id="player" data-file-id="...">
        const v = document.getElementById("player");
        const bootId = v?.dataset?.fileId;
        if (bootId) playItem(bootId);

        // wire clickable cards/buttons
        document.querySelectorAll("[data-file-id]").forEach(el => {
            el.addEventListener("click", (e) => {
                e.preventDefault();
                playItem(el.getAttribute("data-file-id"));
            });
        });
    });
})();