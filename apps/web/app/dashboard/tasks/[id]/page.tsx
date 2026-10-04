'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { api, mediaUrl } from '@/lib/api';
import { getSocket } from '@/lib/socket';

const TaskMap = dynamic(() => import('@/components/TaskMap'), { ssr: false });

interface Proof {
  id: string;
  type: 'PHOTO' | 'SIGNATURE' | 'NOTE';
  content: string;
  createdAt: string;
}

interface Task {
  id: string;
  title: string;
  description: string | null;
  status: string;
  lat: number;
  lng: number;
  address: string;
  dueAt: string;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
  fieldStaff: { id: string; firstName: string; lastName: string } | null;
  proofs: Proof[];
}

interface RouteData {
  status: string;
  destination: { lat: number; lng: number };
  points: { lat: number; lng: number; recordedAt: string }[];
  totalDistanceKm: number;
  durationMinutes: number;
  live: { userId: string; lat: number; lng: number } | null;
}

const STATUS_COLORS: Record<string, string> = {
  UNASSIGNED: 'bg-slate-100 text-slate-600',
  ASSIGNED: 'bg-blue-100 text-blue-700',
  EN_ROUTE: 'bg-amber-100 text-amber-700',
  IN_PROGRESS: 'bg-purple-100 text-purple-700',
  COMPLETED: 'bg-green-100 text-green-700',
  CANCELLED: 'bg-red-100 text-red-700',
};

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [task, setTask] = useState<Task | null>(null);
  const [route, setRoute] = useState<RouteData | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const [t, r] = await Promise.all([
      api<Task>(`/tasks/${id}`),
      api<RouteData>(`/tasks/${id}/route`),
    ]);
    setTask(t);
    setRoute(r);
  }, [id]);

  useEffect(() => {
    load().catch((e) => setError(String(e)));

    // Live updates: refresh the route (live marker) on pings, and the whole
    // task when its status changes.
    const socket = getSocket();
    const onSync = () => api<RouteData>(`/tasks/${id}/route`).then(setRoute).catch(() => {});
    const onTask = () => load().catch(() => {});
    socket.on('location_sync', onSync);
    socket.on('task_updated', onTask);
    return () => {
      socket.off('location_sync', onSync);
      socket.off('task_updated', onTask);
    };
  }, [id, load]);

  if (error) {
    return (
      <div className="space-y-4">
        <Link href="/dashboard/tasks" className="text-sm text-slate-500 underline">
          ← Back to tasks
        </Link>
        <p className="text-red-600">{error}</p>
      </div>
    );
  }
  if (!task || !route) return <p className="text-slate-500">Loading…</p>;

  const completed = task.status === 'COMPLETED';
  const notes = task.proofs.filter((p) => p.type === 'NOTE');
  const photos = task.proofs.filter((p) => p.type === 'PHOTO');
  const assignee = task.fieldStaff
    ? `${task.fieldStaff.firstName} ${task.fieldStaff.lastName}`
    : 'Unassigned';

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <Link href="/dashboard/tasks" className="text-sm text-slate-500 underline">
          ← Back to tasks
        </Link>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            STATUS_COLORS[task.status] ?? ''
          }`}
        >
          {task.status}
        </span>
      </div>

      <div>
        <h1 className="text-2xl font-semibold">{task.title}</h1>
        <p className="text-sm text-slate-500">{task.address}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Assignee" value={assignee} />
        <Stat label="Due" value={new Date(task.dueAt).toLocaleString()} />
        <Stat
          label={completed ? 'Distance travelled' : 'Trail so far'}
          value={`${route.totalDistanceKm} km`}
        />
        <Stat
          label={completed ? 'Completed' : 'Status since'}
          value={
            completed && task.completedAt
              ? new Date(task.completedAt).toLocaleString()
              : task.startedAt
                ? new Date(task.startedAt).toLocaleString()
                : '—'
          }
        />
      </div>

      {/* Map */}
      <div className="h-[420px] overflow-hidden rounded-xl border">
        <TaskMap
          destination={route.destination}
          live={route.live}
          travelled={route.points}
          completed={completed}
          staffName={task.fieldStaff ? assignee : undefined}
        />
      </div>
      <p className="text-xs text-slate-500">
        {completed
          ? '🟢 start → 📍 destination shows the full route the worker travelled.'
          : '📍 destination · 🟣 the worker’s live position · dashed line is the road route to the destination (updates in real time).'}
      </p>

      {task.description && (
        <section className="rounded-xl border bg-white p-4">
          <h2 className="mb-1 text-sm font-medium">Description</h2>
          <p className="text-sm text-slate-600">{task.description}</p>
        </section>
      )}

      {/* Photos */}
      <section className="rounded-xl border bg-white p-4">
        <h2 className="mb-3 text-sm font-medium">Photo attachments ({photos.length})</h2>
        {photos.length === 0 ? (
          <p className="text-sm text-slate-500">No photos uploaded yet.</p>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {photos.map((p) => (
              <a
                key={p.id}
                href={mediaUrl(p.content)}
                target="_blank"
                rel="noopener noreferrer"
                className="block overflow-hidden rounded-lg border"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={mediaUrl(p.content)}
                  alt="Task proof"
                  className="h-32 w-full object-cover transition hover:opacity-90"
                />
              </a>
            ))}
          </div>
        )}
      </section>

      {/* Notes */}
      <section className="rounded-xl border bg-white p-4">
        <h2 className="mb-3 text-sm font-medium">Work notes ({notes.length})</h2>
        {notes.length === 0 ? (
          <p className="text-sm text-slate-500">No notes added yet.</p>
        ) : (
          <ul className="space-y-2">
            {notes.map((n) => (
              <li key={n.id} className="rounded-lg bg-slate-50 p-3 text-sm">
                <p className="text-slate-700">{n.content}</p>
                <p className="mt-1 text-xs text-slate-400">
                  {new Date(n.createdAt).toLocaleString()}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-white p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm font-semibold">{value}</p>
    </div>
  );
}
