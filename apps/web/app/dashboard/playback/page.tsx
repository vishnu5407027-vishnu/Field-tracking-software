'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const PlaybackMap = dynamic(() => import('@/components/PlaybackMap'), {
  ssr: false,
});

interface StaffUser {
  id: string;
  firstName: string;
  lastName: string;
  role: string;
}

interface History {
  points: { lat: number; lng: number; recordedAt: string }[];
  totalDistanceKm: number;
  idleMinutes: number;
  activeMinutes: number;
}

export default function PlaybackPage() {
  const [staff, setStaff] = useState<StaffUser[]>([]);
  const [userId, setUserId] = useState('');
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [history, setHistory] = useState<History | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<StaffUser[]>('/users').then((users) =>
      setStaff(users.filter((u) => u.role === 'FIELD_STAFF')),
    );
  }, []);

  async function load() {
    if (!userId) return;
    setLoading(true);
    try {
      setHistory(
        await api<History>(`/locations/history?userId=${userId}&date=${date}`),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-3rem)] flex-col gap-4">
      <h1 className="text-xl font-semibold">Route Playback</h1>

      <div className="flex flex-wrap items-center gap-3">
        <select
          className="rounded-md border px-3 py-2 text-sm"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        >
          <option value="">Select field staff…</option>
          {staff.map((u) => (
            <option key={u.id} value={u.id}>
              {u.firstName} {u.lastName}
            </option>
          ))}
        </select>
        <input
          type="date"
          className="rounded-md border px-3 py-2 text-sm"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <button
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
          onClick={load}
          disabled={!userId || loading}
        >
          {loading ? 'Loading…' : 'Load route'}
        </button>

        {history && (
          <div className="flex gap-4 text-sm text-slate-600">
            <span>📏 {history.totalDistanceKm} km</span>
            <span>🟢 Active {history.activeMinutes} min</span>
            <span>⏸ Idle {history.idleMinutes} min</span>
            <span>{history.points.length} points</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-hidden rounded-xl border">
        {history ? (
          <PlaybackMap points={history.points} />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            Pick a worker and a date to replay their route
          </div>
        )}
      </div>
    </div>
  );
}
