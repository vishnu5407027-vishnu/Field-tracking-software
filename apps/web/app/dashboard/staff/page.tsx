'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { api, getUser } from '@/lib/api';

interface Member {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: string;
  isClockedIn: boolean;
}

const ROLES = ['FIELD_STAFF', 'DISPATCHER', 'TENANT_ADMIN'];

export default function StaffPage() {
  const me = getUser();
  const isAdmin = me?.role === 'TENANT_ADMIN';
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    email: '',
    password: '',
    firstName: '',
    lastName: '',
    role: 'FIELD_STAFF',
  });

  const [editing, setEditing] = useState<Member | null>(null);
  const [resetting, setResetting] = useState<Member | null>(null);

  const refresh = useCallback(async () => {
    setMembers(await api<Member[]>('/users'));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function invite(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await api('/users', { method: 'POST', body: JSON.stringify(form) });
      setForm({ email: '', password: '', firstName: '', lastName: '', role: 'FIELD_STAFF' });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    }
  }

  async function changeRole(m: Member, role: string) {
    if (role === m.role) return;
    try {
      await api(`/users/${m.id}/role`, { method: 'PATCH', body: JSON.stringify({ role }) });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to change role');
    }
  }

  async function remove(m: Member) {
    if (!confirm(`Delete ${m.firstName} ${m.lastName}? This cannot be undone.`)) return;
    try {
      await api(`/users/${m.id}`, { method: 'DELETE' });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete');
    }
  }

  const input = 'rounded-md border px-3 py-2 text-sm';

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Team</h1>

      {isAdmin && (
        <form onSubmit={invite} className="flex flex-wrap gap-3 rounded-xl border bg-white p-4">
          <input className={input} placeholder="Email" type="email" required
            value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input className={input} placeholder="Temp password" type="password" required minLength={8}
            value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <input className={input} placeholder="First name" required
            value={form.firstName} onChange={(e) => setForm({ ...form, firstName: e.target.value })} />
          <input className={input} placeholder="Last name" required
            value={form.lastName} onChange={(e) => setForm({ ...form, lastName: e.target.value })} />
          <select className={input} value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="FIELD_STAFF">Field staff</option>
            <option value="DISPATCHER">Dispatcher</option>
            <option value="TENANT_ADMIN">Tenant admin</option>
          </select>
          <button className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">Invite</button>
          {error && <p className="w-full text-sm text-red-600">{error}</p>}
        </form>
      )}

      <div className="overflow-hidden rounded-xl border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-3">Name</th>
              <th className="p-3">Email</th>
              <th className="p-3">Role</th>
              <th className="p-3">On duty</th>
              {isAdmin && <th className="p-3 text-right">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id} className="border-t">
                <td className="p-3 font-medium">
                  {m.firstName} {m.lastName}
                  {m.id === me?.id && <span className="ml-1 text-xs text-slate-400">(you)</span>}
                </td>
                <td className="p-3">{m.email}</td>
                <td className="p-3">
                  {isAdmin && m.id !== me?.id ? (
                    <select
                      className="rounded-md border px-2 py-1 text-xs"
                      value={m.role}
                      onChange={(e) => changeRole(m, e.target.value)}
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                  ) : (
                    m.role
                  )}
                </td>
                <td className="p-3">
                  {m.role === 'FIELD_STAFF' ? (
                    <span className={m.isClockedIn ? 'text-green-600' : 'text-slate-400'}>
                      {m.isClockedIn ? '● Clocked in' : '○ Off duty'}
                    </span>
                  ) : '—'}
                </td>
                {isAdmin && (
                  <td className="p-3">
                    <div className="flex justify-end gap-3 text-xs">
                      <button className="text-slate-600 underline" onClick={() => setEditing(m)}>
                        Edit
                      </button>
                      <button className="text-slate-600 underline" onClick={() => setResetting(m)}>
                        Reset password
                      </button>
                      {m.id !== me?.id && (
                        <button className="text-red-600 underline" onClick={() => remove(m)}>
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <EditModal
          member={editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await refresh();
          }}
        />
      )}
      {resetting && (
        <ResetModal member={resetting} onClose={() => setResetting(null)} />
      )}
    </div>
  );
}

function Modal({ title, children, onClose }: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-xl bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-lg font-semibold">{title}</h2>
        {children}
      </div>
    </div>
  );
}

const fieldCls = 'w-full rounded-md border px-3 py-2 text-sm';

function EditModal({ member, onClose, onSaved }: {
  member: Member;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    firstName: member.firstName,
    lastName: member.lastName,
    email: member.email,
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api(`/users/${member.id}`, { method: 'PATCH', body: JSON.stringify(form) });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
      setBusy(false);
    }
  }

  return (
    <Modal title={`Edit ${member.firstName} ${member.lastName}`} onClose={onClose}>
      <form onSubmit={save} className="space-y-3">
        <input className={fieldCls} placeholder="First name" required
          value={form.firstName} onChange={(e) => setForm({ ...form, firstName: e.target.value })} />
        <input className={fieldCls} placeholder="Last name" required
          value={form.lastName} onChange={(e) => setForm({ ...form, lastName: e.target.value })} />
        <input className={fieldCls} type="email" placeholder="Email" required
          value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="rounded-md px-4 py-2 text-sm text-slate-600" onClick={onClose}>
            Cancel
          </button>
          <button disabled={busy} className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50">
            {busy ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ResetModal({ member, onClose }: { member: Member; onClose: () => void }) {
  const [pw, setPw] = useState({ next: '', confirm: '' });
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (pw.next !== pw.confirm) {
      setError('Passwords do not match');
      return;
    }
    setBusy(true);
    try {
      await api(`/users/${member.id}/password`, {
        method: 'POST',
        body: JSON.stringify({ newPassword: pw.next }),
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={`Reset password — ${member.firstName} ${member.lastName}`} onClose={onClose}>
      {done ? (
        <div className="space-y-4">
          <p className="text-sm text-green-600">
            Password updated. Share the new password with {member.firstName}.
          </p>
          <div className="flex justify-end">
            <button className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white" onClick={onClose}>
              Done
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={save} className="space-y-3">
          <input className={fieldCls} type="password" placeholder="New password" required minLength={8}
            value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} />
          <input className={fieldCls} type="password" placeholder="Confirm new password" required minLength={8}
            value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" className="rounded-md px-4 py-2 text-sm text-slate-600" onClick={onClose}>
              Cancel
            </button>
            <button disabled={busy} className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50">
              {busy ? 'Saving…' : 'Set password'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
