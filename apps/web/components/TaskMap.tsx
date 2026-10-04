'use client';

import { useEffect, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
} from 'react-leaflet';
import L from 'leaflet';

const destIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

export interface LatLng {
  lat: number;
  lng: number;
}

interface Props {
  destination: LatLng;
  /** Field staff's current position (active tasks only). */
  live?: LatLng | null;
  /** Travelled route so far / full history (completed). */
  travelled?: LatLng[];
  completed?: boolean;
  staffName?: string;
}

/** Tries OSRM for a real road route; falls back to a straight line. */
function useRoute(from: LatLng | null | undefined, to: LatLng) {
  const [line, setLine] = useState<[number, number][]>([]);
  const [info, setInfo] = useState<{ km: number; min: number } | null>(null);

  useEffect(() => {
    if (!from) {
      setLine([]);
      setInfo(null);
      return;
    }
    let cancelled = false;
    const straight: [number, number][] = [
      [from.lat, from.lng],
      [to.lat, to.lng],
    ];
    fetch(
      `https://router.project-osrm.org/route/v1/driving/${from.lng},${from.lat};${to.lng},${to.lat}?overview=full&geometries=geojson`,
    )
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        const route = data?.routes?.[0];
        if (!route) {
          setLine(straight);
          return;
        }
        setLine(
          route.geometry.coordinates.map(
            (c: [number, number]) => [c[1], c[0]] as [number, number],
          ),
        );
        setInfo({ km: route.distance / 1000, min: route.duration / 60 });
      })
      .catch(() => !cancelled && setLine(straight));
    return () => {
      cancelled = true;
    };
  }, [from?.lat, from?.lng, to.lat, to.lng]);

  return { line, info };
}

export default function TaskMap({
  destination,
  live,
  travelled = [],
  completed = false,
  staffName,
}: Props) {
  const { line: routeLine, info } = useRoute(completed ? null : live, destination);

  const path = travelled.map((p) => [p.lat, p.lng] as [number, number]);
  const center: [number, number] = live
    ? [live.lat, live.lng]
    : [destination.lat, destination.lng];

  return (
    <div className="relative h-full w-full">
      {info && !completed && (
        <div className="pointer-events-none absolute left-1/2 top-3 z-[1000] -translate-x-1/2 rounded-full bg-white/95 px-3 py-1.5 text-sm font-medium shadow">
          🚗 {info.km.toFixed(1)} km · ~{Math.round(info.min)} min to destination
        </div>
      )}
      <MapContainer center={center} zoom={14} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Destination */}
        <Marker position={[destination.lat, destination.lng]} icon={destIcon}>
          <Popup>📍 Task destination</Popup>
        </Marker>

        {/* Travelled route (history / trail so far) */}
        {path.length > 1 && (
          <Polyline positions={path} pathOptions={{ color: '#0f172a', weight: 3 }} />
        )}
        {path.length > 0 && (
          <CircleMarker
            center={path[0]}
            radius={6}
            pathOptions={{ color: '#16a34a', fillColor: '#16a34a', fillOpacity: 1 }}
          >
            <Popup>Start</Popup>
          </CircleMarker>
        )}

        {/* Planned route to destination (active task) */}
        {!completed && routeLine.length > 1 && (
          <Polyline
            positions={routeLine}
            pathOptions={{ color: '#4f46e5', weight: 4, opacity: 0.7, dashArray: '6 8' }}
          />
        )}

        {/* Field staff live position */}
        {!completed && live && (
          <CircleMarker
            center={[live.lat, live.lng]}
            radius={9}
            pathOptions={{ color: '#fff', weight: 2, fillColor: '#4f46e5', fillOpacity: 1 }}
          >
            <Popup>{staffName ? `${staffName} (live)` : 'Field staff (live)'}</Popup>
          </CircleMarker>
        )}
      </MapContainer>
    </div>
  );
}
