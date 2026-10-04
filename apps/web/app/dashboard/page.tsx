'use client';

import dynamic from 'next/dynamic';

// Leaflet touches `window`, so the map must render client-side only.
const LiveMap = dynamic(() => import('@/components/LiveMap'), { ssr: false });

export default function LiveMapPage() {
  return (
    <div className="flex h-[calc(100vh-3rem)] flex-col gap-4">
      <h1 className="text-xl font-semibold">Live Map</h1>
      <div className="flex-1 overflow-hidden rounded-xl border">
        <LiveMap />
      </div>
    </div>
  );
}
