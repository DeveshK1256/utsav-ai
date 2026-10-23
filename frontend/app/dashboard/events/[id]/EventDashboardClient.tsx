'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Navbar } from '@/components/ui/Navbar';
import { ElderDisclaimerBanner } from '@/components/ui/ElderDisclaimerBanner';

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

const DEFAULT_EVENT_DATA: EventData = {
  id: 'default',
  name: "Ananya & Rohan's Celebration",
  owner_name: 'Rohan Joshi',
  event_type: 'wedding',
  city: 'Pune',
  city_tier: 'tier_2',
  guest_count: 350,
  total_budget: 3500000,
  tradition_code: 'maharashtrian_vedic',
  status: 'planning',
  start_date: '2027-11-12',
  end_date: '2027-11-14',
  elder_verification_disclaimer:
    'Auspicious timings & ritual checklists are algorithmic estimates computed via astronomical ephemeris models. Please verify with your family Guruji or elders.',
  sub_events: [
    {
      id: 'se-1',
      name: 'Sakharpuda (Engagement & Ring Ceremony)',
      start_time: '2027-11-12T10:00:00',
      end_time: '2027-11-12T13:00:00',
      venue_name: 'The Heritage Banquets, Koregaon Park',
      is_outdoor: false,
      is_muhurat_locked: true,
      muhurat_notes: 'Shubh Muhurat fixed by Panditji: 10:45 AM - 11:30 AM',
      sort_order: 1
    },
    {
      id: 'se-2',
      name: 'Haldi & Sangeet Evening',
      start_time: '2027-11-12T17:00:00',
      end_time: '2027-11-12T22:30:00',
      venue_name: 'Emerald Lawns (Open Air Pavilion)',
      is_outdoor: true,
      is_muhurat_locked: false,
      muhurat_notes: 'Sound curfew enforced strictly at 10:00 PM',
      sort_order: 2
    },
    {
      id: 'se-3',
      name: 'Mandap Muhurat & Lagna Vivah',
      start_time: '2027-11-13T09:30:00',
      end_time: '2027-11-13T14:30:00',
      venue_name: 'Vedic Wedding Hall, Pune',
      is_outdoor: false,
      is_muhurat_locked: true,
      muhurat_notes: 'Sacred Saptapadi Muhurat: 11:15 AM (Rahu Kaal clear)',
      sort_order: 3
    },
    {
      id: 'se-4',
      name: 'Grand Reception & Gala Dinner',
      start_time: '2027-11-13T19:00:00',
      end_time: '2027-11-13T23:30:00',
      venue_name: 'Grand Ballroom, JW Marriott Pune',
      is_outdoor: false,
      is_muhurat_locked: false,
      muhurat_notes: 'Photo sessions initiate promptly at 7:30 PM',
      sort_order: 4
    }
  ],
  budget_breakdown: [
    {
      id: 'b-1',
      category: 'catering',
      name: 'Catering & Food Service',
      planned_amount: 980000,
      actual_amount: 0,
      percentage: 28,
      reasoning_spec: {
        formula: '350 guests × 2 meals × ₹1,400 tier-2 rate',
        city_tier: 'tier_2',
        guest_count: 350,
        benchmark_basis: 'Regional catering index calibrated for Pune Tier-2 banquet rates'
      }
    },
    {
      id: 'b-2',
      category: 'venue',
      name: 'Venue & Banquet Rental',
      planned_amount: 770000,
      actual_amount: 0,
      percentage: 22,
      reasoning_spec: {
        formula: '2 days dual-venue package (Indoor Hall + Lawn)',
        city_tier: 'tier_2',
        guest_count: 350,
        benchmark_basis: 'Pune venue rental market rate for 350-capacity premium lawns'
      }
    },
    {
      id: 'b-3',
      category: 'decor',
      name: 'Mandap & Floral Decor',
      planned_amount: 560000,
      actual_amount: 0,
      percentage: 16,
      reasoning_spec: {
        formula: 'Traditional Marigold mandap + Sangeet stage trussing',
        city_tier: 'tier_2',
        guest_count: 350,
        benchmark_basis: 'Authentic Maharashtrian floral & fabric decor benchmark'
      }
    },
    {
      id: 'b-4',
      category: 'photography',
      name: 'Photography & Cinematography',
      planned_amount: 315000,
      actual_amount: 0,
      percentage: 9,
      reasoning_spec: {
        formula: '3-day traditional + candid coverage + drone footage',
        city_tier: 'tier_2',
        guest_count: 350,
        benchmark_basis: 'Standard Tier-2 multi-cam cinematic production tier'
      }
    },
    {
      id: 'b-5',
      category: 'entertainment',
      name: 'DJ, Sound & Sangeet Artists',
      planned_amount: 245000,
      actual_amount: 0,
      percentage: 7,
      reasoning_spec: {
        formula: 'Sound system rental + Dhol tasha troupe + Sangeet DJ',
        city_tier: 'tier_2',
        guest_count: 350,
        benchmark_basis: 'Regional entertainment tariff guidelines'
      }
    },
    {
      id: 'b-6',
      category: 'wardrobe',
      name: 'Bridal & Groom Attire',
      planned_amount: 210000,
      actual_amount: 0,
      percentage: 6,
      reasoning_spec: {
        formula: 'Paithani silk sarees, Nauvari, and traditional Kurta sets',
        city_tier: 'tier_2',
        guest_count: 350,
        benchmark_basis: 'Maharashtrian traditional wedding trousseau benchmark'
      }
    },
    {
      id: 'b-7',
      category: 'rituals',
      name: 'Panditji Dakshina & Samagri',
      planned_amount: 140000,
      actual_amount: 0,
      percentage: 4,
      reasoning_spec: {
        formula: 'Complete Vedic samagri kit + Guruji dakshina for 4 ceremonies',
        city_tier: 'tier_2',
        guest_count: 350,
        benchmark_basis: 'Deterministic Vedic Lagna ritual samagri list'
      }
    },
    {
      id: 'b-8',
      category: 'logistics',
      name: 'Guest Shuttles & Valet',
      planned_amount: 140000,
      actual_amount: 0,
      percentage: 4,
      reasoning_spec: {
        formula: '2 Tempo Travellers + 4 valet drivers across 2 days',
        city_tier: 'tier_2',
        guest_count: 350,
        benchmark_basis: 'Intra-city transport & logistics allocation'
      }
    },
    {
      id: 'b-9',
      category: 'contingency',
      name: 'Contingency & Fuel Buffer',
      planned_amount: 140000,
      actual_amount: 0,
      percentage: 4,
      reasoning_spec: {
        formula: '4% unallocated buffer for generator fuel & overtime',
        city_tier: 'tier_2',
        guest_count: 350,
        benchmark_basis: 'Mandatory contingency reserve against vendor slippage'
      }
    }
  ],
  tasks: [
    {
      id: 't-1',
      title: 'Lock Caterer Menu & Food Tasting Session',
      status: 'scheduled',
      scheduled_start: '2027-10-15T11:00:00',
      scheduled_end: '2027-10-15T14:00:00',
      assigned_role: 'Food Coordinator'
    },
    {
      id: 't-2',
      title: 'Panditji Samagri Checklist Verification',
      status: 'scheduled',
      scheduled_start: '2027-10-20T10:00:00',
      scheduled_end: '2027-10-20T11:30:00',
      assigned_role: 'Family Elder'
    },
    {
      id: 't-3',
      title: 'Stage Lighting & Audio Soundcheck',
      status: 'scheduled',
      scheduled_start: '2027-11-12T15:00:00',
      scheduled_end: '2027-11-12T16:30:00',
      assigned_role: 'Tech Lead'
    },
    {
      id: 't-4',
      title: 'Arrival of Fresh Marigold & Lotus Garlands',
      status: 'scheduled',
      scheduled_start: '2027-11-13T07:00:00',
      scheduled_end: '2027-11-13T08:30:00',
      assigned_role: 'Decor Supervisor'
    }
  ]
};

export default function EventDashboardClient() {
  const params = useParams();
  const eventId = (params?.id as string) || 'default';

  const [eventData, setEventData] = useState<EventData>(DEFAULT_EVENT_DATA);
  const [styleProfile, setStyleProfile] = useState<StyleProfile | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'itinerary' | 'budget' | 'vendors' | 'vibe'>('overview');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLiveConnected, setIsLiveConnected] = useState<boolean>(false);
  const [selectedWhyThis, setSelectedWhyThis] = useState<BudgetItem | null>(null);

  // Store active event ID to localStorage for quick navigation
  useEffect(() => {
    if (eventId && eventId !== 'default') {
      try {
        localStorage.setItem('utsav_last_event_id', eventId);
      } catch (e) {
        // ignore
      }
    }
  }, [eventId]);

  // Load Event Data and Style Profiles
  useEffect(() => {
    let isMounted = true;
    const fetchEventData = async () => {
      setIsLoading(true);
      const apiBase =
        typeof window !== 'undefined' && window.location.hostname.includes('netlify.app')
          ? '/api/v1'
          : 'https://utsav-ai-ycg2.onrender.com/api/v1';

      if (eventId && eventId !== 'default') {
        try {
          const res = await fetch(`${apiBase}/events/${eventId}`);
          if (res.ok) {
            const data = await res.json();
            if (isMounted) {
              setEventData({
                id: data.id,
                name: data.name || DEFAULT_EVENT_DATA.name,
                owner_name: data.owner_name || DEFAULT_EVENT_DATA.owner_name,
                event_type: data.event_type || DEFAULT_EVENT_DATA.event_type,
                city: data.city || DEFAULT_EVENT_DATA.city,
                city_tier: data.city_tier || 'tier_2',
                guest_count: data.guest_count || DEFAULT_EVENT_DATA.guest_count,
                total_budget: data.total_budget || DEFAULT_EVENT_DATA.total_budget,
                tradition_code: data.tradition_code || DEFAULT_EVENT_DATA.tradition_code,
                status: data.status || 'planning',
                start_date: data.start_date || DEFAULT_EVENT_DATA.start_date,
                end_date: data.end_date || DEFAULT_EVENT_DATA.end_date,
                elder_verification_disclaimer:
                  data.elder_verification_disclaimer || DEFAULT_EVENT_DATA.elder_verification_disclaimer,
                sub_events: data.sub_events && data.sub_events.length > 0 ? data.sub_events : DEFAULT_EVENT_DATA.sub_events,
                budget_breakdown:
                  data.budget_breakdown && data.budget_breakdown.length > 0
                    ? data.budget_breakdown
                    : DEFAULT_EVENT_DATA.budget_breakdown,
                tasks: data.tasks && data.tasks.length > 0 ? data.tasks : DEFAULT_EVENT_DATA.tasks
              });
              setIsLiveConnected(true);
            }
          }
        } catch (err) {
          console.warn('Could not fetch remote event; running with cached state', err);
        }

        // Try fetching style profiles
        try {
          const vibeRes = await fetch(`${apiBase}/events/${eventId}/vibe/profiles`);
          if (vibeRes.ok) {
            const profiles = await vibeRes.json();
            if (isMounted && profiles && profiles.length > 0) {
              setStyleProfile(profiles[0]);
            }
          }
        } catch (e) {
          // ignore
        }
      }

      if (isMounted) setIsLoading(false);
    };

    fetchEventData();
    return () => {
      isMounted = false;
    };
  }, [eventId]);

  // Derived KPI calculations
  const totalAllocated = useMemo(() => {
    return eventData.budget_breakdown.reduce((sum, item) => sum + (item.planned_amount || 0), 0);
  }, [eventData.budget_breakdown]);

  const muhuratCount = useMemo(() => {
    return eventData.sub_events.filter((s) => s.is_muhurat_locked).length;
  }, [eventData.sub_events]);

  const traditionTitle = useMemo(() => {
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
  }, [eventData.tradition_code]);

  return (
    <div className="min-h-screen pb-24">
      {/* Universal Navbar */}
      <Navbar
        badge="Live Command"
        rightAction={
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                isLiveConnected
                  ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                  : 'bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isLiveConnected ? 'bg-emerald-500' : 'bg-amber-500'} animate-pulse`} />
              {isLiveConnected ? 'DB Live' : 'Demo Mode'}
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
          <span className="font-mono text-stone-400 truncate max-w-[200px]">{eventId}</span>
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

            {/* Quick Action Navigation CTAs */}
            <div className="flex flex-wrap sm:flex-nowrap gap-2.5 self-start lg:self-center">
              <Link
                href={`/dashboard/events/${eventId}/changes/default`}
                className="px-4 py-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs font-semibold hover:bg-amber-100 dark:hover:bg-amber-900/60 transition-all shadow-sm flex items-center gap-1.5"
              >
                <span>⚡</span> Plan B Replanner
              </Link>
              <Link
                href={`/dashboard/events/${eventId}/vibe`}
                className="px-4 py-2.5 rounded-xl bg-purple-50 dark:bg-purple-950/60 border border-purple-300 dark:border-purple-800 text-purple-900 dark:text-purple-200 text-xs font-semibold hover:bg-purple-100 dark:hover:bg-purple-900/60 transition-all shadow-sm flex items-center gap-1.5"
              >
                <span>🎨</span> Vibe Studio
              </Link>
              <Link
                href="/dashboard/vendors/quotes"
                className="px-4 py-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 text-xs font-semibold hover:bg-emerald-100 dark:hover:bg-emerald-900/60 transition-all shadow-sm flex items-center gap-1.5"
              >
                <span>📑</span> Quote Auditor
              </Link>
            </div>
          </div>
        </section>

        {/* Live KPI Cards (4 Pillars) */}
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
            { key: 'budget', label: 'Itemized Budget & Formulas', icon: '💰' },
            { key: 'vendors', label: 'Vendor Hub & Quotes', icon: '🤝' },
            { key: 'vibe', label: 'Vibe & Aesthetic Decor', icon: '🎨' }
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
                  href={`/dashboard/events/${eventId}/changes/default`}
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
                  href={`/dashboard/events/${eventId}/vibe`}
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
                  href="/dashboard/vendors/quotes"
                  className="inline-flex items-center text-xs font-bold text-emerald-700 dark:text-emerald-400 hover:underline gap-1"
                >
                  Audit Vendor Quotes →
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
                  {eventData.sub_events.slice(0, 3).map((se) => (
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
                  ))}
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
                  {eventData.tasks.slice(0, 4).map((task) => (
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
                  ))}
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

        {/* TAB 4: VENDOR HUB & QUOTE AUDITOR */}
        {activeTab === 'vendors' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-100">
                  Vendor Hub & Quote Management
                </h2>
                <p className="text-xs text-stone-600 dark:text-stone-300 mt-1">
                  Upload vendor proposals and let the deterministic comparison engine flag hidden fees, generator surges, and overtime rates.
                </p>
              </div>
              <Link
                href="/dashboard/vendors/quotes"
                className="self-start sm:self-auto px-5 py-2.5 rounded-xl bg-[#8B1E28] hover:bg-[#721820] text-white dark:bg-[#F4B41A] dark:text-stone-950 font-semibold text-xs shadow-md transition-all"
              >
                + Upload Quote for Audit
              </Link>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              <div className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  Required Vendors Shortlist
                </div>
                <div className="text-2xl font-bold font-serif text-stone-900 dark:text-stone-100">
                  8 Categories
                </div>
                <div className="text-xs text-stone-600 dark:text-stone-400">
                  Caterer, Mandap, Sound & Light, Priest, Photography, Hair & Makeup, Transport, Hospitality.
                </div>
              </div>

              <div className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  Audited Quotes
                </div>
                <div className="text-2xl font-bold font-serif text-emerald-600 dark:text-emerald-400">
                  Active OCR Engine
                </div>
                <div className="text-xs text-stone-600 dark:text-stone-400">
                  Cross-checks line items against 18 regional hidden charge patterns (DEC-013).
                </div>
              </div>

              <div className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  City Benchmark
                </div>
                <div className="text-2xl font-bold font-serif text-amber-600 dark:text-amber-400">
                  {eventData.city} ({eventData.city_tier.toUpperCase()})
                </div>
                <div className="text-xs text-stone-600 dark:text-stone-400">
                  Quotes evaluated against live database benchmarks with full sample size transparency.
                </div>
              </div>
            </div>

            <div className="p-8 rounded-3xl glass-card text-center space-y-4 border border-stone-200/80 dark:border-stone-800/80">
              <div className="text-3xl">📑</div>
              <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                Ready to review vendor estimates?
              </h3>
              <p className="text-xs text-stone-600 dark:text-stone-300 max-w-md mx-auto leading-relaxed">
                Run quotes side-by-side to identify discrepancy percentages and negotiate with AI-assisted WhatsApp templates.
              </p>
              <Link
                href="/dashboard/vendors/quotes"
                className="inline-block px-6 py-2.5 rounded-full bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900 text-xs font-semibold shadow-sm hover:opacity-90"
              >
                Go to Quote Comparison Matrix →
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
                href={`/dashboard/events/${eventId}/vibe`}
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
                  No mood photos analyzed yet
                </h3>
                <p className="text-xs text-stone-600 dark:text-stone-300 max-w-md mx-auto leading-relaxed">
                  Upload up to 10 photos of mandaps, outfits, or decor you love. Real multimodal AI will translate them into an actionable decor proposal with cost bounds.
                </p>
                <Link
                  href={`/dashboard/events/${eventId}/vibe`}
                  className="inline-block px-6 py-2.5 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-xs font-semibold shadow-sm"
                >
                  Launch Vibe-to-Plan Studio →
                </Link>
              </div>
            )}
          </div>
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
                <span>City Tier: {selectedWhyThis.reasoning_spec?.city_tier || 'Tier-2'}</span>
                <span>Guest Count: {selectedWhyThis.reasoning_spec?.guest_count || 350}</span>
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
