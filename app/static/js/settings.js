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
    const server = document.getElementById('form-server');

    // Load existing values
    try {
        if (general) setFormValues(general, await (await fetch('/admin/settings/general')).json());
        if (remote) setFormValues(remote, await (await fetch('/admin/settings/remote')).json());
        if (transcoder) setFormValues(transcoder, await (await fetch('/admin/settings/transcoder')).json());
        if (server) setFormValues(server, await (await fetch('/admin/settings/server')).json());
    } catch (error) {
        console.error('Error loading settings:', error);
    }

    // Save handlers
    general?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('save-general');
        btn.classList.add('is-loading'); btn.disabled = true;
        const body = { general: getFormValues(general) };
        const r = await fetch('/admin/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        document.getElementById('msg-general').textContent = r.ok ? 'Preferences saved.' : 'Save failed';
        btn.classList.remove('is-loading'); btn.disabled = false;
    });

    remote?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('save-remote');
        btn.classList.add('is-loading'); btn.disabled = true;

        try {
            const formData = getFormValues(remote);
            const body = { remote: formData };

            const r = await fetch('/admin/settings', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            btn.classList.remove('is-loading'); btn.disabled = false;

            if (r.ok) {
                document.getElementById('msg-remote').textContent = 'Remote settings saved successfully!';
            } else {
                document.getElementById('msg-remote').textContent = 'Failed to save remote settings';
            }
        } catch (error) {
            btn.classList.remove('is-loading'); btn.disabled = false;
            document.getElementById('msg-remote').textContent = 'Error saving settings: ' + error.message;
        }
    });

    transcoder?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('save-transcoder');
        btn.classList.add('is-loading'); btn.disabled = true;
        const body = { transcoder: getFormValues(transcoder) };
        const r = await fetch('/admin/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        document.getElementById('msg-transcoder').textContent = r.ok ? 'Transcoder settings saved.' : 'Save failed';
        btn.classList.remove('is-loading'); btn.disabled = false;
    });

    // Server settings handlers
    server?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('save-server');
        btn.classList.add('is-loading'); btn.disabled = true;

        const formData = getFormValues(server);

        // Handle external access checkbox
        if (formData.external_access) {
            formData.server_host = '0.0.0.0';
        }

        // Handle SSL settings
        if (!formData.ssl_enabled) {
            formData.ssl_cert_file = '';
            formData.ssl_key_file = '';
        }

        const body = { server: formData };
        const r = await fetch('/admin/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        document.getElementById('msg-server').textContent = r.ok ? 'Server settings saved. Restart required for changes to take effect.' : 'Save failed';
        btn.classList.remove('is-loading'); btn.disabled = false;
    });

    // Presets for quick configuration
    document.getElementById('preset-local')?.addEventListener('click', () => {
        if (!server) return;
        const host = server.elements['server_host'];
        const port = server.elements['server_port'];
        const ext = server.elements['external_access'];
        const ssl = server.elements['ssl_enabled'];
        const cert = server.elements['ssl_cert_file'];
        const key = server.elements['ssl_key_file'];
        host.value = '127.0.0.1';
        port.value = 8085;
        ext.checked = false;
        ssl.checked = false;
        cert.value = '';
        key.value = '';
        document.getElementById('msg-server').textContent = 'Applied preset: local only (HTTP)';
    });

    document.getElementById('preset-https')?.addEventListener('click', () => {
        if (!server) return;
        const host = server.elements['server_host'];
        const port = server.elements['server_port'];
        const ext = server.elements['external_access'];
        const ssl = server.elements['ssl_enabled'];
        host.value = '0.0.0.0';
        port.value = 443;
        ext.checked = true;
        ssl.checked = true;
        document.getElementById('msg-server').textContent = 'Applied preset: HTTPS on 443';
    });

    // When SSL toggled, suggest a sensible port
    server?.elements['ssl_enabled']?.addEventListener('change', (e) => {
        const port = server.elements['server_port'];
        const val = Number(port.value || 0);
        if (e.target.checked) {
            if (!val || val === 8000 || val === 8080 || val === 8085) port.value = 443;
        } else {
            if (val === 443) port.value = 8085;
        }
        updateQuickLinks();
    });

    // Update quick open links
    function updateQuickLinks() {
        if (!server) return;
        const host = (server.elements['server_host'].value || '0.0.0.0');
        const port = Number(server.elements['server_port'].value || 0) || (server.elements['ssl_enabled'].checked ? 443 : 8085);
        const https = !!server.elements['ssl_enabled'].checked;
        const scheme = https ? 'https' : 'http';
        const local = `${scheme}://127.0.0.1:${port}`;
        const domain = (document.querySelector('#form-remote input[name="public_base_url"]').value || '').trim();
        const aLocal = document.getElementById('link-local');
        const aDom = document.getElementById('link-domain');
        if (aLocal) { aLocal.href = local; aLocal.textContent = local; }
        if (aDom) {
            if (domain) {
                const url = domain.match(/^https?:\/\//) ? domain : `${scheme}://${domain}${port===443&&https?'':(':'+port)}`;
                aDom.href = url; aDom.textContent = url; aDom.style.display='inline';
            } else {
                aDom.href = '#'; aDom.textContent = 'domain'; aDom.style.display='none';
            }
        }
    }

    // Initial link update after load
    updateQuickLinks();
    server?.elements['server_port']?.addEventListener('input', updateQuickLinks);
    server?.elements['server_host']?.addEventListener('input', updateQuickLinks);
    document.querySelector('#form-remote input[name="public_base_url"]')?.addEventListener('input', updateQuickLinks);

    // Restart server button
    document.getElementById('restart-server')?.addEventListener('click', async () => {
        if (!confirm('Restart the server? This will disconnect all users.')) return;

        const btn = document.getElementById('restart-server');
        btn.classList.add('is-loading'); btn.disabled = true;
        btn.textContent = 'Restarting...';

        try {
            const r = await fetch('/admin/server/restart', { method: 'POST' });
            if (r.ok) {
                document.getElementById('msg-server').textContent = 'Server restarting... Please wait a moment and refresh the page.';
                setTimeout(() => window.location.reload(), 3000);
            } else {
                document.getElementById('msg-server').textContent = 'Restart failed';
            }
        } catch (e) {
            document.getElementById('msg-server').textContent = 'Restart failed: ' + e.message;
        }

        btn.classList.remove('is-loading'); btn.disabled = false;
        btn.textContent = 'Restart Server';
    });

    // External access checkbox handlers
    document.querySelectorAll('input[name="external_access"]').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const hostInput = e.target.closest('form').querySelector('input[name="server_host"]');
            if (e.target.checked) {
                hostInput.value = '0.0.0.0';
                hostInput.disabled = true;
            } else {
                hostInput.disabled = false;
            }
        });

        // Initialize state
        const hostInput = checkbox.closest('form').querySelector('input[name="server_host"]');
        if (checkbox.checked && hostInput) {
            hostInput.disabled = true;
        }
    });
});
