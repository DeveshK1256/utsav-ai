'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DashboardIndex() {
  const router = useRouter();

  useEffect(() => {
    // Check if there is a recently saved event in localStorage, otherwise default
    let targetEventId = 'default';
    try {
      const saved = localStorage.getItem('utsav_last_event_id');
      if (saved) targetEventId = saved;
    } catch (e) {
      // ignore
    }
    router.replace(`/dashboard/events/${targetEventId}`);
  }, [router]);

  return (
    <main id="main-content" className="min-h-screen flex items-center justify-center p-6 text-stone-600 dark:text-stone-300">
      <div className="text-center space-y-3">
        <div className="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm font-medium">Loading Celebration Workspace...</p>
      </div>
    </main>
  );
}
