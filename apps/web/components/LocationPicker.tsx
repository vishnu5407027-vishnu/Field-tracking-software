'use client';

import { useEffect, useRef, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Circle,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import L from 'leaflet';

// Leaflet's default marker icons break under bundlers; point at CDN assets.
const markerIcon = new L.Icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const DEFAULT_CENTER: [number, number] = [8.5241, 76.9366];

export interface PickedLocation {
  lat: number;
  lng: number;
}

interface PlaceResult {
  label: string;
  lat: number;
  lng: number;
}

/** Build a readable "Name, City, State, Country" label from Photon props. */
function photonLabel(p: Record<string, string>): string {
  const main = p.name || [p.housenumber, p.street].filter(Boolean).join(' ');
  const parts: string[] = [];
  for (const part of [main, p.city || p.county, p.state, p.country]) {
    if (part && !parts.includes(part)) parts.push(part);
  }
  return parts.join(', ');
}

function ClickToPlace({ onPick }: { onPick: (pos: PickedLocation) => void }) {
  useMapEvents({
    click: (e) => onPick({ lat: e.latlng.lat, lng: e.latlng.lng }),
  });
  return null;
}

/**
 * Google-Maps-style worldwide place search. Debounced autocomplete against
 * Photon (komoot's OSM geocoder, no API key); picking a result recenters the
 * map, drops the pin, and — when provided — reports the label for the address.
 */
function PlaceSearch({
  onPick,
  onResolveAddress,
}: {
  onPick: (pos: PickedLocation) => void;
  onResolveAddress?: (label: string) => void;
}) {
  const map = useMap();
  const boxRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PlaceResult[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  // Typing/clicking inside the box must not pan the map or drop a pin.
  useEffect(() => {
    if (boxRef.current) {
      L.DomEvent.disableClickPropagation(boxRef.current);
      L.DomEvent.disableScrollPropagation(boxRef.current);
    }
  }, []);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setBusy(true);
      try {
        const res = await fetch(
          'https://photon.komoot.io/api/?limit=8&q=' + encodeURIComponent(q),
          { signal: controller.signal },
        );
        const data = await res.json();
        const parsed: PlaceResult[] = (data.features ?? [])
          .map((f: { geometry: { coordinates: [number, number] }; properties: Record<string, string> }) => ({
            label: photonLabel(f.properties),
            lat: f.geometry.coordinates[1],
            lng: f.geometry.coordinates[0],
          }))
          .filter((r: PlaceResult) => r.label);
        setResults(parsed);
        setOpen(true);
      } catch {
        // Aborted (next keystroke) or offline — ignore.
      } finally {
        setBusy(false);
      }
    }, 350);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [query]);

  function choose(r: PlaceResult) {
    map.setView([r.lat, r.lng], 16);
    onPick({ lat: r.lat, lng: r.lng });
    onResolveAddress?.(r.label);
    setQuery(r.label);
    setResults([]);
    setOpen(false);
  }

  return (
    <div className="leaflet-top leaflet-right">
      <div ref={boxRef} className="leaflet-control" style={{ width: 280 }}>
        <input
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow"
          placeholder="🔍 Search a place…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
        />
        {open && results.length > 0 && (
          <ul className="mt-1 max-h-48 overflow-auto rounded-md border border-slate-200 bg-white text-sm shadow-lg">
            {results.map((r, i) => (
              <li key={i}>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left hover:bg-slate-100"
                  onClick={() => choose(r)}
                >
                  {r.label}
                </button>
              </li>
            ))}
          </ul>
        )}
        {busy && <p className="mt-1 text-xs text-slate-500">Searching…</p>}
      </div>
    </div>
  );
}

/**
 * Click the map to drop a pin (drag to fine-tune) or search for a place.
 * Passing `radiusM` draws a live circle preview around the pin — used when
 * defining geofences.
 */
export default function LocationPicker({
  value,
  onPick,
  onResolveAddress,
  radiusM,
}: {
  value: PickedLocation | null;
  onPick: (pos: PickedLocation) => void;
  onResolveAddress?: (label: string) => void;
  radiusM?: number;
}) {
  const center: [number, number] = value ? [value.lat, value.lng] : DEFAULT_CENTER;

  return (
    <MapContainer center={center} zoom={13} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <PlaceSearch onPick={onPick} onResolveAddress={onResolveAddress} />
      <ClickToPlace onPick={onPick} />
      {value && (
        <Marker
          position={[value.lat, value.lng]}
          icon={markerIcon}
          draggable
          eventHandlers={{
            dragend: (e) => {
              const pos = (e.target as L.Marker).getLatLng();
              onPick({ lat: pos.lat, lng: pos.lng });
            },
          }}
        />
      )}
      {value && radiusM != null && radiusM > 0 && (
        <Circle
          center={[value.lat, value.lng]}
          radius={radiusM}
          pathOptions={{ color: '#6366f1', fillOpacity: 0.08 }}
        />
      )}
    </MapContainer>
  );
}
