'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  CircleMarker,
  ZoomControl,
} from 'react-leaflet';
import L from 'leaflet';
import { api } from '@/lib/api';
import { getSocket } from '@/lib/socket';

interface Live {
  userId: string;
  lat: number;
  lng: number;
  speed?: number;
  batteryLevel?: number;
  recordedAt: string;
}

interface Fence {
  id: string;
  name: string;
  lat: number;
  lng: number;
  radiusM: number;
}

interface StaffUser {
  id: string;
  firstName: string;
  lastName: string;
}

interface TaskPin {
  id: string;
  title: string;
  address: string;
  status: string;
  lat: number;
  lng: number;
  fieldStaff: { firstName: string; lastName: string } | null;
}

const OPEN_TASK_STATUSES = ['UNASSIGNED', 'ASSIGNED', 'EN_ROUTE', 'IN_PROGRESS'];

const DEFAULT_CENTER: [number, number] = [8.5241, 76.9366];

function escapeHtml(s: string): string {
  return s.replace(
    /[&<>"']/g,
    (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!,
  );
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?';
}

/** Deterministic, evenly-spread colour per user so each marker stays consistent. */
function colorFor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  return `hsl(${Math.abs(hash) % 360}, 65%, 45%)`;
}

/** Snap-Map-style marker: an initials bubble with a name pill and a live pulse ring. */
function avatarIcon(name: string, id: string): L.DivIcon {
  const safe = escapeHtml(name);
  return L.divIcon({
    className: 'ft-avatar-icon',
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -24],
    html: `
      <div class="ft-avatar-wrap">
        <div class="ft-avatar-ring"></div>
        <div class="ft-avatar" style="background:${colorFor(id)}">${initials(name)}</div>
        <div class="ft-avatar-name">${safe}</div>
      </div>`,
  });
}

export default function LiveMap() {
  const [locations, setLocations] = useState<Record<string, Live>>({});
  const [fences, setFences] = useState<Fence[]>([]);
  const [names, setNames] = useState<Record<string, string>>({});
  const [staffList, setStaffList] = useState<StaffUser[]>([]);
  const [taskPins, setTaskPins] = useState<TaskPin[]>([]);
  const [query, setQuery] = useState('');
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    api<Live[]>('/locations/live').then((list) =>
      setLocations(Object.fromEntries(list.map((l) => [l.userId, l]))),
    );
    api<Fence[]>('/geofences').then(setFences);
    const loadTasks = () =>
      api<TaskPin[]>('/tasks').then((all) =>
        setTaskPins(all.filter((t) => OPEN_TASK_STATUSES.includes(t.status))),
      );
    loadTasks();
    api<(StaffUser & { role: string })[]>('/users').then((users) => {
      const staff = users.filter((u) => u.role === 'FIELD_STAFF');
      setStaffList(staff);
      setNames(
        Object.fromEntries(users.map((u) => [u.id, `${u.firstName} ${u.lastName}`])),
      );
    });

    const socket = getSocket();
    const onSync = (loc: Live) =>
      setLocations((prev) => ({ ...prev, [loc.userId]: loc }));
    const onTaskUpdate = () => loadTasks();
    socket.on('location_sync', onSync);
    socket.on('task_updated', onTaskUpdate);
    return () => {
      socket.off('location_sync', onSync);
      socket.off('task_updated', onTaskUpdate);
    };
  }, []);

  const live = Object.values(locations);
  const center: [number, number] = live.length
    ? [live[0].lat, live[0].lng]
    : DEFAULT_CENTER;

  /** Pan & zoom the map to a worker's current position (no-op if off duty). */
  function focusStaff(userId: string) {
    const loc = locations[userId];
    if (loc && mapRef.current) {
      mapRef.current.flyTo([loc.lat, loc.lng], 16, { duration: 1 });
      mapRef.current.openPopup(
        `<strong>${names[userId] ?? 'Staff'}</strong>`,
        [loc.lat, loc.lng],
      );
    }
  }

  // Rebuild icons only when a name or id set changes, not on every position tick.
  const icons = useMemo(() => {
    const map: Record<string, L.DivIcon> = {};
    for (const l of live) {
      map[l.userId] = avatarIcon(names[l.userId] ?? 'Staff', l.userId);
    }
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [Object.keys(locations).join(','), names]);

  const filteredStaff = staffList
    .filter((s) =>
      `${s.firstName} ${s.lastName}`.toLowerCase().includes(query.toLowerCase()),
    )
    .sort((a, b) => {
      // Online first, then alphabetical.
      const ao = locations[a.id] ? 0 : 1;
      const bo = locations[b.id] ? 0 : 1;
      return ao - bo || a.firstName.localeCompare(b.firstName);
    });

  return (
    <div className="relative h-full w-full">
      <div className="pointer-events-none absolute right-3 top-3 z-[1000] flex items-center gap-2 rounded-full bg-white/95 px-3 py-1.5 text-sm font-medium shadow">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
        </span>
        {live.length} field staff live
      </div>

      {/* Staff finder: search + jump to a worker's live location. */}
      <div className="absolute left-3 top-3 z-[1000] flex max-h-[85%] w-64 flex-col overflow-hidden rounded-xl bg-white/95 shadow-lg ring-1 ring-black/5">
        <div className="border-b p-3">
          <p className="text-sm font-semibold">Field staff</p>
          <p className="text-xs text-slate-500">
            {live.length} online · {staffList.length} total
          </p>
          <input
            className="mt-2 w-full rounded-md border border-slate-300 px-2.5 py-1.5 text-sm"
            placeholder="🔍 Search staff…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <ul className="overflow-auto p-1">
          {filteredStaff.map((s) => {
            const online = !!locations[s.id];
            return (
              <li key={s.id}>
                <button
                  type="button"
                  disabled={!online}
                  onClick={() => focusStaff(s.id)}
                  className={`flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm ${
                    online ? 'hover:bg-slate-100' : 'cursor-default opacity-50'
                  }`}
                >
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: online ? colorFor(s.id) : '#cbd5e1' }}
                  />
                  <span className="flex-1 truncate">
                    {s.firstName} {s.lastName}
                  </span>
                  <span
                    className={`text-xs ${online ? 'text-green-600' : 'text-slate-400'}`}
                  >
                    {online ? 'Live' : 'Off'}
                  </span>
                </button>
              </li>
            );
          })}
          {filteredStaff.length === 0 && (
            <li className="px-2 py-3 text-center text-xs text-slate-400">
              No staff found
            </li>
          )}
        </ul>
      </div>

      <MapContainer
        center={center}
        zoom={13}
        zoomControl={false}
        className="h-full w-full"
        ref={mapRef}
      >
        <ZoomControl position="bottomright" />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {fences.map((f) => (
          <Circle
            key={f.id}
            center={[f.lat, f.lng]}
            radius={f.radiusM}
            pathOptions={{ color: '#6366f1', fillOpacity: 0.08 }}
          />
        ))}
        {taskPins.map((t) => (
          <CircleMarker
            key={t.id}
            center={[t.lat, t.lng]}
            radius={8}
            pathOptions={{ color: '#b45309', fillColor: '#f59e0b', fillOpacity: 0.85 }}
          >
            <Popup>
              <strong>📋 {t.title}</strong>
              <br />
              {t.address}
              <br />
              {t.status} ·{' '}
              {t.fieldStaff
                ? `${t.fieldStaff.firstName} ${t.fieldStaff.lastName}`
                : 'Unassigned'}
            </Popup>
          </CircleMarker>
        ))}
        {live.map((l) => (
          <Marker
            key={l.userId}
            position={[l.lat, l.lng]}
            icon={icons[l.userId]}
            eventHandlers={{ click: () => focusStaff(l.userId) }}
          >
            <Popup>
              <strong>{names[l.userId] ?? l.userId}</strong>
              <br />
              Speed: {l.speed != null ? `${(l.speed * 3.6).toFixed(1)} km/h` : '—'}
              <br />
              Battery: {l.batteryLevel != null ? `${l.batteryLevel}%` : '—'}
              <br />
              Updated {new Date(l.recordedAt).toLocaleTimeString()}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
