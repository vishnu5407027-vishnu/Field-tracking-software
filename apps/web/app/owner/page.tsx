'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { api, clearSession, getUser } from '@/lib/api';

interface Analytics {
  tenantsByStatus: Record<string, number>;
  totalFieldStaff: number;
  onlineFieldStaff: number;
  mrrInr: number;
}

interface TenantRow {
  id: string;
  name: string;
  slug: string;
  planTier: string;
  status: string;
  seatLimit: number;
  fieldStaffCount: number;
}

export default function OwnerPortal() {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    name: '',
    slug: '',
    planTier: 'BASIC',
    adminEmail: '',
    adminPassword: '',
    adminFirstName: '',
    adminLastName: '',
  });

  // The owner portal is SUPER_ADMIN-only — send everyone else where they
  // belong instead of rendering a portal whose every API call 403s.
  useEffect(() => {
    const user = getUser();
    if (!user) router.replace('/login');
    else if (user.role !== 'SUPER_ADMIN') router.replace('/dashboard');
    else setAuthorized(true);
  }, [router]);

  const refresh = useCallback(async () => {
    const [a, t] = await Promise.all([
      api<Analytics>('/owner/analytics'),
      api<TenantRow[]>('/owner/tenants'),
    ]);
    setAnalytics(a);
    setTenants(t);
  }, []);

  useEffect(() => {
    if (authorized) refresh().catch((e) => setError(String(e)));
  }, [authorized, refresh]);

  async function createTenant(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await api('/owner/tenants', { method: 'POST', body: JSON.stringify(form) });
      setForm({
        name: '', slug: '', planTier: 'BASIC',
        adminEmail: '', adminPassword: '', adminFirstName: '', adminLastName: '',
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    }
  }

  async function toggleStatus(t: TenantRow) {
    const status = t.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    await api(`/owner/tenants/${t.id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
    await refresh();
  }

  const input = 'rounded-md border px-3 py-2 text-sm';

  if (!authorized) return null;

  return (
    <main className="mx-auto max-w-6xl space-y-8 p-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Owner Portal</h1>
        <div className="flex items-center gap-4">
          <Link href="/profile" className="text-sm text-slate-500 underline">
            Profile
          </Link>
          <button
            className="text-sm text-slate-500 underline"
            onClick={() => { clearSession(); window.location.href = '/login'; }}
          >
            Sign out
          </button>
        </div>
      </header>

      {analytics && (
        <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {[
            ['Active tenants', analytics.tenantsByStatus.ACTIVE ?? 0],
            ['Field staff (total)', analytics.totalFieldStaff],
            ['Field staff online', analytics.onlineFieldStaff],
            ['MRR (₹)', analytics.mrrInr.toLocaleString('en-IN')],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-xl border bg-white p-4">
              <p className="text-sm text-slate-500">{label}</p>
              <p className="text-2xl font-semibold">{value}</p>
            </div>
          ))}
        </section>
      )}

      <section className="rounded-xl border bg-white p-6">
        <h2 className="mb-4 font-medium">Provision new tenant</h2>
        <form onSubmit={createTenant} className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <input className={input} placeholder="Company name" required
            value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className={input} placeholder="slug (a-z, 0-9, -)" required pattern="[a-z0-9-]+"
            value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
          <select className={input} value={form.planTier}
            onChange={(e) => setForm({ ...form, planTier: e.target.value })}>
            <option>BASIC</option><option>PRO</option><option>ENTERPRISE</option>
          </select>
          <input className={input} placeholder="Admin email" type="email" required
            value={form.adminEmail} onChange={(e) => setForm({ ...form, adminEmail: e.target.value })} />
          <input className={input} placeholder="Admin password" type="password" required minLength={8}
            value={form.adminPassword} onChange={(e) => setForm({ ...form, adminPassword: e.target.value })} />
          <input className={input} placeholder="Admin first name" required
            value={form.adminFirstName} onChange={(e) => setForm({ ...form, adminFirstName: e.target.value })} />
          <input className={input} placeholder="Admin last name" required
            value={form.adminLastName} onChange={(e) => setForm({ ...form, adminLastName: e.target.value })} />
          <button className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white">
            Create tenant
          </button>
        </form>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </section>

      <section className="overflow-hidden rounded-xl border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-3">Tenant</th>
              <th className="p-3">Plan</th>
              <th className="p-3">Seats used</th>
              <th className="p-3">Status</th>
              <th className="p-3" />
            </tr>
          </thead>
          <tbody>
            {tenants.map((t) => (
              <tr key={t.id} className="border-t">
                <td className="p-3">
                  <span className="font-medium">{t.name}</span>{' '}
                  <span className="text-slate-400">/{t.slug}</span>
                </td>
                <td className="p-3">{t.planTier}</td>
                <td className="p-3">{t.fieldStaffCount} / {t.seatLimit}</td>
                <td className="p-3">
                  <span className={t.status === 'ACTIVE'
                    ? 'rounded-full bg-green-100 px-2 py-0.5 text-green-700'
                    : 'rounded-full bg-red-100 px-2 py-0.5 text-red-700'}>
                    {t.status}
                  </span>
                </td>
                <td className="p-3 text-right">
                  <button className="text-sm underline" onClick={() => toggleStatus(t)}>
                    {t.status === 'ACTIVE' ? 'Suspend' : 'Activate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
