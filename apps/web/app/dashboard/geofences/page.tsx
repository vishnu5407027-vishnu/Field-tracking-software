'use client';

import dynamic from 'next/dynamic';
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { getSocket } from '@/lib/socket';

// Leaflet touches `window`, so the picker must render client-side only.
const LocationPicker = dynamic(() => import('@/components/LocationPicker'), {
  ssr: false,
});

interface Fence {
  id: string;
  name: string;
  lat: number;
  lng: number;
  radiusM: number;
}

interface FenceEvent {
  id: string;
  type: 'ENTER' | 'EXIT';
  occurredAt: string;
  geofence: { name: string };
  user: { firstName: string; lastName: string };
}

export default function GeofencesPage() {
  const [fences, setFences] = useState<Fence[]>([]);
  const [events, setEvents] = useState<FenceEvent[]>([]);
  const [form, setForm] = useState({ name: '', lat: '', lng: '', radiusM: '200' });

  const refresh = useCallback(async () => {
    const [f, e] = await Promise.all([
      api<Fence[]>('/geofences'),
      api<FenceEvent[]>('/geofences/events'),
    ]);
    setFences(f);
    setEvents(e);
  }, []);

  useEffect(() => {
    refresh();
    const socket = getSocket();
    const onEvent = () => refresh();
    socket.on('geofence_event', onEvent);
    return () => {
      socket.off('geofence_event', onEvent);
    };
  }, [refresh]);

  async function create(e: FormEvent) {
    e.preventDefault();
    await api('/geofences', {
      method: 'POST',
      body: JSON.stringify({
        name: form.name,
        lat: Number(form.lat),
        lng: Number(form.lng),
        radiusM: Number(form.radiusM),
      }),
    });
    setForm({ name: '', lat: '', lng: '', radiusM: '200' });
    await refresh();
  }

  const input = 'rounded-md border px-3 py-2 text-sm';

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Geofences</h1>

      <form onSubmit={create} className="space-y-3 rounded-xl border bg-white p-4">
        <div className="flex flex-wrap gap-3">
          <input className={input} placeholder="Site name" required
            value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className={input} placeholder="Latitude" type="number" step="any" required
            value={form.lat} onChange={(e) => setForm({ ...form, lat: e.target.value })} />
          <input className={input} placeholder="Longitude" type="number" step="any" required
            value={form.lng} onChange={(e) => setForm({ ...form, lng: e.target.value })} />
          <input className={input} placeholder="Radius (m)" type="number" min={10} required
            value={form.radiusM} onChange={(e) => setForm({ ...form, radiusM: e.target.value })} />
          <button className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">Add geofence</button>
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
            radiusM={Number(form.radiusM) || 0}
          />
        </div>
        <p className="text-xs text-slate-500">
          Search a place or click the map to mark the site center — the circle previews the geofence boundary.
        </p>
      </form>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="overflow-hidden rounded-xl border bg-white">
          <h2 className="border-b bg-slate-100 p-3 text-sm font-medium">Defined sites</h2>
          <ul className="divide-y text-sm">
            {fences.map((f) => (
              <li key={f.id} className="flex items-center justify-between p-3">
                <div>
                  <p className="font-medium">{f.name}</p>
                  <p className="text-xs text-slate-500">
                    {f.lat.toFixed(5)}, {f.lng.toFixed(5)} · {f.radiusM} m
                  </p>
                </div>
                <button
                  className="text-xs text-red-600 underline"
                  onClick={async () => {
                    await api(`/geofences/${f.id}`, { method: 'DELETE' });
                    await refresh();
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
            {!fences.length && <li className="p-3 text-slate-500">No geofences yet</li>}
          </ul>
        </section>

        <section className="overflow-hidden rounded-xl border bg-white">
          <h2 className="border-b bg-slate-100 p-3 text-sm font-medium">
            Check-in / check-out log
          </h2>
          <ul className="divide-y text-sm">
            {events.map((e) => (
              <li key={e.id} className="flex items-center justify-between p-3">
                <span>
                  <strong>{e.user.firstName} {e.user.lastName}</strong>{' '}
                  {e.type === 'ENTER' ? 'checked in at' : 'checked out of'}{' '}
                  {e.geofence.name}
                </span>
                <span className="text-xs text-slate-500">
                  {new Date(e.occurredAt).toLocaleString()}
                </span>
              </li>
            ))}
            {!events.length && <li className="p-3 text-slate-500">No events yet</li>}
          </ul>
        </section>
      </div>
    </div>
  );
}
