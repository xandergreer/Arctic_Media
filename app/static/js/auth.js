// app/static/js/auth.js
(() => {
    const $ = (id) => document.getElementById(id);

    async function post(url, body) {
        const r = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(body),
        });
        let data = null;
        try { data = await r.json(); } catch { }
        if (!r.ok) {
            const detail = (data && (data.detail || data.message)) || `HTTP ${r.status}`;
            throw new Error(detail);
        }
        return data;
    }

    // ---- LOGIN ----
    const loginForm = $('login-form');
    const loginBtn = $('login-btn');
    const loginMsg = $('login-msg');

    loginForm?.addEventListener('submit', async (e) => {
        // Get return URL from query params and add to form action
        const params = new URLSearchParams(window.location.search);
        const returnUrl = params.get('return_url');
        if (returnUrl) {
            loginForm.action = `/auth/login?return_url=${encodeURIComponent(returnUrl)}`;
        }
        
        // Don't prevent default - let the form submit naturally
        // This ensures cookies are set properly by the browser
        // The server will redirect after setting cookies
    });

    // ---- REGISTER ----
    const regForm = $('register-form');
    const regBtn = $('register-btn');
    const regMsg = $('register-msg');

    regForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        regMsg && (regMsg.textContent = '');
        if (regBtn) { regBtn.disabled = true; regBtn.classList.add('is-loading'); }

        const fd = new FormData(regForm);
        const body = {
            email: fd.get('email'),
            username: fd.get('username'),
            password: fd.get('password'),
        };

        try {
            await post('/auth/register', body);
            // after register, auto-login
            await post('/auth/login', { identifier: body.username, password: body.password });
            window.location.href = '/';
        } catch (err) {
            if (regMsg) regMsg.textContent = err.message || 'Registration failed';
        } finally {
            if (regBtn) { regBtn.disabled = false; regBtn.classList.remove('is-loading'); }
        }
    });
})();
