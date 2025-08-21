// static/js/player.js
(() => {
    const v = document.getElementById('player');
    if (!v) return;

    // Key used for localStorage resume
    // Fall back to src if we don't have a file-id data attribute
    const fileKey = (v.dataset.fileId || v.currentSrc || v.src || '').replace(/\W+/g, ':');
    const POS_KEY = `ams:pos:${fileKey}`;
    const VOL_KEY = `ams:vol`;

    // Resume position
    try {
        const last = parseFloat(localStorage.getItem(POS_KEY) || 'NaN');
        if (!Number.isNaN(last) && last > 1) {
            v.currentTime = last;
        }
    } catch { }

    // Restore volume
    try {
        const vol = parseFloat(localStorage.getItem(VOL_KEY) || 'NaN');
        if (!Number.isNaN(vol)) v.volume = Math.min(1, Math.max(0, vol));
    } catch { }

    // Persist position every ~3s
    let tLast = 0;
    v.addEventListener('timeupdate', () => {
        if (v.duration && v.currentTime > 0) {
            const now = performance.now();
            if (now - tLast > 3000) {
                tLast = now;
                localStorage.setItem(POS_KEY, String(v.currentTime));
            }
        }
    });

    v.addEventListener('ended', () => {
        try { localStorage.removeItem(POS_KEY); } catch { }
    });

    v.addEventListener('volumechange', () => {
        try { localStorage.setItem(VOL_KEY, String(v.volume)); } catch { }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // ignore if typing in inputs
        const tag = (document.activeElement && document.activeElement.tagName) || '';
        if (['INPUT', 'TEXTAREA'].includes(tag)) return;

        // space toggles play/pause
        if (e.code === 'Space') {
            e.preventDefault();
            if (v.paused) v.play().catch(() => { }); else v.pause();
        }
        // left/right arrows seek
        if (e.code === 'ArrowRight') {
            v.currentTime = Math.min((v.currentTime || 0) + 10, v.duration || 1e12);
        }
        if (e.code === 'ArrowLeft') {
            v.currentTime = Math.max((v.currentTime || 0) - 10, 0);
        }
        // up/down volume
        if (e.code === 'ArrowUp') {
            e.preventDefault();
            v.volume = Math.min(1, (v.volume || 0) + 0.05);
        }
        if (e.code === 'ArrowDown') {
            e.preventDefault();
            v.volume = Math.max(0, (v.volume || 0) - 0.05);
        }
        // M to mute
        if (e.key.toLowerCase() === 'm') {
            v.muted = !v.muted;
        }
        // F for fullscreen
        if (e.key.toLowerCase() === 'f') {
            if (!document.fullscreenElement) v.requestFullscreen?.();
            else document.exitFullscreen?.();
        }
    });

    // Double-click toggles fullscreen
    v.addEventListener('dblclick', () => {
        if (!document.fullscreenElement) v.requestFullscreen?.();
        else document.exitFullscreen?.();
    });
})();
