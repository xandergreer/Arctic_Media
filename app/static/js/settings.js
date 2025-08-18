function setFormValues(form, obj) {
    for (const [k, v] of Object.entries(obj || {})) {
        const el = form.elements[k];
        if (!el) continue;
        if (el.type === 'checkbox') el.checked = !!v;
        else el.value = v ?? '';
    }
}

function getFormValues(form) {
    const out = {};
    for (const el of form.elements) {
        if (!el.name) continue;
        out[el.name] = el.type === 'checkbox' ? el.checked : (el.type === 'number' ? Number(el.value) : el.value);
    }
    return out;
}

document.addEventListener('DOMContentLoaded', async () => {
    const general = document.getElementById('form-general');
    const remote = document.getElementById('form-remote');
    const transcoder = document.getElementById('form-transcoder');

    // Load existing values
    try {
        if (general) setFormValues(general, await (await fetch('/admin/settings/general')).json());
        if (remote) setFormValues(remote, await (await fetch('/admin/settings/remote')).json());
        if (transcoder) setFormValues(transcoder, await (await fetch('/admin/settings/transcoder')).json());
    } catch { }

    // Save handlers
    general?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('save-general');
        btn.classList.add('is-loading'); btn.disabled = true;
        const body = { general: getFormValues(general) };
        const r = await fetch('/admin/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        document.getElementById('msg-general').textContent = r.ok ? 'Saved.' : 'Save failed';
        btn.classList.remove('is-loading'); btn.disabled = false;
    });

    remote?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('save-remote');
        btn.classList.add('is-loading'); btn.disabled = true;
        const body = { remote: getFormValues(remote) };
        const r = await fetch('/admin/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        document.getElementById('msg-remote').textContent = r.ok ? 'Saved.' : 'Save failed';
        btn.classList.remove('is-loading'); btn.disabled = false;
    });

    transcoder?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('save-transcoder');
        btn.classList.add('is-loading'); btn.disabled = true;
        const body = { transcoder: getFormValues(transcoder) };
        const r = await fetch('/admin/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        document.getElementById('msg-transcoder').textContent = r.ok ? 'Saved.' : 'Save failed';
        btn.classList.remove('is-loading'); btn.disabled = false;
    });
});
