'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { clearSession, getUser, SessionUser } from '@/lib/api';
import { disconnectSocket } from '@/lib/socket';

const NAV = [
  { href: '/dashboard', label: 'Live Map' },
  { href: '/dashboard/playback', label: 'Route Playback' },
  { href: '/dashboard/tasks', label: 'Tasks' },
  { href: '/dashboard/geofences', label: 'Geofences' },
  { href: '/dashboard/performance', label: 'Performance' },
  { href: '/dashboard/staff', label: 'Team' },
  { href: '/profile', label: 'Profile' },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);

  useEffect(() => {
    const u = getUser();
    if (!u || u.role === 'FIELD_STAFF') router.replace('/login');
    else setUser(u);
  }, [router]);

  if (!user) return null;

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 flex-col border-r bg-white p-4">
        <div className="mb-6">
          <p className="font-semibold">FieldTracking</p>
          <p className="text-xs text-slate-500">{user.tenantName}</p>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-3 py-2 text-sm ${
                pathname === item.href
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <button
          className="mt-4 text-left text-sm text-slate-500 underline"
          onClick={() => {
            disconnectSocket();
            clearSession();
            router.replace('/login');
          }}
        >
          Sign out ({user.firstName})
        </button>
      </aside>
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
