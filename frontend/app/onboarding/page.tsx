'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { ElderDisclaimerBanner } from '@/components/ui/ElderDisclaimerBanner';

interface BudgetItemCalculation {
  category: string;
  percentage: number;
  planned_amount: number;
  city_tier: string;
  city_tier_multiplier: number;
  reasoning_spec: {
    formula: string;
    city_tier: string;
    guest_count: number;
    benchmark_basis: string;
  };
}

interface BudgetCalculationResponse {
  city: string;
  city_tier: string;
  city_tier_multiplier: number;
  total_budget: number;
  scaled_envelope: number;
  items: BudgetItemCalculation[];
}

interface SubEventResponse {
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

interface BudgetItemResponse {
  id: string;
  category: string;
  name: string;
  planned_amount: number;
  actual_amount: number;
  percentage: number;
  reasoning_spec?: any;
}

interface TaskResponse {
  id: string;
  title: string;
  status: string;
  scheduled_start?: string;
  scheduled_end?: string;
  duration_minutes?: number;
  assigned_role?: string;
}

interface MasterPlanResponse {
  event_id: string;
  name: string;
  owner_name: string;
  status: string;
  city_tier: string;
  total_budget: number;
  guest_count: number;
  tradition_code: string;
  elder_verification_disclaimer: string;
  sub_events: SubEventResponse[];
  budget_breakdown: BudgetItemResponse[];
  tasks: TaskResponse[];
  created_at: string;
}

const TRADITIONS = [
  {
    code: 'maharashtrian_vedic',
    name: 'Maharashtrian Vedic Lagna',
    highlights: 'Sakharpuda, Haldi, Mandap Muhurat, Saptapadi, Reception',
    icon: '🕉️'
  },
  {
    code: 'gujarati_hindu',
    name: 'Gujarati Hindu Vivah',
    highlights: 'Mameru, Dandiya Raas, Mandap, Hastamelap, Gala Dinner',
    icon: '🪔'
  },
  {
    code: 'punjabi_sikh',
    name: 'Punjabi Anand Karaj',
    highlights: 'Roka, Chunni, Mehndi/Sangeet, Anand Karaj, Grand Reception',
    icon: '✨'
  },
  {
    code: 'south_indian_iyer',
    name: 'Tamil Brahmin Iyer Kalyanam',
    highlights: 'Vratham, Janavasam, Kasi Yatra, Oonjal, Kanyadaan',
    icon: '🌸'
  },
  {
    code: 'marwari_traditional',
    name: 'Marwari Traditional Vivah',
    highlights: 'Mudha Tika, Pithi, Tel Baan, Baraat, Royal Feast',
    icon: '👑'
  },
  {
    code: 'satyanarayan_puja',
    name: 'Satyanarayan Vrat & Griha Pravesh',
    highlights: 'Veda Pathan, Katha, Mahaprasad, Family Blessing',
    icon: '🙏'
  }
];

// Single source of API endpoint configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://utsav-api-engine.loca.lt/api/v1';

export default function OnboardingPage() {
  const [step, setStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isLoadingBudget, setIsLoadingBudget] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    name: "Ananya & Rohan's Celebration",
    hostName: 'Rohan Joshi',
    phone: '+91 98220 12345',
    eventType: 'wedding',
    traditionCode: 'maharashtrian_vedic',
    city: 'Pune',
    pincode: '411001',
    startDate: '2027-11-12',
    endDate: '2027-11-14',
    guestCount: 350,
    budget: 3500000
  });

  // State populated STRICTLY by the backend API
  const [budgetCalc, setBudgetCalc] = useState<BudgetCalculationResponse | null>(null);
  const [masterPlan, setMasterPlan] = useState<MasterPlanResponse | null>(null);

  // Fetch backend budget calculation (Zero client-side math)
  const fetchBackendBudget = useCallback(async () => {
    setIsLoadingBudget(true);
    setApiError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/intake/calculate-budget`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Bypass-Tunnel-Reminder': 'true'
        },
        body: JSON.stringify({
          total_budget: formData.budget,
          event_type: formData.eventType,
          city: formData.city,
          guest_count: formData.guestCount
        })
      });

      if (!res.ok) {
        throw new Error(`Backend error (${res.status}): ${res.statusText}`);
      }

      const data: BudgetCalculationResponse = await res.json();
      setBudgetCalc(data);
    } catch (err: any) {
      console.error('Failed to load budget from backend:', err);
      setApiError('Live calculation engine unavailable. Ensure backend server is reachable.');
    } finally {
      setIsLoadingBudget(false);
    }
  }, [formData.budget, formData.eventType, formData.city, formData.guestCount]);

  // Debounced effect for live calculation from backend
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchBackendBudget();
    }, 300);
    return () => clearTimeout(timer);
  }, [fetchBackendBudget]);

  // Synthesize master plan strictly via backend API
  const handleSynthesize = async () => {
    setIsSubmitting(true);
    setApiError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/intake/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Bypass-Tunnel-Reminder': 'true'
        },
        body: JSON.stringify({
          name: formData.name,
          host_name: formData.hostName,
          phone_number: formData.phone,
          event_type: formData.eventType,
          tradition_code: formData.traditionCode,
          guest_count: formData.guestCount,
          total_budget: formData.budget,
          city: formData.city,
          pincode: formData.pincode,
          start_date: formData.startDate,
          end_date: formData.endDate
        })
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Synthesis failed with status ${res.status}`);
      }

      const planData: MasterPlanResponse = await res.json();
      setMasterPlan(planData);
      setStep(5);
    } catch (err: any) {
      console.error('Synthesis error:', err);
      setApiError(err.message || 'Failed to synthesize master plan from backend.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };

  return (
    <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-8 mb-8 border-b border-stone-200 dark:border-stone-800">
          <Link href="/" className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-kumkum via-marigold to-haldi flex items-center justify-center text-white font-devanagari text-xl shadow-md">
              उ
            </div>
            <div>
              <span className="text-xl font-serif font-bold tracking-wider">UTSAV</span>
              <span className="text-xs ml-2 px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/60 text-marigold font-semibold uppercase">
                Intake Studio
              </span>
            </div>
          </Link>
          <div className="text-xs text-stone-500 font-mono">
            {step <= 4 ? `Step ${step} of 4` : 'Plan Composed'}
          </div>
        </div>

        {/* Global Error Banner */}
        {apiError && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center justify-between">
            <span>⚠️ {apiError}</span>
            <button
              onClick={fetchBackendBudget}
              className="ml-3 px-3 py-1 rounded bg-rose-600 text-white font-semibold hover:bg-rose-700"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Step Indicator */}
        {step <= 4 && (
          <div className="mb-10">
            <div className="grid grid-cols-4 gap-2 mb-3">
              {[1, 2, 3, 4].map((s) => (
                <div
                  key={s}
                  className={`h-1.5 rounded-full transition-all duration-300 ${
                    s <= step ? 'bg-kumkum dark:bg-haldi' : 'bg-stone-200 dark:bg-stone-800'
                  }`}
                />
              ))}
            </div>
            <div className="flex justify-between text-xs text-stone-500 font-medium">
              <span>1. Basics</span>
              <span>2. Tradition</span>
              <span>3. Scale & Budget</span>
              <span>4. Review</span>
            </div>
          </div>
        )}

        {/* STEP 1: Event Basics */}
        {step === 1 && (
          <div className="p-8 rounded-3xl glass-card shadow-xl space-y-6">
            <div>
              <h2 className="text-2xl font-serif font-semibold mb-1">Let’s begin crafting your celebration</h2>
              <p className="text-stone-500 text-sm">Tell us the foundational details of your gathering.</p>
            </div>

            <div className="grid sm:grid-cols-2 gap-5">
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">
                  Celebration Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-700 text-sm focus:outline-none focus:ring-2 focus:ring-marigold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">
                  Primary Host / Couple Name
                </label>
                <input
                  type="text"
                  value={formData.hostName}
                  onChange={(e) => setFormData({ ...formData, hostName: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-700 text-sm focus:outline-none focus:ring-2 focus:ring-marigold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">
                  Host WhatsApp Number (for updates)
                </label>
                <input
                  type="text"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-700 text-sm focus:outline-none focus:ring-2 focus:ring-marigold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">
                  Celebration City
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-700 text-sm focus:outline-none focus:ring-2 focus:ring-marigold"
                  />
                  {budgetCalc && (
                    <span className="absolute right-3 top-3 text-xs px-2 py-0.5 rounded-md bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-300 font-mono">
                      {budgetCalc.city_tier} ({budgetCalc.city_tier_multiplier}x)
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">
                  Venue Pincode
                </label>
                <input
                  type="text"
                  value={formData.pincode}
                  onChange={(e) => setFormData({ ...formData, pincode: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-700 text-sm focus:outline-none focus:ring-2 focus:ring-marigold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">
                  Celebration Start Date
                </label>
                <input
                  type="date"
                  value={formData.startDate}
                  onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-700 text-sm focus:outline-none focus:ring-2 focus:ring-marigold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1.5">
                  Celebration End Date
                </label>
                <input
                  type="date"
                  value={formData.endDate}
                  onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-700 text-sm focus:outline-none focus:ring-2 focus:ring-marigold"
                />
              </div>
            </div>

            <div className="pt-4 flex justify-end">
              <button
                onClick={() => setStep(2)}
                className="px-8 py-3 rounded-full bg-kumkum text-white dark:bg-haldi dark:text-stone-950 font-semibold text-sm hover:opacity-90 transition-all shadow-md"
              >
                Continue to Traditions →
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: Cultural Tradition Selection */}
        {step === 2 && (
          <div className="p-8 rounded-3xl glass-card shadow-xl space-y-6">
            <div>
              <h2 className="text-2xl font-serif font-semibold mb-1">Select Cultural & Ritual Heritage</h2>
              <p className="text-stone-500 text-sm">
                Utsav pre-loads verified ritual sequencing, samagri checklists, and solar-lunar alignments.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              {TRADITIONS.map((trad) => {
                const isSelected = formData.traditionCode === trad.code;
                return (
                  <div
                    key={trad.code}
                    onClick={() => setFormData({ ...formData, traditionCode: trad.code })}
                    className={`p-5 rounded-2xl cursor-pointer transition-all border text-left ${
                      isSelected
                        ? 'border-2 border-kumkum bg-amber-50/50 dark:border-haldi dark:bg-amber-950/20 shadow-md'
                        : 'border-stone-200 dark:border-stone-800 hover:border-stone-300 bg-white dark:bg-stone-900/50'
                    }`}
                  >
                    <div className="flex items-center space-x-3 mb-2">
                      <span className="text-2xl">{trad.icon}</span>
                      <h4 className="font-semibold text-sm">{trad.name}</h4>
                    </div>
                    <p className="text-xs text-stone-500 dark:text-stone-400 leading-relaxed">
                      {trad.highlights}
                    </p>
                  </div>
                );
              })}
            </div>

            <ElderDisclaimerBanner />

            <div className="pt-4 flex justify-between">
              <button
                onClick={() => setStep(1)}
                className="px-6 py-2.5 rounded-full border border-stone-300 text-sm font-medium hover:bg-stone-100 dark:hover:bg-stone-800"
              >
                ← Back
              </button>
              <button
                onClick={() => setStep(3)}
                className="px-8 py-3 rounded-full bg-kumkum text-white dark:bg-haldi dark:text-stone-950 font-semibold text-sm hover:opacity-90 transition-all shadow-md"
              >
                Continue to Scale & Budget →
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: Scale & Budget Envelope (All math from FastAPI Backend) */}
        {step === 3 && (
          <div className="p-8 rounded-3xl glass-card shadow-xl space-y-6">
            <div>
              <h2 className="text-2xl font-serif font-semibold mb-1">Scale & Budget Envelope</h2>
              <p className="text-stone-500 text-sm">
                Calibrated in real time via FastAPI backend ({budgetCalc?.city_tier || 'tier_1'} • {budgetCalc?.city_tier_multiplier || 1.0}x). Zero client-side guesswork.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-stone-500 mb-2">
                Estimated Guest Headcount: <strong className="text-stone-900 dark:text-white text-base">{formData.guestCount} Guests</strong>
              </label>
              <div className="flex gap-2 mb-3">
                {[150, 250, 350, 500, 800].map((count) => (
                  <button
                    key={count}
                    type="button"
                    onClick={() => setFormData({ ...formData, guestCount: count })}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${
                      formData.guestCount === count
                        ? 'bg-kumkum text-white border-kumkum dark:bg-haldi dark:text-stone-950'
                        : 'border-stone-300 hover:bg-stone-100 dark:border-stone-700 dark:hover:bg-stone-800'
                    }`}
                  >
                    {count}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  Target Budget Envelope
                </span>
                <span className="text-2xl font-bold font-mono text-kumkum dark:text-haldi">
                  {formatINR(formData.budget)}
                </span>
              </div>
              <input
                type="range"
                min="500000"
                max="15000000"
                step="250000"
                value={formData.budget}
                onChange={(e) => setFormData({ ...formData, budget: parseFloat(e.target.value) })}
                className="w-full accent-kumkum dark:accent-haldi cursor-pointer"
              />
            </div>

            {/* Live Backend Allocation Cards */}
            <div className="p-5 rounded-2xl bg-stone-100/70 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800">
              <div className="flex items-center justify-between mb-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  Authoritative Backend Allocation (FastAPI Compute Engine)
                </div>
                {isLoadingBudget && (
                  <span className="text-xs text-amber-600 animate-pulse font-mono">Computing in backend...</span>
                )}
              </div>

              {budgetCalc ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {budgetCalc.items.slice(0, 4).map((item, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-white dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
                      <div className="text-xs text-stone-400 capitalize">{item.category} ({item.percentage}%)</div>
                      <div className="font-bold text-sm mt-1">{formatINR(item.planned_amount)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center text-xs text-stone-400">Loading allocation breakdown from backend...</div>
              )}
            </div>

            <div className="pt-4 flex justify-between">
              <button
                onClick={() => setStep(2)}
                className="px-6 py-2.5 rounded-full border border-stone-300 text-sm font-medium hover:bg-stone-100 dark:hover:bg-stone-800"
              >
                ← Back
              </button>
              <button
                onClick={() => setStep(4)}
                className="px-8 py-3 rounded-full bg-kumkum text-white dark:bg-haldi dark:text-stone-950 font-semibold text-sm hover:opacity-90 transition-all shadow-md"
              >
                Review & Compose Plan →
              </button>
            </div>
          </div>
        )}

        {/* STEP 4: Review & Synthesis Submission */}
        {step === 4 && (
          <div className="p-8 rounded-3xl glass-card shadow-xl space-y-6">
            <div>
              <h2 className="text-2xl font-serif font-semibold mb-1">Review Celebration Blueprint</h2>
              <p className="text-stone-500 text-sm">
                Confirm your parameters before our backend engines assemble the master itinerary.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-stone-50 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800 space-y-4">
              <div className="grid sm:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-stone-400 block text-xs">Event:</span>
                  <strong className="text-stone-900 dark:text-white">{formData.name}</strong>
                </div>
                <div>
                  <span className="text-stone-400 block text-xs">Primary Host:</span>
                  <strong className="text-stone-900 dark:text-white">{formData.hostName} ({formData.phone})</strong>
                </div>
                <div>
                  <span className="text-stone-400 block text-xs">Location & Tier:</span>
                  <strong className="text-stone-900 dark:text-white">
                    {formData.city} • {budgetCalc ? `${budgetCalc.city_tier} (${budgetCalc.city_tier_multiplier}x)` : 'Tier 1'}
                  </strong>
                </div>
                <div>
                  <span className="text-stone-400 block text-xs">Dates:</span>
                  <strong className="text-stone-900 dark:text-white">{formData.startDate} to {formData.endDate}</strong>
                </div>
                <div>
                  <span className="text-stone-400 block text-xs">Guest Count:</span>
                  <strong className="text-stone-900 dark:text-white">{formData.guestCount} Confirmed Headcount</strong>
                </div>
                <div>
                  <span className="text-stone-400 block text-xs">Scaled Budget Envelope:</span>
                  <strong className="text-stone-900 dark:text-white">
                    {budgetCalc ? formatINR(budgetCalc.scaled_envelope) : formatINR(formData.budget)}
                  </strong>
                </div>
              </div>
            </div>

            <ElderDisclaimerBanner />

            <div className="pt-4 flex justify-between items-center">
              <button
                onClick={() => setStep(3)}
                disabled={isSubmitting}
                className="px-6 py-2.5 rounded-full border border-stone-300 text-sm font-medium hover:bg-stone-100 dark:hover:bg-stone-800 disabled:opacity-50"
              >
                ← Back
              </button>

              <button
                onClick={handleSynthesize}
                disabled={isSubmitting}
                className="px-10 py-4 rounded-full bg-gradient-to-r from-kumkum via-marigold to-haldi text-white font-bold text-sm hover:opacity-95 transition-all shadow-lg flex items-center space-x-3 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                    </svg>
                    <span>Synthesizing via FastAPI Backend...</span>
                  </>
                ) : (
                  <span>✨ Synthesize Master Plan</span>
                )}
              </button>
            </div>
          </div>
        )}

        {/* STEP 5: Master Plan Output Rendered from Backend */}
        {step === 5 && masterPlan && (
          <div className="space-y-8 animate-fadeIn">
            <div className="p-8 rounded-3xl glass-card shadow-2xl border-2 border-haldi/60 relative overflow-hidden">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-stone-200 dark:border-stone-800">
                <div>
                  <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 text-xs font-semibold mb-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>Backend Plan Synthesized • ID: {masterPlan.event_id}</span>
                  </div>
                  <h1 className="text-3xl font-serif font-bold">{masterPlan.name}</h1>
                  <p className="text-stone-500 text-sm mt-1">
                    Host: {masterPlan.owner_name} • {masterPlan.city_tier} • {masterPlan.guest_count} Guests • Total Budget: {formatINR(masterPlan.total_budget)}
                  </p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => window.print()}
                    className="px-5 py-2.5 rounded-full border border-stone-300 dark:border-stone-700 text-xs font-semibold hover:bg-stone-100 dark:hover:bg-stone-800"
                  >
                    Print Itinerary
                  </button>
                  <Link
                    href="/"
                    className="px-6 py-2.5 rounded-full bg-stone-900 text-white dark:bg-haldi dark:text-stone-950 text-xs font-semibold shadow-sm hover:opacity-90"
                  >
                    Open Live Command
                  </Link>
                </div>
              </div>

              {/* Sub-Events Timeline */}
              <div className="mt-8">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-marigold mb-4">
                  Multi-Day Sub-Events Schedule (DAG Resolved)
                </h3>
                <div className="grid sm:grid-cols-2 gap-4">
                  {masterPlan.sub_events.map((se) => (
                    <div key={se.id} className="p-5 rounded-2xl bg-white dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800 relative">
                      {se.is_muhurat_locked && (
                        <span className="absolute top-4 right-4 px-2.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 text-xs font-bold font-mono">
                          🕉️ Muhurat Locked
                        </span>
                      )}
                      <h4 className="font-semibold text-base mb-1">{se.name}</h4>
                      <div className="text-xs text-stone-500 mb-2">
                        {new Date(se.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date(se.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                      <div className="text-xs text-stone-600 dark:text-stone-400">
                        📍 Venue: {se.venue_name} {se.is_outdoor ? '(Outdoor)' : '(Indoor)'}
                      </div>
                      {se.muhurat_notes && (
                        <div className="mt-2 text-xs text-marigold font-medium">
                          {se.muhurat_notes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Itemized Budget Breakdown */}
              <div className="mt-8">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-marigold mb-4">
                  Itemized Budget Allocations (Exact Cents Arithmetic)
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {masterPlan.budget_breakdown.map((b) => (
                    <div key={b.id} className="p-4 rounded-xl bg-stone-50 dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
                      <div className="text-xs text-stone-400 capitalize">{b.name} ({b.percentage}%)</div>
                      <div className="font-bold text-sm mt-1">{formatINR(b.planned_amount)}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Scheduled Tasks */}
              <div className="mt-8">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-marigold mb-4">
                  Critical Path Milestones (DAG Scheduled)
                </h3>
                <div className="space-y-2">
                  {masterPlan.tasks.map((task) => (
                    <div key={task.id} className="p-3.5 rounded-xl bg-white dark:bg-stone-900/40 border border-stone-200 dark:border-stone-800 flex items-center justify-between text-xs">
                      <span className="font-medium text-stone-800 dark:text-stone-200">{task.title}</span>
                      <div className="flex items-center space-x-3 text-stone-500">
                        <span className="px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800 font-mono">{task.assigned_role}</span>
                        <span className="font-semibold text-kumkum dark:text-haldi">
                          {task.scheduled_start ? new Date(task.scheduled_start).toLocaleDateString() : 'Pending'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8">
                <ElderDisclaimerBanner customText={masterPlan.elder_verification_disclaimer} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
