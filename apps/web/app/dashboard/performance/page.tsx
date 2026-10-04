'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface StaffRow {
  userId: string;
  name: string;
  visits: number;
  tasksCompleted: number;
  distanceKm: number;
  activeMinutes: number;
  hoursWorked: number;
}

interface Report {
  date: string;
  staff: StaffRow[];
}

export default function PerformancePage() {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (d: string) => {
    setLoading(true);
    try {
      setReport(await api<Report>(`/reports/performance?date=${d}`));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(date);
  }, [date, load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Team Performance</h1>
        <input
          type="date"
          className="rounded-md border px-3 py-2 text-sm"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </div>

      <div className="overflow-hidden rounded-xl border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-3">Field staff</th>
              <th className="p-3">Site visits</th>
              <th className="p-3">Tasks completed</th>
              <th className="p-3">Distance</th>
              <th className="p-3">Active time</th>
              <th className="p-3">Hours on shift</th>
            </tr>
          </thead>
          <tbody>
            {report?.staff.map((s) => (
              <tr key={s.userId} className="border-t">
                <td className="p-3 font-medium">{s.name}</td>
                <td className="p-3">{s.visits}</td>
                <td className="p-3">{s.tasksCompleted}</td>
                <td className="p-3">{s.distanceKm} km</td>
                <td className="p-3">{s.activeMinutes} min</td>
                <td className="p-3">{s.hoursWorked} h</td>
              </tr>
            ))}
            {!loading && !report?.staff.length && (
              <tr>
                <td className="p-4 text-slate-500" colSpan={6}>
                  No field staff yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {loading && <p className="text-sm text-slate-500">Loading…</p>}
    </div>
  );
}
