'use client';

import { MapContainer, TileLayer, Polyline, CircleMarker } from 'react-leaflet';

interface Point {
  lat: number;
  lng: number;
  recordedAt: string;
}

export default function PlaybackMap({ points }: { points: Point[] }) {
  if (!points.length) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        No location data for this selection
      </div>
    );
  }

  const path = points.map((p) => [p.lat, p.lng] as [number, number]);
  const start = path[0];
  const end = path[path.length - 1];

  return (
    <MapContainer center={start} zoom={14} className="h-full w-full rounded-xl">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Polyline positions={path} pathOptions={{ color: '#0f172a', weight: 3 }} />
      <CircleMarker center={start} radius={7} pathOptions={{ color: '#16a34a' }} />
      <CircleMarker center={end} radius={7} pathOptions={{ color: '#dc2626' }} />
    </MapContainer>
  );
}
