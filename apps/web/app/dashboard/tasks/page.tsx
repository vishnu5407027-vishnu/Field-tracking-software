'use client';

import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { getSocket } from '@/lib/socket';

// Leaflet touches `window`, so the picker must render client-side only.
const LocationPicker = dynamic(() => import('@/components/LocationPicker'), {
  ssr: false,
});

interface Task {
  id: string;
  title: string;
  status: string;
  address: string;
  dueAt: string;
  fieldStaff: { id: string; firstName: string; lastName: string } | null;
}

interface StaffUser {
  id: string;
  firstName: string;
  lastName: string;
  role: string;
}

const STATUS_COLORS: Record<string, string> = {
  UNASSIGNED: 'bg-slate-100 text-slate-600',
  ASSIGNED: 'bg-blue-100 text-blue-700',
  EN_ROUTE: 'bg-amber-100 text-amber-700',
  IN_PROGRESS: 'bg-purple-100 text-purple-700',
  COMPLETED: 'bg-green-100 text-green-700',
  CANCELLED: 'bg-red-100 text-red-700',
};

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [staff, setStaff] = useState<StaffUser[]>([]);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    title: '',
    address: '',
    lat: '',
    lng: '',
    fieldStaffId: '',
    dueAt: '',
  });

  const refresh = useCallback(async () => {
    setTasks(await api<Task[]>('/tasks'));
  }, []);

  useEffect(() => {
    refresh();
    api<StaffUser[]>('/users').then((users) =>
      setStaff(users.filter((u) => u.role === 'FIELD_STAFF')),
    );
    const socket = getSocket();
    const onUpdate = () => refresh();
    socket.on('task_updated', onUpdate);
    return () => {
      socket.off('task_updated', onUpdate);
    };
  }, [refresh]);

  async function createTask(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await api('/tasks', {
        method: 'POST',
        body: JSON.stringify({
          title: form.title,
          address: form.address,
          lat: Number(form.lat),
          lng: Number(form.lng),
          fieldStaffId: form.fieldStaffId || undefined,
          dueAt: new Date(form.dueAt).toISOString(),
        }),
      });
      setForm({ title: '', address: '', lat: '', lng: '', fieldStaffId: '', dueAt: '' });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    }
  }

  const input = 'rounded-md border px-3 py-2 text-sm';

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Task Dispatch</h1>

      <form onSubmit={createTask} className="space-y-3 rounded-xl border bg-white p-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <input className={input} placeholder="Title" required
            value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input className={input} placeholder="Address" required
            value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <select className={input} value={form.fieldStaffId}
            onChange={(e) => setForm({ ...form, fieldStaffId: e.target.value })}>
            <option value="">Unassigned</option>
            {staff.map((u) => (
              <option key={u.id} value={u.id}>{u.firstName} {u.lastName}</option>
            ))}
          </select>
          <input className={input} type="datetime-local" required
            value={form.dueAt} onChange={(e) => setForm({ ...form, dueAt: e.target.value })} />
          <input className={input} placeholder="Latitude" type="number" step="any" required
            value={form.lat} onChange={(e) => setForm({ ...form, lat: e.target.value })} />
          <input className={input} placeholder="Longitude" type="number" step="any" required
            value={form.lng} onChange={(e) => setForm({ ...form, lng: e.target.value })} />
        </div>
        <div className="h-64 overflow-hidden rounded-lg border">
          <LocationPicker
            value={
              form.lat !== '' && form.lng !== ''
                ? { lat: Number(form.lat), lng: Number(form.lng) }
                : null
            }
            onPick={(pos) =>
              setForm((f) => ({
                ...f,
                lat: pos.lat.toFixed(6),
                lng: pos.lng.toFixed(6),
              }))
            }
            onResolveAddress={(label) => setForm((f) => ({ ...f, address: label }))}
          />
        </div>
        <p className="text-xs text-slate-500">
          Search a place, or click the map to mark the task location — drag the pin to fine-tune.
        </p>
        <button className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">
          Dispatch task
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>

      <div className="overflow-hidden rounded-xl border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-3">Task</th>
              <th className="p-3">Assignee</th>
              <th className="p-3">Due</th>
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr
                key={t.id}
                className="cursor-pointer border-t hover:bg-slate-50"
                onClick={() => router.push(`/dashboard/tasks/${t.id}`)}
              >
                <td className="p-3">
                  <span className="font-medium text-slate-900 underline-offset-2 hover:underline">
                    {t.title}
                  </span>
                  <br />
                  <span className="text-xs text-slate-500">{t.address}</span>
                </td>
                <td className="p-3">
                  {t.fieldStaff
                    ? `${t.fieldStaff.firstName} ${t.fieldStaff.lastName}`
                    : '—'}
                </td>
                <td className="p-3">{new Date(t.dueAt).toLocaleString()}</td>
                <td className="p-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_COLORS[t.status] ?? ''}`}>
                    {t.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
