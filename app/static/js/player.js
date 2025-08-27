// /static/js/player.js
(() => {
    const HLS_LOCAL = "/static/js/vendor/hls.min.js";

    // tiny helpers
    const $ = (sel, ctx = document) => ctx.querySelector(sel);
    const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
    const log = (...a) => { try { console.log("[player]", ...a); } catch { } };
    const warn = (...a) => { try { console.warn("[player]", ...a); } catch { } };

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
    }
    function closePlayerUI() {
        const wrap = $("#playerWrap");
        const video = $("#plyr") || $("video");
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
    function ensurePlyr(video) {
        if (window.Plyr && !plyr) {
            plyr = new Plyr(video, {
                controls: [
                    "play-large", "play", "progress", "current-time", "duration",
                    "mute", "volume", "captions", "settings", "pip", "airplay", "fullscreen"
                ],
                ratio: "16:9",
                clickToPlay: true
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
                        try { hls.startLoad(0); } catch { }
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

        const direct = `/stream/${encodeURIComponent(fileId)}/direct`;  // Fastest - direct file
        const m3u8 = `/stream/${encodeURIComponent(fileId)}/master.m3u8?container=fmp4`;  // HLS
        const mp4 = `/stream/${encodeURIComponent(fileId)}/auto`;  // Progressive fallback

        log("playItem", { fileId, direct, m3u8, mp4, title });

        // Try direct file first (fastest)
        try {
            const response = await fetch(direct, { method: 'HEAD' });
            if (response.ok) {
                video.src = direct;
                video.load();
                await video.play().catch(() => { });
                openPlayerUI();
                return;
            }
        } catch (e) {
            log("Direct file not available, trying HLS");
        }

        // Fall back to HLS
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
