const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

/** Absolute URL for a server media path (e.g. proof photo) like "/media/...". */
export function mediaUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  const origin = BASE.replace(/\/api\/v1\/?$/, '');
  return `${origin}${path}`;
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('ft_token');
}

export interface SessionUser {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: 'SUPER_ADMIN' | 'TENANT_ADMIN' | 'DISPATCHER' | 'FIELD_STAFF';
  tenantId: string | null;
  tenantName: string | null;
}

export function getUser(): SessionUser | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem('ft_user');
  return raw ? JSON.parse(raw) : null;
}

export function setSession(token: string, user: SessionUser) {
  localStorage.setItem('ft_token', token);
  localStorage.setItem('ft_user', JSON.stringify(user));
}

/** Patch the stored session user after a profile edit so the UI stays in sync. */
export function updateStoredUser(patch: Partial<SessionUser>) {
  const user = getUser();
  if (!user) return;
  localStorage.setItem('ft_user', JSON.stringify({ ...user, ...patch }));
}

export function clearSession() {
  localStorage.removeItem('ft_token');
  localStorage.removeItem('ft_user');
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });
  if (res.status === 401) {
    clearSession();
    if (typeof window !== 'undefined') window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // DRF errors arrive as {detail} or {field: [messages]}.
    const firstFieldError = Object.values(body).flat().find((v) => typeof v === 'string');
    throw new Error(body.detail ?? body.message ?? firstFieldError ?? `Request failed (${res.status})`);
  }
  return res.json();
}
