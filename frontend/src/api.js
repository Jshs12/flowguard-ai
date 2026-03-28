const API = import.meta.env.VITE_API_URL || 'https://flowguard-ai.onrender.com';

export async function api(path, options = {}) {
  const token = localStorage.getItem('fg_token');
  const headers = { ...options.headers };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Only set Content-Type for non-FormData bodies
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('fg_token');
    localStorage.removeItem('fg_user');
    window.location.reload();
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }

  return res.json();
}

export function getUser() {
  const raw = localStorage.getItem('fg_user');
  return raw ? JSON.parse(raw) : null;
}

export function setAuth(data) {
  localStorage.setItem('fg_token', data.access_token);
  localStorage.setItem('fg_user', JSON.stringify({
    username: data.username,
    role: data.role,
    full_name: data.full_name,
    user_id: data.user_id,
  }));
}

export function logout() {
  localStorage.removeItem('fg_token');
  localStorage.removeItem('fg_user');
  window.location.reload();
}

export async function checkHealth() {
  try {
    const res = await fetch(`${API}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function autoAssign(data) {
  return api('/api/tasks/auto-assign', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
