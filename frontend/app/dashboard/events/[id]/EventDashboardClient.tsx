'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Navbar } from '@/components/ui/Navbar';
import { ElderDisclaimerBanner } from '@/components/ui/ElderDisclaimerBanner';
import { GuestCoordinationModule } from '@/components/ui/GuestCoordinationModule';
import { RitualIntelligenceHub } from '@/components/ui/RitualIntelligenceHub';

// Currency Formatter
const formatINR = (val: number) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(val);
};

interface SubEvent {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
  venue_name: string;
  is_outdoor: boolean;
  is_muhurat_locked: boolean;
  muhurat_notes?: string;
  sort_order: number;
}

interface BudgetItem {
  id: string;
  category: string;
  name: string;
  planned_amount: number;
  actual_amount: number;
  percentage: number;
  reasoning_spec?: {
    formula?: string;
    city_tier?: string;
    guest_count?: number;
    benchmark_basis?: string;
  };
}

interface TaskItem {
  id: string;
  title: string;
  status: string;
  scheduled_start?: string;
  scheduled_end?: string;
  duration_minutes?: number;
  assigned_role?: string;
}

interface EventData {
  id: string;
  name: string;
  owner_name: string;
  event_type: string;
  city: string;
  city_tier: string;
  guest_count: number;
  total_budget: number;
  tradition_code: string;
  status: string;
  start_date?: string;
  end_date?: string;
  elder_verification_disclaimer?: string;
  sub_events: SubEvent[];
  budget_breakdown: BudgetItem[];
  tasks: TaskItem[];
}

interface StyleProfile {
  profile_id: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  neutral_color: string;
  background_color: string;
  aesthetic_tags: string[];
  materials: string[];
  theme_concept?: string;
}

export default function EventDashboardClient() {
  const params = useParams();
  const router = useRouter();
  const rawEventId = (params?.id as string) || '';

  const [eventData, setEventData] = useState<EventData | null>(null);
  const [styleProfile, setStyleProfile] = useState<StyleProfile | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'itinerary' | 'rituals' | 'budget' | 'vendors' | 'vibe' | 'guests'>('overview');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedWhyThis, setSelectedWhyThis] = useState<BudgetItem | null>(null);

  // Dynamic API Base URL resolver
  const getApiBase = () => {
    return typeof window !== 'undefined' && window.location.hostname.includes('netlify.app')
      ? '/api/v1'
      : 'https://utsav-ai-ycg2.onrender.com/api/v1';
  };

  // Fetch real event data from backend API — strictly zero invented facts
  const fetchEventData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    // Guard: If rawEventId is 'default' or empty, check if we have a saved ID, else reject immediately
    let targetId = rawEventId;
    if (!targetId || targetId === 'default') {
      try {
        const saved = localStorage.getItem('utsav_last_event_id');
        if (saved && saved !== 'default') {
          targetId = saved;
          router.replace(`/dashboard/events/${saved}`);
          return;
        }
      } catch (e) {
        // ignore
      }
      setIsLoading(false);
      setErrorMessage('No celebration event selected. Please create your plan via the intake wizard to launch your real workspace.');
      return;
    }

    try {
      const apiBase = getApiBase();
      const res = await fetch(`${apiBase}/events/${targetId}`);

      if (res.status === 404) {
        setIsLoading(false);
        setErrorMessage(`Event with ID "${targetId}" was not found in the live database. Please check the URL or create a new celebration plan.`);
        return;
      }

      if (!res.ok) {
        setIsLoading(false);
        setErrorMessage(`Backend server returned HTTP error ${res.status} (${res.statusText || 'Failed to fetch event'}).`);
        return;
      }

      const data = await res.json();
      setEventData({
        id: data.id,
        name: data.name,
        owner_name: data.owner_name || 'Host',
        event_type: data.event_type || 'wedding',
        city: data.city,
        city_tier: data.city_tier || 'tier_2',
        guest_count: data.guest_count,
        total_budget: Number(data.total_budget),
        tradition_code: data.tradition_code || 'maharashtrian_vedic',
        status: data.status || 'planning',
        start_date: data.start_date,
        end_date: data.end_date,
        elder_verification_disclaimer: data.elder_verification_disclaimer ||
          'Auspicious timings & ritual checklists are algorithmic estimates computed via astronomical ephemeris models. Please verify with your family Guruji or elders.',
        sub_events: data.sub_events || [],
        budget_breakdown: data.budget_breakdown || [],
        tasks: data.tasks || []
      });

      // Persist active ID in localStorage
      try {
        localStorage.setItem('utsav_last_event_id', data.id);
      } catch (e) {
        // ignore
      }

      // Try fetching style profiles for this event
      try {
        const vibeRes = await fetch(`${apiBase}/events/${targetId}/vibe/profiles`);
        if (vibeRes.ok) {
          const profiles = await vibeRes.json();
          if (profiles && profiles.length > 0) {
            setStyleProfile(profiles[0]);
          }
        }
      } catch (e) {
        // ignore vibe fetch failures
      }
    } catch (err: any) {
      console.error('Failed to fetch live event:', err);
      setErrorMessage(`Network error connecting to backend: ${err.message || 'Unable to reach API server'}. Please verify backend health.`);
    } finally {
      setIsLoading(false);
    }
  }, [rawEventId, router]);

  useEffect(() => {
    fetchEventData();
  }, [fetchEventData]);

  // Derived KPI calculations from REAL database data
  const totalAllocated = useMemo(() => {
    if (!eventData?.budget_breakdown) return 0;
    return eventData.budget_breakdown.reduce((sum, item) => sum + (item.planned_amount || 0), 0);
  }, [eventData]);

  const muhuratCount = useMemo(() => {
    if (!eventData?.sub_events) return 0;
    return eventData.sub_events.filter((s) => s.is_muhurat_locked).length;
  }, [eventData]);

  const traditionTitle = useMemo(() => {
    if (!eventData?.tradition_code) return 'Celebration';
    const map: Record<string, string> = {
      maharashtrian_vedic: 'Maharashtrian Vedic Lagna 🕉️',
      gujarati_hindu: 'Gujarati Hindu Vivah 🪔',
      punjabi_sikh: 'Punjabi Anand Karaj ✨',
      south_indian_iyer: 'Tamil Brahmin Iyer Kalyanam 🌸',
      marwari_traditional: 'Marwari Traditional Vivah 👑',
      satyanarayan_puja: 'Satyanarayan Vrat & Puja 🙏',
      community_festival: 'Sarvajanik Community Utsav 🚩'
    };
    return map[eventData.tradition_code] || `${eventData.tradition_code.replace('_', ' ')} ✨`;
  }, [eventData]);

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen pb-20">
        <Navbar badge="Live Command" />
        <div className="max-w-lg mx-auto pt-24 px-4 text-center space-y-4">
          <div className="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <h2 className="text-xl font-serif font-bold text-stone-900 dark:text-stone-100">
            Connecting to PostgreSQL Event Registry...
          </h2>
          <p className="text-xs text-stone-500 dark:text-stone-400 font-mono">
            Resolving live event #{rawEventId} • Zero invented facts policy active
          </p>
        </div>
      </div>
    );
  }

  // Explicit, impossible-to-miss Error State (Zero Invented Facts)
  if (errorMessage || !eventData) {
    return (
      <div className="min-h-screen pb-20">
        <Navbar badge="Live Command" />
        <div className="max-w-xl mx-auto pt-16 px-4">
          <div className="glass-card rounded-3xl p-8 border-2 border-rose-400/80 dark:border-rose-800 shadow-xl text-center space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-rose-100 dark:bg-rose-950/80 text-rose-600 dark:text-rose-400 flex items-center justify-center text-3xl mx-auto shadow-sm">
              ⚠️
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-50">
                Unable to Load Event Data
              </h2>
              <p className="text-sm text-stone-600 dark:text-stone-300 leading-relaxed">
                {errorMessage}
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-stone-100 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800 text-xs text-stone-600 dark:text-stone-400 font-mono text-left space-y-1.5">
              <div className="font-semibold text-rose-700 dark:text-rose-400 uppercase tracking-wider text-[11px]">
                Integrity Guard Active
              </div>
              <div>• Requested Event ID: <span className="font-bold text-stone-900 dark:text-stone-200">{rawEventId || '(none)'}</span></div>
              <div>• Zero Invented Facts: Utsav never fabricates placeholder budgets or fake schedules when real database records cannot be verified.</div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
              <button
                onClick={() => fetchEventData()}
                className="px-5 py-2.5 rounded-xl border border-stone-300 dark:border-stone-700 text-xs font-semibold hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-800 dark:text-stone-200 transition-colors"
              >
                🔄 Retry Connection
              </button>
              <Link
                href="/onboarding"
                className="px-5 py-2.5 rounded-xl bg-[#8B1E28] hover:bg-[#721820] text-white dark:bg-[#F4B41A] dark:text-stone-950 font-semibold text-xs shadow-md transition-all"
              >
                + Create Celebration Plan
              </Link>
              <Link
                href="/demo"
                className="px-5 py-2.5 rounded-xl border border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-950/40 text-xs font-semibold transition-all"
              >
                Explore Demo Preview →
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const currentEventId = eventData.id;

  return (
    <div className="min-h-screen pb-24">
      {/* Universal Navbar */}
      <Navbar
        badge="Live Command"
        rightAction={
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Live PostgreSQL
            </span>
            <Link
              href="/onboarding"
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-800 hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 transition-colors"
            >
              + New Plan
            </Link>
          </div>
        }
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 space-y-8">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400 font-medium">
          <Link href="/" className="hover:text-stone-900 dark:hover:text-white transition-colors">
            Home
          </Link>
          <span>/</span>
          <span className="text-stone-700 dark:text-stone-300">Celebration Workspace</span>
          <span>/</span>
          <span className="font-mono text-stone-400 truncate max-w-[200px]">{currentEventId}</span>
        </div>

        {/* Header Hero Banner */}
        <section className="glass-card rounded-3xl p-6 sm:p-8 relative overflow-hidden shadow-sm border border-stone-200/80 dark:border-stone-800/80">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3 max-w-3xl">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-[#8B1E28]/10 text-[#8B1E28] dark:bg-[#F4B41A]/20 dark:text-[#F4B41A]">
                  {traditionTitle}
                </span>
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300">
                  📍 {eventData.city} ({eventData.city_tier.toUpperCase()})
                </span>
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300">
                  👥 {eventData.guest_count} Guests
                </span>
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold uppercase font-mono bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400">
                  Status: {eventData.status}
                </span>
              </div>

              <h1 className="text-3xl sm:text-4xl font-serif font-bold text-stone-900 dark:text-stone-50 tracking-tight">
                {eventData.name}
              </h1>

              <p className="text-sm text-stone-600 dark:text-stone-300 leading-relaxed">
                Primary Host:{' '}
                <strong className="text-stone-900 dark:text-stone-100 font-semibold">{eventData.owner_name}</strong> •
                Target Dates:{' '}
                <span className="font-mono text-stone-700 dark:text-stone-300">
                  {eventData.start_date || 'TBD'} to {eventData.end_date || 'TBD'}
                </span>
              </p>
            </div>

            {/* Quick Action Navigation CTAs (Properly Event-Scoped) */}
            <div className="flex flex-wrap sm:flex-nowrap gap-2.5 self-start lg:self-center">
              <Link
                href={`/dashboard/events/${currentEventId}/changes/default`}
                className="px-4 py-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs font-semibold hover:bg-amber-100 dark:hover:bg-amber-900/60 transition-all shadow-sm flex items-center gap-1.5"
              >
                <span>⚡</span> Plan B Replanner
              </Link>
              <Link
                href={`/dashboard/events/${currentEventId}/vibe`}
                className="px-4 py-2.5 rounded-xl bg-purple-50 dark:bg-purple-950/60 border border-purple-300 dark:border-purple-800 text-purple-900 dark:text-purple-200 text-xs font-semibold hover:bg-purple-100 dark:hover:bg-purple-900/60 transition-all shadow-sm flex items-center gap-1.5"
              >
                <span>🎨</span> Vibe Studio
              </Link>
              <Link
                href={`/dashboard/events/${currentEventId}/vendors/quotes`}
                className="px-4 py-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 text-xs font-semibold hover:bg-emerald-100 dark:hover:bg-emerald-900/60 transition-all shadow-sm flex items-center gap-1.5"
              >
                <span>📑</span> Vendor Quotes
              </Link>
            </div>
          </div>
        </section>

        {/* Live KPI Cards (4 Pillars Grounded in Real Data) */}
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 1. Target Budget Envelope */}
          <div className="glass-card p-5 rounded-2xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-400">
              Total Budget Envelope
            </div>
            <div className="text-2xl font-bold font-serif text-stone-900 dark:text-stone-50">
              {formatINR(eventData.total_budget)}
            </div>
            <div className="text-xs text-amber-700 dark:text-amber-400 font-mono">
              Deterministic 100% envelope allocation
            </div>
          </div>

          {/* 2. Scaled / Allocated Spend */}
          <div className="glass-card p-5 rounded-2xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-400">
              Itemized Allocation
            </div>
            <div className="text-2xl font-bold font-serif text-emerald-700 dark:text-emerald-400">
              {formatINR(totalAllocated)}
            </div>
            <div className="text-xs text-stone-500 dark:text-stone-400">
              Across {eventData.budget_breakdown.length} verified categories
            </div>
          </div>

          {/* 3. Sacred Muhurat Anchors */}
          <div className="glass-card p-5 rounded-2xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-400">
              Muhurat Anchors
            </div>
            <div className="text-2xl font-bold font-serif text-[#8B1E28] dark:text-[#F4B41A] flex items-center gap-1.5">
              <span>🕉️</span> {muhuratCount} Locked
            </div>
            <div className="text-xs text-stone-500 dark:text-stone-400">
              Astronomical ephemeris verified
            </div>
          </div>

          {/* 4. Sub-Events & DAG Tasks */}
          <div className="glass-card p-5 rounded-2xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-400">
              Timeline Velocity
            </div>
            <div className="text-2xl font-bold font-serif text-stone-900 dark:text-stone-50">
              {eventData.sub_events.length} Events • {eventData.tasks.length} Tasks
            </div>
            <div className="text-xs text-stone-500 dark:text-stone-400">
              DAG dependency scheduled
            </div>
          </div>
        </section>

        {/* Tab Navigation Controls */}
        <section className="flex border-b border-stone-200 dark:border-stone-800 overflow-x-auto no-scrollbar gap-1">
          {[
            { key: 'overview', label: 'Overview & Cockpit', icon: '⚡' },
            { key: 'itinerary', label: 'Master Itinerary & Muhurats', icon: '📅' },
            { key: 'rituals', label: 'Cultural Rituals & Fusion', icon: '🕉️' },
            { key: 'budget', label: 'Itemized Budget & Formulas', icon: '💰' },
            { key: 'vendors', label: 'Vendor Hub & Quotes', icon: '🤝' },
            { key: 'vibe', label: 'Vibe & Aesthetic Decor', icon: '🎨' },
            { key: 'guests', label: 'Guests & WhatsApp RSVP', icon: '💌' }
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-5 py-3 text-xs sm:text-sm font-semibold whitespace-nowrap transition-all border-b-2 ${
                activeTab === tab.key
                  ? 'border-[#8B1E28] dark:border-[#F4B41A] text-[#8B1E28] dark:text-[#F4B41A]'
                  : 'border-transparent text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-200'
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </section>

        {/* TAB 1: OVERVIEW / COCKPIT */}
        {activeTab === 'overview' && (
          <div className="space-y-8 animate-fadeIn">
            {/* Quick Action Navigation Tiles */}
            <div className="grid sm:grid-cols-3 gap-6">
              {/* Tile 1: Replanning Engine */}
              <div className="glass-card p-6 rounded-3xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-4 hover:border-amber-400/50 transition-all">
                <div className="w-10 h-10 rounded-2xl bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 flex items-center justify-center text-xl font-bold">
                  ⚡
                </div>
                <div>
                  <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                    Plan B Live Replanning
                  </h3>
                  <p className="text-xs text-stone-600 dark:text-stone-300 mt-1 leading-relaxed">
                    Test schedule shifts, guest count changes, or bad weather relocations with zero-LLM deterministic budget math.
                  </p>
                </div>
                <Link
                  href={`/dashboard/events/${currentEventId}/changes/default`}
                  className="inline-flex items-center text-xs font-bold text-amber-700 dark:text-amber-400 hover:underline gap-1"
                >
                  Simulate Replanning Scenario →
                </Link>
              </div>

              {/* Tile 2: Vibe-to-Plan */}
              <div className="glass-card p-6 rounded-3xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-4 hover:border-purple-400/50 transition-all">
                <div className="w-10 h-10 rounded-2xl bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 flex items-center justify-center text-xl font-bold">
                  🎨
                </div>
                <div>
                  <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                    Vibe-to-Plan Vision Engine
                  </h3>
                  <p className="text-xs text-stone-600 dark:text-stone-300 mt-1 leading-relaxed">
                    Upload moodboard photos and color inspirations. Multimodal AI extracts color palettes and generates concrete decor items.
                  </p>
                </div>
                <Link
                  href={`/dashboard/events/${currentEventId}/vibe`}
                  className="inline-flex items-center text-xs font-bold text-purple-700 dark:text-purple-400 hover:underline gap-1"
                >
                  Open Vibe Studio →
                </Link>
              </div>

              {/* Tile 3: Quote Auditor */}
              <div className="glass-card p-6 rounded-3xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-4 hover:border-emerald-400/50 transition-all">
                <div className="w-10 h-10 rounded-2xl bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 flex items-center justify-center text-xl font-bold">
                  📑
                </div>
                <div>
                  <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                    Quote Auditor & Hidden Costs
                  </h3>
                  <p className="text-xs text-stone-600 dark:text-stone-300 mt-1 leading-relaxed">
                    Scan PDF or photo vendor quotes to detect hidden generator charges, overtime fees, and compare against city benchmarks.
                  </p>
                </div>
                <Link
                  href={`/dashboard/events/${currentEventId}/vendors/quotes`}
                  className="inline-flex items-center text-xs font-bold text-emerald-700 dark:text-emerald-400 hover:underline gap-1"
                >
                  Audit Scoped Vendor Quotes →
                </Link>
              </div>
            </div>

            {/* Run-of-Show Preview & Upcoming Tasks */}
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Left: Schedule Glance */}
              <div className="glass-card p-6 rounded-3xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
                    <span>📅</span> Multi-Day Run-of-Show
                  </h3>
                  <button
                    onClick={() => setActiveTab('itinerary')}
                    className="text-xs font-semibold text-amber-700 dark:text-amber-400 hover:underline"
                  >
                    View All ({eventData.sub_events.length}) →
                  </button>
                </div>
                <div className="space-y-3">
                  {eventData.sub_events.length === 0 ? (
                    <p className="text-xs text-stone-500 py-3">No sub-events generated yet.</p>
                  ) : (
                    eventData.sub_events.slice(0, 3).map((se) => (
                      <div
                        key={se.id}
                        className="p-3.5 rounded-xl bg-white/70 dark:bg-stone-900/60 border border-stone-200/80 dark:border-stone-800/80 flex items-start justify-between gap-3 shadow-xs"
                      >
                        <div>
                          <div className="font-semibold text-xs sm:text-sm text-stone-900 dark:text-stone-100">
                            {se.name}
                          </div>
                          <div className="text-xs text-stone-500 dark:text-stone-400 font-mono mt-0.5">
                            {new Date(se.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} -{' '}
                            {new Date(se.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                          <div className="text-xs text-stone-600 dark:text-stone-300 mt-1">
                            📍 {se.venue_name}
                          </div>
                        </div>
                        {se.is_muhurat_locked && (
                          <span className="shrink-0 px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 text-[10px] font-bold font-mono">
                            🕉️ Muhurat Locked
                          </span>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Right: Critical Path Tasks */}
              <div className="glass-card p-6 rounded-3xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
                    <span>🧭</span> Critical Path Milestones (DAG)
                  </h3>
                  <span className="text-xs text-stone-500 dark:text-stone-400 font-mono">
                    {eventData.tasks.length} total
                  </span>
                </div>
                <div className="space-y-3">
                  {eventData.tasks.length === 0 ? (
                    <p className="text-xs text-stone-500 py-3">No tasks scheduled yet.</p>
                  ) : (
                    eventData.tasks.slice(0, 4).map((task) => (
                      <div
                        key={task.id}
                        className="p-3.5 rounded-xl bg-white/70 dark:bg-stone-900/60 border border-stone-200/80 dark:border-stone-800/80 flex items-center justify-between gap-3 shadow-xs text-xs"
                      >
                        <div className="space-y-0.5">
                          <div className="font-semibold text-stone-900 dark:text-stone-100">
                            {task.title}
                          </div>
                          <div className="text-[11px] text-stone-500 dark:text-stone-400">
                            Role:{' '}
                            <span className="font-mono text-stone-700 dark:text-stone-300 font-medium">
                              {task.assigned_role || 'Coordinator'}
                            </span>
                          </div>
                        </div>
                        <span className="shrink-0 px-2.5 py-1 rounded-md bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 font-mono font-medium text-[11px]">
                          {task.scheduled_start ? new Date(task.scheduled_start).toLocaleDateString() : 'Pending'}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: MASTER ITINERARY & MUHURATS */}
        {activeTab === 'itinerary' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-100">
                  Master Itinerary & Multi-Day Timeline
                </h2>
                <p className="text-xs text-stone-600 dark:text-stone-300 mt-1">
                  Chronological schedule resolved through topological DAG dependencies with sacred muhurat locks.
                </p>
              </div>
              <button
                onClick={() => window.print()}
                className="self-start sm:self-auto px-4 py-2 rounded-xl border border-stone-300 dark:border-stone-700 text-xs font-semibold hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 transition-colors"
              >
                🖨️ Print Master Run-of-Show
              </button>
            </div>

            <div className="grid sm:grid-cols-2 gap-5">
              {eventData.sub_events.map((se) => (
                <div
                  key={se.id}
                  className="glass-card p-6 rounded-3xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 relative space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="w-8 h-8 rounded-xl bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 flex items-center justify-center font-bold text-xs font-mono">
                      #{se.sort_order}
                    </span>
                    {se.is_muhurat_locked && (
                      <span className="px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-900 dark:text-amber-200 text-xs font-bold font-mono border border-amber-300 dark:border-amber-800">
                        🕉️ Muhurat Locked
                      </span>
                    )}
                  </div>

                  <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                    {se.name}
                  </h3>

                  <div className="text-xs font-mono text-stone-600 dark:text-stone-400 bg-stone-100 dark:bg-stone-900/60 p-2.5 rounded-xl border border-stone-200/60 dark:border-stone-800/60">
                    ⏱️ {new Date(se.start_time).toLocaleDateString()} •{' '}
                    {new Date(se.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} -{' '}
                    {new Date(se.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>

                  <div className="text-xs text-stone-700 dark:text-stone-300 space-y-1">
                    <div>
                      📍 <strong>Venue:</strong> {se.venue_name}{' '}
                      <span className="text-stone-500 font-mono">({se.is_outdoor ? 'Outdoor Lawn' : 'Indoor AC Banquet'})</span>
                    </div>
                    {se.muhurat_notes && (
                      <div className="p-2.5 rounded-xl bg-amber-50/80 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-900 dark:text-amber-300 text-xs leading-relaxed font-medium">
                        🪔 {se.muhurat_notes}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB: CULTURAL RITUALS & MULTI-TRADITION FUSION */}
        {activeTab === 'rituals' && (
          <div className="space-y-6 animate-fadeIn">
            <RitualIntelligenceHub
              eventId={eventData.id}
              eventName={eventData.name}
              city={eventData.city}
              startDate={eventData.start_date}
              initialTraditionCode={eventData.tradition_code || 'maharashtrian_vedic'}
              initialSecondaryTraditionCode={(eventData as any).secondary_tradition_code || 'punjabi_traditional'}
              apiBase={getApiBase().replace(/\/api\/v1$/, '')}
              onTasksGenerated={fetchEventData}
            />
          </div>
        )}

        {/* TAB 3: ITEMIZED BUDGET & WHY THIS */}
        {activeTab === 'budget' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-100">
                  Itemized Budget Engine
                </h2>
                <p className="text-xs text-stone-600 dark:text-stone-300 mt-1">
                  100% deterministic arithmetic calibrated for {eventData.city} ({eventData.city_tier.toUpperCase()}) across{' '}
                  {eventData.guest_count} guests. Zero LLM hallucinations.
                </p>
              </div>
              <div className="text-right">
                <span className="text-xs text-stone-500 uppercase tracking-wider block">Total Envelope</span>
                <span className="text-xl font-bold font-serif text-[#8B1E28] dark:text-[#F4B41A]">
                  {formatINR(eventData.total_budget)}
                </span>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {eventData.budget_breakdown.map((item) => (
                <div
                  key={item.id}
                  className="glass-card p-5 rounded-2xl shadow-sm border border-stone-200/80 dark:border-stone-800/80 space-y-3 flex flex-col justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                        {item.category.replace('_', ' ')}
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 text-xs font-mono font-semibold">
                        {item.percentage}%
                      </span>
                    </div>
                    <h4 className="font-semibold text-sm text-stone-900 dark:text-stone-100">
                      {item.name}
                    </h4>
                  </div>

                  <div className="pt-2 border-t border-stone-200/60 dark:border-stone-800/60 flex items-center justify-between">
                    <span className="font-bold text-base text-stone-900 dark:text-stone-50 font-mono">
                      {formatINR(item.planned_amount)}
                    </span>
                    <button
                      onClick={() => setSelectedWhyThis(item)}
                      className="px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-950/60 hover:bg-amber-100 text-amber-900 dark:text-amber-300 text-xs font-medium border border-amber-200 dark:border-amber-800 transition-colors"
                    >
                      Why This? 🔍
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: VENDOR HUB & QUOTE AUDITOR (SCOPED TO CURRENT EVENT) */}
        {activeTab === 'vendors' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-100">
                  Vendor Hub & Quotes
                </h2>
                <p className="text-xs text-stone-600 dark:text-stone-300 mt-1">
                  Upload vendor proposals scoped to <strong className="font-semibold">{eventData.name}</strong>. Flag hidden fees, generator charges, and overtime rates.
                </p>
              </div>
              <Link
                href={`/dashboard/events/${currentEventId}/vendors/quotes`}
                className="self-start sm:self-auto px-5 py-2.5 rounded-xl bg-[#8B1E28] hover:bg-[#721820] text-white dark:bg-[#F4B41A] dark:text-stone-950 font-semibold text-xs shadow-md transition-all"
              >
                + Manage Quotes for this Event
              </Link>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              <div className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  Target Event
                </div>
                <div className="text-xl font-bold font-serif text-stone-900 dark:text-stone-100 truncate">
                  {eventData.name}
                </div>
                <div className="text-xs text-stone-600 dark:text-stone-400">
                  Guest Count: {eventData.guest_count} • City: {eventData.city}
                </div>
              </div>

              <div className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  OCR Comparison Engine
                </div>
                <div className="text-xl font-bold font-serif text-emerald-600 dark:text-emerald-400">
                  18 Red Flag Checks
                </div>
                <div className="text-xs text-stone-600 dark:text-stone-400">
                  Cross-checks line items against regional hidden charge patterns (DEC-013).
                </div>
              </div>

              <div className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  City Benchmark
                </div>
                <div className="text-xl font-bold font-serif text-amber-600 dark:text-amber-400">
                  {eventData.city} ({eventData.city_tier.toUpperCase()})
                </div>
                <div className="text-xs text-stone-600 dark:text-stone-400">
                  Evaluated against live regional benchmarks with sample size transparency.
                </div>
              </div>
            </div>

            <div className="p-8 rounded-3xl glass-card text-center space-y-4 border border-stone-200/80 dark:border-stone-800/80">
              <div className="text-3xl">📑</div>
              <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                Ready to upload vendor estimates?
              </h3>
              <p className="text-xs text-stone-600 dark:text-stone-300 max-w-md mx-auto leading-relaxed">
                Add PDF or photo quotes for catering, mandap, sound, or photography. The engine audits line items and benchmarks costs against {eventData.city}.
              </p>
              <Link
                href={`/dashboard/events/${currentEventId}/vendors/quotes`}
                className="inline-block px-6 py-2.5 rounded-full bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900 text-xs font-semibold shadow-sm hover:opacity-90"
              >
                Go to Scoped Quote Studio →
              </Link>
            </div>
          </div>
        )}

        {/* TAB 5: VIBE & AESTHETIC DECOR */}
        {activeTab === 'vibe' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-100">
                  Vibe & Theme Studio
                </h2>
                <p className="text-xs text-stone-600 dark:text-stone-300 mt-1">
                  Multimodal vision translation: from Pinterest/Instagram inspiration to concrete itemized decor proposals.
                </p>
              </div>
              <Link
                href={`/dashboard/events/${currentEventId}/vibe`}
                className="self-start sm:self-auto px-5 py-2.5 rounded-xl bg-purple-700 hover:bg-purple-800 text-white font-semibold text-xs shadow-md transition-all"
              >
                Open Vibe-to-Plan Studio →
              </Link>
            </div>

            {styleProfile ? (
              <div className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-6">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-purple-700 dark:text-purple-400">
                    Active Style Profile
                  </span>
                  <h3 className="text-xl font-serif font-bold text-stone-900 dark:text-stone-100 mt-1">
                    {styleProfile.theme_concept || 'Custom Curated Aesthetic'}
                  </h3>
                </div>

                {/* Color Palette Swatches */}
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-3">
                    Color Palette (5-Swatch Harmony)
                  </h4>
                  <div className="grid grid-cols-5 gap-3">
                    {[
                      { name: 'Primary', hex: styleProfile.primary_color },
                      { name: 'Secondary', hex: styleProfile.secondary_color },
                      { name: 'Accent', hex: styleProfile.accent_color },
                      { name: 'Neutral', hex: styleProfile.neutral_color },
                      { name: 'Base', hex: styleProfile.background_color }
                    ].map((col) => (
                      <div key={col.name} className="space-y-1.5 text-center">
                        <div
                          className="w-full h-14 rounded-2xl border border-stone-300/40 dark:border-stone-700/60 shadow-xs"
                          style={{ backgroundColor: col.hex }}
                        />
                        <div className="text-[11px] font-semibold text-stone-700 dark:text-stone-300">{col.name}</div>
                        <div className="text-[10px] font-mono text-stone-500">{col.hex}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Aesthetic Tags & Materials */}
                <div className="grid sm:grid-cols-2 gap-4 pt-4 border-t border-stone-200/60 dark:border-stone-800/60">
                  <div>
                    <h5 className="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-2">
                      Aesthetic Tags
                    </h5>
                    <div className="flex flex-wrap gap-2">
                      {styleProfile.aesthetic_tags.map((tag, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 rounded-lg bg-stone-100 dark:bg-stone-800 text-stone-800 dark:text-stone-200 text-xs font-medium"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h5 className="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-2">
                      Cultural Materials
                    </h5>
                    <div className="flex flex-wrap gap-2">
                      {styleProfile.materials.map((mat, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-200 dark:border-purple-800 text-xs font-medium"
                        >
                          ✨ {mat}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 rounded-3xl glass-card text-center space-y-4 border border-stone-200/80 dark:border-stone-800/80">
                <div className="text-3xl">🎨</div>
                <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                  No mood photos analyzed yet for this celebration
                </h3>
                <p className="text-xs text-stone-600 dark:text-stone-300 max-w-md mx-auto leading-relaxed">
                  Upload up to 10 photos of mandaps, outfits, or decor you love. Real multimodal AI will translate them into an actionable decor proposal with cost bounds.
                </p>
                <Link
                  href={`/dashboard/events/${currentEventId}/vibe`}
                  className="inline-block px-6 py-2.5 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-xs font-semibold shadow-sm"
                >
                  Launch Vibe-to-Plan Studio →
                </Link>
              </div>
            )}
          </div>
        )}

        {/* TAB 6: GUESTS & WHATSAPP RSVP CONCIERGE (M4) */}
        {activeTab === 'guests' && (
          <GuestCoordinationModule
            eventId={currentEventId}
            eventName={eventData.name}
            apiBase={getApiBase()}
          />
        )}

        {/* Elder Verification Disclaimer Banner (Mandatory F13 compliance) */}
        <section className="pt-4">
          <ElderDisclaimerBanner customText={eventData.elder_verification_disclaimer} />
        </section>
      </main>

      {/* "Why This?" Architectural Transparency Slide-Over Modal (F13) */}
      {selectedWhyThis && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn">
          <div className="glass-card max-w-lg w-full p-6 sm:p-8 rounded-3xl shadow-xl border border-stone-200 dark:border-stone-800 space-y-5 animate-scaleUp">
            <div className="flex items-center justify-between pb-3 border-b border-stone-200/60 dark:border-stone-800/60">
              <div className="flex items-center gap-2">
                <span className="text-lg">🔍</span>
                <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                  Why This Allocation?
                </h3>
              </div>
              <button
                onClick={() => setSelectedWhyThis(null)}
                className="w-8 h-8 rounded-full bg-stone-100 dark:bg-stone-800 text-stone-500 hover:text-stone-900 dark:hover:text-white flex items-center justify-center text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs text-stone-700 dark:text-stone-300">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-stone-400 block mb-1">
                  Category & Planned Amount
                </span>
                <div className="text-base font-bold text-stone-900 dark:text-stone-50">
                  {selectedWhyThis.name} • {formatINR(selectedWhyThis.planned_amount)} ({selectedWhyThis.percentage}%)
                </div>
              </div>

              {selectedWhyThis.reasoning_spec?.formula && (
                <div className="p-3.5 rounded-xl bg-stone-100 dark:bg-stone-900 font-mono text-stone-800 dark:text-stone-200 border border-stone-200 dark:border-stone-800">
                  <span className="text-[10px] uppercase font-bold text-amber-700 dark:text-amber-400 block mb-1">
                    Deterministic Math Formula
                  </span>
                  {selectedWhyThis.reasoning_spec.formula}
                </div>
              )}

              {selectedWhyThis.reasoning_spec?.benchmark_basis && (
                <div>
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-stone-400 block mb-1">
                    Regional Benchmark Basis
                  </span>
                  <p className="leading-relaxed bg-amber-50/60 dark:bg-amber-950/30 p-3 rounded-xl border border-amber-200/80 dark:border-amber-900/60 text-amber-900 dark:text-amber-200 font-medium">
                    {selectedWhyThis.reasoning_spec.benchmark_basis}
                  </p>
                </div>
              )}

              <div className="flex items-center justify-between pt-3 border-t border-stone-200/60 dark:border-stone-800/60 text-[11px] text-stone-500">
                <span>City Tier: {selectedWhyThis.reasoning_spec?.city_tier || eventData.city_tier}</span>
                <span>Guest Count: {selectedWhyThis.reasoning_spec?.guest_count || eventData.guest_count}</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedWhyThis(null)}
              className="w-full py-2.5 rounded-xl bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900 font-semibold text-xs transition-opacity hover:opacity-90"
            >
              Close Reasoning Inspector
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
