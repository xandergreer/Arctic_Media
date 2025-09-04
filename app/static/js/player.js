// /static/js/player.js
(() => {
    const HLS_LOCAL = "/static/js/vendor/hls.min.js";

    // tiny helpers
    const $ = (sel, ctx = document) => ctx.querySelector(sel);
    const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
    const log = (...a) => { try { console.log("[player]", ...a); } catch { } };
    const warn = (...a) => { try { console.warn("[player]", ...a); } catch { } };
    const fmtTime = (secs) => {
        secs = Math.max(0, Math.floor(Number(secs || 0)));
        const h = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        const s = secs % 60;
        const pad = (n) => String(n).padStart(2, '0');
        return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
    };
    const updateDurationLabel = (video, totalSecs) => {
        try {
            if (!totalSecs || !Number.isFinite(totalSecs)) return;
            const plyrRoot = video.closest('.plyr') || document;
            const label = plyrRoot.querySelector('.plyr__time--duration');
            if (label) label.textContent = fmtTime(totalSecs);
        } catch { }
    };
    async function fetchMetaDuration(fileId) {
        try {
            const r = await fetch(`/stream/${encodeURIComponent(fileId)}/meta`, { cache: 'no-store' });
            if (!r.ok) return null;
            const j = await r.json();
            return (j && typeof j.duration === 'number') ? j.duration : null;
        } catch {
            return null;
        }
    }

    // load hls.js from your local copy
    function loadHls() {
        return new Promise((resolve, reject) => {
            if (window.Hls) return resolve(window.Hls);
            const s = document.createElement("script");
            s.src = HLS_LOCAL;
            s.async = true;
            s.onload = () => resolve(window.Hls);
            s.onerror = () => reject(new Error("Failed to load hls.min.js"));
            document.head.appendChild(s);
        });
    }

    function supportsNativeHls(video) {
        const t = video?.canPlayType?.("application/vnd.apple.mpegurl");
        return !!(t && t !== "");
    }

    // ── UI helpers
    function openPlayerUI() {
        const wrap = $("#playerWrap");
        if (wrap) {
            wrap.classList.remove("collapsed");
            wrap.classList.add("expanded");
        }
        // Start time updates when player opens
        startTimeUpdate();
    }

    function updateCurrentTimeDisplay() {
        // Find the PLYR controls container
        const plyrRoot = document.querySelector('.plyr') || document;
        let timeDisplay = plyrRoot.querySelector('.real-time-display');

        if (!timeDisplay) {
            // Create the time display element if it doesn't exist
            timeDisplay = document.createElement('div');
            timeDisplay.className = 'real-time-display';
            timeDisplay.style.cssText = `
                color: #fff;
                font-family: monospace;
                font-size: 14px;
                font-weight: 500;
                padding: 6px 10px;
                background: rgba(0, 0, 0, 0.8);
                border-radius: 6px;
                position: absolute;
                top: 15px;
                right: 15px;
                z-index: 1000;
                pointer-events: none;
                user-select: none;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
            `;

            // Insert it into the PLYR video wrapper, not the controls
            const plyrContainer = plyrRoot.querySelector('.plyr__video-wrapper') || plyrRoot;
            if (plyrContainer) {
                plyrContainer.style.position = 'relative';
                plyrContainer.appendChild(timeDisplay);
            }
        }

        if (timeDisplay) {
            const now = new Date();
            const hours = now.getHours().toString().padStart(2, '0');
            const minutes = now.getMinutes().toString().padStart(2, '0');
            const seconds = now.getSeconds().toString().padStart(2, '0');

            timeDisplay.textContent = `${hours}:${minutes}:${seconds}`;
        }
    }

    function startTimeUpdate() {
        const video = $("#plyr") || $("video");
        if (video) {
            // Update time display every 100ms for smooth updates
            const timeInterval = setInterval(updateCurrentTimeDisplay, 100);

            // Store the interval ID so we can clear it later
            video._timeInterval = timeInterval;

            // Also update on timeupdate event for more responsive updates
            video.addEventListener('timeupdate', updateCurrentTimeDisplay);
        }
    }

    function stopTimeUpdate() {
        const video = $("#plyr") || $("video");
        if (video && video._timeInterval) {
            clearInterval(video._timeInterval);
            video._timeInterval = null;
            video.removeEventListener('timeupdate', updateCurrentTimeDisplay);
        }
    }
    function closePlayerUI() {
        const wrap = $("#playerWrap");
        const video = $("#plyr") || $("video");

        // Stop time updates
        stopTimeUpdate();

        if (video) {
            try { if (video._hls) video._hls.destroy(); } catch { }
            video._hls = null;
            try { video.removeAttribute("src"); video.load(); } catch { }
        }
        if (wrap) {
            wrap.classList.add("collapsed");
            wrap.classList.remove("expanded", "mini");
        }
    }
    window.closePlayer = closePlayerUI;

    // Keep one Plyr instance
    let plyr = null;
    let currentQuality = 0; // 0=Auto; else height like 1080,720
    let currentFileId = null;
    let currentItemId = null;
    function ensurePlyr(video) {
        if (window.Plyr && !plyr) {
            plyr = new Plyr(video, {
                controls: [
                    "play-large", "play", "progress", "current-time", "duration",
                    "mute", "volume", "captions", "settings", "pip", "airplay", "fullscreen"
                ],
                ratio: "16:9",
                clickToPlay: true,
                settings: ["quality", "captions", "speed"],
                quality: {
                    default: 0,
                    options: [0, 1080, 720, 480],
                    forced: true,
                    onChange: (q) => {
                        try {
                            currentQuality = Number(q) || 0;
                            if (currentItemId) {
                                const qq = currentQuality > 0 ? `&vcodec=h264&vh=${currentQuality}` : '';
                                const m3u8 = `/stream/${encodeURIComponent(currentItemId)}/master.m3u8?container=fmp4${qq}`;
                                const mp4 = currentFileId ? `/stream/${encodeURIComponent(currentFileId)}/auto` : '';
                                attachAndPlay({ video, m3u8, mp4 });
                            }
                        } catch { }
                    }
                }
            });
        }
        return plyr;
    }

    // ── main attach/play
    async function attachAndPlay({ video, m3u8, mp4 }) {
        if (!video) return;
        ensurePlyr(video);

        // improve autoplay chances on first gesture
        if (video.paused && video.currentTime === 0) video.muted = true;

        const native = supportsNativeHls(video);
        if (!native) {
            try {
                const Hls = await loadHls();
                if (Hls && Hls.isSupported()) {
                    if (video._hls) { try { video._hls.destroy(); } catch { } video._hls = null; }

                    const hls = new Hls({
                        lowLatencyMode: false,
                        backBufferLength: 30,
                        maxBufferLength: 20,
                        maxMaxBufferLength: 60,
                        fragLoadingMaxRetry: 2,
                        manifestLoadingMaxRetry: 2,
                        enableWorker: true,
                        startPosition: -1,
                        // Better codec handling
                        forceKeyFrameOnDiscontinuity: true,
                        abrEwmaDefaultEstimate: 500000,
                        abrBandWidthFactor: 0.95,
                        abrBandWidthUpFactor: 0.7,
                        abrMaxWithRealBitrate: true
                    });

                    hls.on(Hls.Events.ERROR, (_evt, data) => {
                        warn("HLS error", data);

                        // Handle specific codec errors
                        if (data?.details === "bufferAppendError" || data?.details === "bufferAddCodecError") {
                            warn("Codec compatibility issue, trying fallback");
                            try {
                                hls.destroy();
                            } catch { }
                            video._hls = null;

                            // Try MP4 fallback immediately
                            if (mp4) {
                                video.src = mp4;
                                video.load();
                                video.play().catch(() => { });
                            }
                            return;
                        }

                        // common bufferAppendError → flush & retry once
                        if (data?.details === "bufferAppendError") {
                            try { hls.stopLoad(); hls.startLoad(hls.media?.currentTime || 0); } catch { }
                            return;
                        }

                        if (data?.fatal) {
                            try { hls.destroy(); } catch { }
                            video._hls = null;
                            if (mp4) {
                                video.src = mp4;
                                video.load();
                                video.play().catch(() => { });
                            }
                        }
                    });

                    hls.loadSource(m3u8);
                    hls.attachMedia(video);
                    hls.on(Hls.Events.MANIFEST_PARSED, () => {
                        try { hls.startLoad(-1); } catch { }
                        video.play().catch(() => { });
                    });

                    video._hls = hls;
                    return;
                }
            } catch (e) {
                warn("Failed to init hls.js:", e);
            }
        }

        // Native HLS (Safari/iOS)
        if (native) {
            video.src = m3u8;
            video.load();
            await video.play().catch(() => { });
            return;
        }

        // Final fallback: progressive MP4
        if (mp4) {
            video.src = mp4;
            video.load();
            await video.play().catch(() => { });
        }
    }

    // ── high level
    async function playItem(fileId, title = "") {
        const video = $("#plyr") || $("video");
        const npTitle = $("#npTitle");
        if (!video || !fileId) return;

        if (npTitle) npTitle.textContent = title || "";

        // Fetch known duration for better UI (does not affect actual seek constraints)
        const metaDur = await fetchMetaDuration(fileId);
        if (metaDur) {
            video.dataset.totalDuration = String(Math.floor(metaDur));
            updateDurationLabel(video, metaDur);
        }

        const direct = `/stream/${encodeURIComponent(fileId)}/file`;  // Fastest - direct file (Range)
        // Use the itemId for HLS endpoints; this avoids mismatches with fileId-only routes
        const itemId = (video.dataset && (video.dataset.itemId || video.getAttribute("data-item-id"))) || "";
        currentFileId = fileId; currentItemId = itemId || null;
        const qq = currentQuality > 0 ? `&vcodec=h264&vh=${currentQuality}` : '';
        const m3u8 = itemId
            ? `/stream/${encodeURIComponent(itemId)}/master.m3u8?container=fmp4${qq}`
            : ``;  // if missing, we'll fall back to direct/mp4
        const mp4 = `/stream/${encodeURIComponent(fileId)}/auto`;  // Progressive fallback

        log("playItem", { fileId, direct, m3u8, mp4, title });

        // Try direct file first (fastest) with graceful fallback if decode stalls or fails
        let triedDirect = false;
        try {
            // Prefer smarter HEAD that checks codecs when we have itemId
            const headUrl = itemId ? `/stream/${encodeURIComponent(itemId)}/direct` : direct;
            const response = await fetch(headUrl, { method: 'HEAD', cache: 'no-store' });
            if (response.ok) {
                triedDirect = true;
                let fellBack = false;
                const cleanup = () => {
                    try { video.removeEventListener('error', onError); } catch { }
                    try { video.removeEventListener('playing', onPlaying); } catch { }
                    try { video.removeEventListener('canplay', onPlaying); } catch { }
                    if (fallbackTimer) clearTimeout(fallbackTimer);
                };
                const doFallback = () => {
                    if (fellBack) return; fellBack = true; cleanup();
                    attachAndPlay({ video, m3u8, mp4 }).then(() => openPlayerUI());
                };
                const onError = () => {
                    // codec or playback failure — fall back to HLS/MP4
                    doFallback();
                };
                const onPlaying = () => { cleanup(); };
                video.addEventListener('error', onError, { once: true });
                video.addEventListener('playing', onPlaying, { once: true });
                video.addEventListener('canplay', onPlaying, { once: true });

                video.src = direct;
                video.load();
                try {
                    await video.play();
                    // If decode doesn’t start (no events) within a short window, fall back
                    var fallbackTimer = setTimeout(() => {
                        // Haven't started decoding? (readyState < HAVE_CURRENT_DATA or no progress)
                        if (video.readyState < 2 || video.currentTime === 0) {
                            doFallback();
                        } else {
                            cleanup();
                        }
                    }, 2500);
                    openPlayerUI();
                    return;
                } catch (e) {
                    // Autoplay/codec issue — fallback
                    doFallback();
                }
            }
        } catch (e) {
            log("Direct HEAD failed, trying HLS");
        }

        // Fall back to HLS (or progressive) if direct was not viable
        await attachAndPlay({ video, m3u8, mp4 });
        openPlayerUI();
    }
    window.playItem = playItem;

    function wirePage() {
        // buttons & selectors
        const playBtn = $("#playBtn");
        playBtn?.addEventListener("click", () => {
            const id = playBtn.dataset.fileId || playBtn.getAttribute("data-file-id");
            const title = playBtn.dataset.title || "";
            if (id) playItem(id, title);
        });

        $$(".ep-card[data-file-id]").forEach(btn => {
            btn.addEventListener("click", () => {
                playItem(btn.getAttribute("data-file-id"), btn.getAttribute("data-title") || "");
            });
        });

        const sel = $("#sourceSelect");
        if (sel) {
            sel.addEventListener("change", () => {
                const opt = sel.options[sel.selectedIndex];
                const id = opt?.dataset?.fileId || opt?.value;
                const title = (opt?.textContent || "").trim();
                if (id) playItem(id, title);
            });
        }

        $("#minBtn")?.addEventListener("click", () => {
            const wrap = $("#playerWrap"); if (!wrap) return;
            wrap.classList.toggle("mini");
            wrap.classList.toggle("expanded");
        });
        $("#closeBtn")?.addEventListener("click", closePlayerUI);

        // auto-boot if the <video> carries a file id
        const v = $("#plyr") || $("video");
        const bootId = v?.dataset?.fileId || v?.getAttribute?.("data-file-id");
        const bootTitle = v?.dataset?.title || "";
        if (bootId) playItem(bootId, bootTitle);
    }

    document.addEventListener("DOMContentLoaded", () => {
        const video = $("#plyr");
        if (video && window.Plyr) ensurePlyr(video);
        wirePage();
    });
})();
