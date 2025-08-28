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
        if (remote) {
            // Load both remote and server settings for the remote form
            const [remoteSettings, serverSettings] = await Promise.all([
                fetch('/admin/settings/remote').then(r => r.json()),
                fetch('/admin/settings/server').then(r => r.json())
            ]);

            // Merge settings for the remote form
            const combinedSettings = { ...remoteSettings, ...serverSettings };
            setFormValues(remote, combinedSettings);
        }
        if (transcoder) setFormValues(transcoder, await (await fetch('/admin/settings/transcoder')).json());
        if (server) {
            const serverSettings = await (await fetch('/admin/settings/server')).json();
            setFormValues(server, serverSettings);
        }
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
        document.getElementById('msg-general').textContent = r.ok ? 'Saved.' : 'Save failed';
        btn.classList.remove('is-loading'); btn.disabled = false;
    });

    remote?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('save-remote');
        btn.classList.add('is-loading'); btn.disabled = true;

        try {
            // Split form data into remote and server settings
            const formData = getFormValues(remote);
            const remoteSettings = {
                enable_remote_access: formData.enable_remote_access,
                public_base_url: formData.public_base_url,
                port: formData.port,
                upnp: formData.upnp,
                allow_insecure_fallback: formData.allow_insecure_fallback
            };

            const serverSettings = {
                server_host: formData.server_host,
                server_port: formData.server_port,
                external_access: formData.external_access
            };

            const body = {
                remote: remoteSettings,
                server: serverSettings
            };

            const r = await fetch('/admin/settings', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            btn.classList.remove('is-loading'); btn.disabled = false;

            if (r.ok) {
                document.getElementById('msg-remote').textContent = 'Settings saved successfully! Server restart may be required for port changes.';
            } else {
                document.getElementById('msg-remote').textContent = 'Failed to save settings';
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
        document.getElementById('msg-transcoder').textContent = r.ok ? 'Saved.' : 'Save failed';
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

        const body = { server: formData };
        const r = await fetch('/admin/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        document.getElementById('msg-server').textContent = r.ok ? 'Server settings saved. Restart required for changes to take effect.' : 'Save failed';
        btn.classList.remove('is-loading'); btn.disabled = false;
    });

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
