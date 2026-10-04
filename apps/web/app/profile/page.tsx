'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { api, getUser, updateStoredUser } from '@/lib/api';

interface Profile {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: string;
  tenantName: string | null;
  createdAt: string;
}

const ROLE_LABELS: Record<string, string> = {
  SUPER_ADMIN: 'Platform Owner',
  TENANT_ADMIN: 'Tenant Admin',
  DISPATCHER: 'Dispatcher',
  FIELD_STAFF: 'Field Staff',
};

export default function ProfilePage() {
  const router = useRouter();
  const [home, setHome] = useState('/dashboard');
  const [ready, setReady] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '' });
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' });
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [pwMsg, setPwMsg] = useState('');
  const [pwErr, setPwErr] = useState('');

  const load = useCallback(async () => {
    const me = await api<Profile>('/me');
    setProfile(me);
    setForm({ firstName: me.firstName, lastName: me.lastName, email: me.email });
  }, []);

  useEffect(() => {
    const user = getUser();
    if (!user) {
      router.replace('/login');
      return;
    }
    setHome(user.role === 'SUPER_ADMIN' ? '/owner' : '/dashboard');
    setReady(true);
    load().catch((e) => setErr(String(e)));
  }, [router, load]);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setMsg('');
    setErr('');
    try {
      const updated = await api<Profile>('/me', {
        method: 'PATCH',
        body: JSON.stringify(form),
      });
      setProfile(updated);
      updateStoredUser({
        firstName: updated.firstName,
        lastName: updated.lastName,
        email: updated.email,
      });
      setMsg('Profile updated');
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Update failed');
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setPwMsg('');
    setPwErr('');
    if (pw.next !== pw.confirm) {
      setPwErr('New passwords do not match');
      return;
    }
    try {
      await api('/me/password', {
        method: 'POST',
        body: JSON.stringify({ currentPassword: pw.current, newPassword: pw.next }),
      });
      setPw({ current: '', next: '', confirm: '' });
      setPwMsg('Password updated');
    } catch (e) {
      setPwErr(e instanceof Error ? e.message : 'Could not change password');
    }
  }

  if (!ready) return null;

  const input = 'w-full rounded-md border px-3 py-2 text-sm';
  const initials = profile
    ? (profile.firstName[0] ?? '') + (profile.lastName[0] ?? '')
    : '';

  return (
    <main className="mx-auto max-w-2xl space-y-6 p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">My Profile</h1>
        <Link href={home} className="text-sm text-slate-500 underline">
          ← Back
        </Link>
      </div>

      {profile && (
        <section className="flex items-center gap-4 rounded-xl border bg-white p-6">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-900 text-xl font-semibold uppercase text-white">
            {initials}
          </div>
          <div>
            <p className="text-lg font-semibold">
              {profile.firstName} {profile.lastName}
            </p>
            <p className="text-sm text-slate-500">{profile.email}</p>
            <p className="mt-1 text-xs text-slate-500">
              {ROLE_LABELS[profile.role] ?? profile.role}
              {profile.tenantName ? ` · ${profile.tenantName}` : ''} · Member since{' '}
              {new Date(profile.createdAt).toLocaleDateString()}
            </p>
          </div>
        </section>
      )}

      <section className="rounded-xl border bg-white p-6">
        <h2 className="mb-4 font-medium">Edit details</h2>
        <form onSubmit={saveProfile} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm">
              <span className="mb-1 block text-slate-600">First name</span>
              <input
                className={input}
                required
                value={form.firstName}
                onChange={(e) => setForm({ ...form, firstName: e.target.value })}
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-slate-600">Last name</span>
              <input
                className={input}
                required
                value={form.lastName}
                onChange={(e) => setForm({ ...form, lastName: e.target.value })}
              />
            </label>
          </div>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-600">Email</span>
            <input
              className={input}
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </label>
          <div className="flex items-center gap-3">
            <button className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white">
              Save changes
            </button>
            {msg && <span className="text-sm text-green-600">{msg}</span>}
            {err && <span className="text-sm text-red-600">{err}</span>}
          </div>
        </form>
      </section>

      <section className="rounded-xl border bg-white p-6">
        <h2 className="mb-4 font-medium">Change password</h2>
        <form onSubmit={changePassword} className="space-y-3">
          <input
            className={input}
            type="password"
            placeholder="Current password"
            required
            value={pw.current}
            onChange={(e) => setPw({ ...pw, current: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              className={input}
              type="password"
              placeholder="New password"
              required
              minLength={8}
              value={pw.next}
              onChange={(e) => setPw({ ...pw, next: e.target.value })}
            />
            <input
              className={input}
              type="password"
              placeholder="Confirm new password"
              required
              minLength={8}
              value={pw.confirm}
              onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
            />
          </div>
          <div className="flex items-center gap-3">
            <button className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white">
              Update password
            </button>
            {pwMsg && <span className="text-sm text-green-600">{pwMsg}</span>}
            {pwErr && <span className="text-sm text-red-600">{pwErr}</span>}
          </div>
        </form>
      </section>
    </main>
  );
}
