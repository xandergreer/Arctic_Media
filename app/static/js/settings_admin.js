async function fetchJSON(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Request failed');
    return r.json();
}

document.addEventListener('DOMContentLoaded', async () => {
    // USERS
    const usersTable = document.getElementById('users-table');
    const userForm = document.getElementById('user-create');

    async function loadUsers() {
        if (!usersTable) return;
        const tbody = usersTable.querySelector('tbody');
        tbody.innerHTML = '<tr><td colspan="4">Loading…</td></tr>';
        try {
            const users = await fetchJSON('/admin/users');
            tbody.innerHTML = '';
            for (const u of users) {
                const tr = document.createElement('tr');
                tr.innerHTML = `
          <td>${u.email}</td>
          <td>${u.username}</td>
          <td>
            <select data-act="role" data-id="${u.id}" class="input" style="width:auto">
              <option value="user" ${u.role === 'user' ? 'selected' : ''}>User</option>
              <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
            </select>
          </td>
          <td style="white-space:nowrap">
            <button class="btn btn-secondary" data-act="reset" data-id="${u.id}">Reset PW</button>
            <button class="btn btn-ghost" data-act="delete" data-id="${u.id}">Delete</button>
          </td>`;
                tbody.appendChild(tr);
            }
            if (!users.length) tbody.innerHTML = '<tr><td colspan="4">No users.</td></tr>';
        } catch { tbody.innerHTML = '<tr><td colspan="4">Failed to load users.</td></tr>'; }
    }

    userForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fd = new FormData(userForm);
        const body = Object.fromEntries(fd.entries());
        try {
            await fetchJSON('/admin/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            userForm.reset(); loadUsers();
        } catch (e) { alert(e.message); }
    });

    usersTable?.addEventListener('change', async (e) => {
        const sel = e.target.closest('select[data-act="role"]'); if (!sel) return;
        const id = sel.getAttribute('data-id');
        try {
            await fetchJSON(`/admin/users/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role: sel.value }) });
        } catch (err) { alert(err.message); }
    });

    usersTable?.addEventListener('click', async (e) => {
        const btn = e.target.closest('button'); if (!btn) return;
        const id = btn.getAttribute('data-id');
        const act = btn.getAttribute('data-act');
        try {
            if (act === 'reset') {
                const pw = prompt('New password:'); if (!pw) return;
                await fetchJSON(`/admin/users/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: pw }) });
                alert('Password reset.');
            } else if (act === 'delete') {
                if (!confirm('Delete user?')) return;
                await fetchJSON(`/admin/users/${id}`, { method: 'DELETE' });
                loadUsers();
            }
        } catch (err) { alert(err.message); }
    });

    // TASKS
    const tasksTable = document.getElementById('tasks-table');
    const taskForm = document.getElementById('task-create');
    const libSelect = document.getElementById('task-library');

    async function loadLibrariesForTasks() {
        if (!libSelect) return;
        try {
            const libs = await fetchJSON('/libraries');
            libSelect.innerHTML = libs.map(l => `<option value="${l.id}">${l.name} (${l.type})</option>`).join('');
        } catch { libSelect.innerHTML = ''; }
    }

    async function loadTasks() {
        if (!tasksTable) return;
        const tbody = tasksTable.querySelector('tbody');
        tbody.innerHTML = '<tr><td colspan="6">Loading…</td></tr>';
        try {
            const tasks = await fetchJSON('/admin/tasks');
            tbody.innerHTML = '';
            for (const t of tasks) {
                const tr = document.createElement('tr');
                tr.innerHTML = `
          <td>${t.name}</td>
          <td>${t.job_type}</td>
          <td style="text-align:center">${t.interval_minutes}m</td>
          <td>${t.next_run_at || '—'}</td>
          <td style="text-align:center">
            <input type="checkbox" data-act="enable" data-id="${t.id}" ${t.enabled ? 'checked' : ''}>
          </td>
          <td style="white-space:nowrap">
            <button class="btn btn-secondary" data-act="run" data-id="${t.id}">Run now</button>
            <button class="btn btn-ghost" data-act="delete" data-id="${t.id}">Delete</button>
          </td>`;
                tbody.appendChild(tr);
            }
            if (!tasks.length) tbody.innerHTML = '<tr><td colspan="6">No tasks.</td></tr>';
        } catch { tbody.innerHTML = '<tr><td colspan="6">Failed to load tasks.</td></tr>'; }
    }

    taskForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fd = new FormData(taskForm);
        const body = Object.fromEntries(fd.entries());
        body.interval_minutes = Number(body.interval_minutes || 60);
        try {
            await fetchJSON('/admin/tasks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            taskForm.reset(); loadTasks();
        } catch (err) { alert(err.message); }
    });

    tasksTable?.addEventListener('click', async (e) => {
        const btn = e.target.closest('button'); if (!btn) return;
        const id = btn.getAttribute('data-id');
        const act = btn.getAttribute('data-act');
        try {
            if (act === 'run') {
                btn.classList.add('is-loading'); btn.disabled = true;
                await fetchJSON(`/admin/tasks/${id}/run`, { method: 'POST' });
                setTimeout(() => { btn.classList.remove('is-loading'); btn.disabled = false; }, 600);
            } else if (act === 'delete') {
                if (!confirm('Delete task?')) return;
                await fetchJSON(`/admin/tasks/${id}`, { method: 'DELETE' });
                loadTasks();
            }
        } catch (err) { alert(err.message); }
    });

    tasksTable?.addEventListener('change', async (e) => {
        const cb = e.target.closest('input[type="checkbox"][data-act="enable"]'); if (!cb) return;
        const id = cb.getAttribute('data-id');
        try {
            await fetchJSON(`/admin/tasks/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: cb.checked }) });
        } catch (err) { alert(err.message); cb.checked = !cb.checked; }
    });

    // initial loads
    loadUsers();
    await loadLibrariesForTasks();
    loadTasks();
});
