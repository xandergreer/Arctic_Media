async function jsonGET(url) {
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

function el(tag, attrs = {}, ...kids) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
        if (k === "className") e.className = v;
        else if (k in e) e[k] = v;
        else e.setAttribute(k, v);
    });
    for (const k of kids) {
        if (k == null) continue;
        e.appendChild(typeof k === "string" ? document.createTextNode(k) : k);
    }
    return e;
}

const PLACEHOLDER = "/static/img/placeholder.png";

const state = { show: null };

async function loadShows() {
    const grid = document.getElementById("shows-grid");
    grid.innerHTML = "";
    const shows = await jsonGET("/api/tv/shows");
    shows.forEach((s) => {
        const poster = s.poster || PLACEHOLDER;
        const card = el("a", { className: "media-card", href: "#", title: s.title });
        card.addEventListener("click", (ev) => { ev.preventDefault(); selectShow(s); });
        const wrap = el("div", { className: "poster-wrap" },
            el("img", { loading: "lazy", src: poster, alt: s.title })
        );
        const meta = el("div", { className: "meta" },
            el("div", { className: "title" }, s.title),
            s.first_air_date ? el("div", { className: "sub" }, s.first_air_date.slice(0, 4)) : null
        );
        card.append(wrap, meta);
        grid.appendChild(card);
    });
}

async function selectShow(s) {
    state.show = s;
    document.getElementById("shows-view").classList.add("hidden");
    document.getElementById("seasons-view").classList.remove("hidden");
    document.getElementById("show-title").textContent = s.title;

    const row = document.getElementById("seasons-row");
    row.innerHTML = "";
    const seasons = await jsonGET(`/api/tv/seasons?show_id=${encodeURIComponent(s.id)}`);
    seasons.forEach((se) => {
        const card = el("a", { className: "media-card sm", href: "#", title: se.title });
        card.addEventListener("click", (ev) => { ev.preventDefault(); selectSeason(se.season); });
        const wrap = el("div", { className: "poster-wrap" },
            el("img", { loading: "lazy", src: s.poster || PLACEHOLDER, alt: se.title })
        );
        const meta = el("div", { className: "meta" }, el("div", { className: "title" }, se.title));
        card.append(wrap, meta);
        row.appendChild(card);
    });
    if (seasons.length) await selectSeason(seasons[0].season);
}

async function selectSeason(n) {
    const grid = document.getElementById("episodes-grid");
    grid.innerHTML = "";
    const eps = await jsonGET(`/api/tv/episodes?show_id=${encodeURIComponent(state.show.id)}&season=${n}`);
    eps.forEach((e) => {
        const still = e.still || PLACEHOLDER;
        const card = el("a", { className: "media-card wide", href: "#", title: e.title });
        const wrap = el("div", { className: "poster-wrap" },
            el("img", { loading: "lazy", src: still, alt: e.title })
        );
        const meta = el("div", { className: "meta" },
            el("div", { className: "title" }, e.title),
            e.air_date ? el("div", { className: "sub" }, e.air_date) : null
        );
        card.append(wrap, meta);
        grid.appendChild(card);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("back-to-shows").addEventListener("click", () => {
        document.getElementById("seasons-view").classList.add("hidden");
        document.getElementById("shows-view").classList.remove("hidden");
        state.show = null;
    });
    loadShows();
});
