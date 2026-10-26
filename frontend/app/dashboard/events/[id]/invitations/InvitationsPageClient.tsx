'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Navbar } from '@/components/ui/Navbar';
import { InvitationStudio } from '@/components/ui/InvitationStudio';
import { getAuthHeaders } from '@/lib/auth';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.hostname.includes('netlify.app')
    ? '/api/v1'
    : 'https://utsav-ai-ycg2.onrender.com/api/v1');

export default function InvitationsPageClient() {
  const params = useParams();
  const rawEventId = (params?.id as string) || '';

  const [eventId, setEventId] = useState<string>(rawEventId);
  const [eventName, setEventName] = useState<string>('Celebration');
  const [city, setCity] = useState<string>('Mumbai');
  const [startDate, setStartDate] = useState<string>('');

  useEffect(() => {
    // Resolve real event ID from URL path or localStorage
    let resolvedId = rawEventId;
    if (typeof window !== 'undefined') {
      const segments = window.location.pathname.split('/').filter(Boolean);
      const evIdx = segments.indexOf('events');
      if (evIdx !== -1 && segments[evIdx + 1] && segments[evIdx + 1] !== 'default') {
        resolvedId = segments[evIdx + 1];
      } else if (!resolvedId || resolvedId === 'default') {
        const stored = localStorage.getItem('current_event_id') || localStorage.getItem('last_event_id');
        if (stored) resolvedId = stored;
      }
    }

    if (resolvedId && resolvedId !== 'default') {
      setEventId(resolvedId);
      // Fetch basic event details
      fetch(`${API_BASE_URL}/events/${resolvedId}`, {
        headers: getAuthHeaders(resolvedId)
      })
        .then((r) => r.json())
        .then((d) => {
          if (d && d.name) {
            setEventName(d.name);
            setCity(d.city || 'Mumbai');
            setStartDate(d.start_date || '');
          }
        })
        .catch(() => {});
    }
  }, [rawEventId]);

  return (
    <div className="min-h-screen bg-[#FAF8F5] dark:bg-stone-950 text-stone-900 dark:text-stone-100 flex flex-col font-sans transition-colors duration-200">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Breadcrumb Header */}
        <div className="flex items-center justify-between border-b border-stone-200 dark:border-stone-800 pb-4">
          <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400">
            <Link href="/dashboard" className="hover:text-amber-700">Dashboard</Link>
            <span>/</span>
            <Link href={`/dashboard/events/${eventId}`} className="hover:text-amber-700">{eventName}</Link>
            <span>/</span>
            <span className="font-semibold text-stone-800 dark:text-stone-200">Invitation Cards Studio</span>
          </div>

          <Link
            href={`/dashboard/events/${eventId}`}
            className="text-xs font-bold text-amber-800 dark:text-amber-400 hover:underline flex items-center gap-1"
          >
            ← Return to Event Workspace
          </Link>
        </div>

        {/* Invitation Studio Component */}
        <InvitationStudio
          eventId={eventId}
          eventName={eventName}
          city={city}
          startDate={startDate}
          apiBase={API_BASE_URL.replace(/\/api\/v1\/?$/, '')}
        />
      </main>
    </div>
  );
}
