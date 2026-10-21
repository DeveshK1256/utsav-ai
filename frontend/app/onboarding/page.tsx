'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ElderDisclaimerBanner } from '@/components/ui/ElderDisclaimerBanner';

interface SubEventPlan {
  name: string;
  duration: string;
  venue: string;
  is_outdoor: boolean;
  is_muhurat_locked: boolean;
  muhurat_notes?: string;
}

interface BudgetItemPlan {
  category: string;
  amount: number;
  percentage: number;
}

interface TaskPlan {
  title: string;
  role: string;
  timeline: string;
}

interface GeneratedPlan {
  event_id: string;
  name: string;
  city_tier: string;
  total_budget: number;
  guest_count: number;
  sub_events: SubEventPlan[];
  budget_breakdown: BudgetItemPlan[];
  tasks: TaskPlan[];
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

const CITY_TIERS: Record<string, string> = {
  'mumbai': 'Tier 1 (1.0x)',
  'pune': 'Tier 1 (1.0x)',
  'bengaluru': 'Tier 1 (1.0x)',
  'delhi': 'Tier 1 (1.0x)',
  'hyderabad': 'Tier 1 (1.0x)',
  'jaipur': 'Tier 2 (0.68x)',
  'ahmedabad': 'Tier 2 (0.68x)',
  'lucknow': 'Tier 2 (0.68x)',
  'indore': 'Tier 2 (0.68x)',
  'chandigarh': 'Tier 2 (0.68x)'
};

export default function OnboardingPage() {
  const [step, setStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [generatedPlan, setGeneratedPlan] = useState<GeneratedPlan | null>(null);

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

  const cityLower = formData.city.toLowerCase().trim();
  const tierLabel = CITY_TIERS[cityLower] || 'Tier 2 (0.68x)';
  const multiplier = cityLower.includes('mumbai') || cityLower.includes('pune') || cityLower.includes('bengaluru') || cityLower.includes('delhi') ? 1.0 : 0.68;
  const effectiveBudget = formData.budget * multiplier;

  const handleSynthesize = () => {
    setIsSubmitting(true);
    // Simulate deterministic engine call or real API
    setTimeout(() => {
      const syntheticPlan: GeneratedPlan = {
        event_id: 'utsav_' + Math.random().toString(36).substring(2, 9),
        name: formData.name,
        city_tier: tierLabel,
        total_budget: effectiveBudget,
        guest_count: formData.guestCount,
        sub_events: [
          {
            name: 'Haldi & Floral Mehndi Gathering',
            duration: 'Day 1 • 4:00 PM - 8:00 PM',
            venue: 'Lotus Courtyard',
            is_outdoor: true,
            is_muhurat_locked: false
          },
          {
            name: 'Sangeet & Cultural Night',
            duration: 'Day 1 • 8:30 PM - 12:30 AM',
            venue: 'Grand Heritage Ballroom',
            is_outdoor: false,
            is_muhurat_locked: false
          },
          {
            name: 'Vedic Vivah & Saptapadi',
            duration: 'Day 2 • 10:30 AM - 1:30 PM',
            venue: 'Mandap Sanctum Hall',
            is_outdoor: false,
            is_muhurat_locked: true,
            muhurat_notes: 'Calculated auspicious window: 10:42 AM - 12:15 PM'
          },
          {
            name: 'Celebratory Gala Reception',
            duration: 'Day 2 • 7:30 PM - 11:30 PM',
            venue: 'Palace Royal Lawn',
            is_outdoor: true,
            is_muhurat_locked: false
          }
        ],
        budget_breakdown: [
          { category: 'Catering & Hospitality', amount: effectiveBudget * 0.28, percentage: 28 },
          { category: 'Venue & Banquets', amount: effectiveBudget * 0.22, percentage: 22 },
          { category: 'Floral & Mandap Decor', amount: effectiveBudget * 0.16, percentage: 16 },
          { category: 'Cinematic Photography', amount: effectiveBudget * 0.09, percentage: 9 },
          { category: 'Music & Entertainment', amount: effectiveBudget * 0.07, percentage: 7 },
          { category: 'Ritual Supplies & Panditji', amount: effectiveBudget * 0.04, percentage: 4 },
          { category: 'Contingency & Fuel Buffer', amount: effectiveBudget * 0.04, percentage: 4 }
        ],
        tasks: [
          { title: 'Lock Venue & Access Hours Contract', role: 'Host', timeline: 'T-60 Days' },
          { title: 'Finalize Per-Plate Menu & Tandoor Terms', role: 'F&B Coordinator', timeline: 'T-45 Days' },
          { title: 'Source 27 Vedic Samagri Items', role: 'Elder Lead', timeline: 'T-21 Days' },
          { title: 'Dispatch WhatsApp Concierge Invites', role: 'Guest Lead', timeline: 'T-21 Days' },
          { title: 'Solve 2D Table Seating Constraints', role: 'Host', timeline: 'T-7 Days' },
          { title: 'Issue Day-of Vendor Call-Sheets', role: 'Day-of Director', timeline: 'T-2 Days' }
        ]
      };
      setGeneratedPlan(syntheticPlan);
      setIsSubmitting(false);
      setStep(5); // Result view
    }, 1800);
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
                  <span className="absolute right-3 top-3 text-xs px-2 py-0.5 rounded-md bg-stone-100 dark:bg-stone-800 text-stone-500">
                    {tierLabel}
                  </span>
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

        {/* STEP 3: Scale & Budget Envelope */}
        {step === 3 && (
          <div className="p-8 rounded-3xl glass-card shadow-xl space-y-6">
            <div>
              <h2 className="text-2xl font-serif font-semibold mb-1">Scale & Budget Envelope</h2>
              <p className="text-stone-500 text-sm">
                Calibrated against {formData.city} ({tierLabel}). Zero guesswork or arbitrary pricing.
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

            {/* Live Computed Previews */}
            <div className="p-5 rounded-2xl bg-stone-100/70 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800">
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-3">
                Computed Baseline Allocation for {formData.city}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-white dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
                  <div className="text-xs text-stone-400">Catering (28%)</div>
                  <div className="font-bold text-sm mt-1">{formatINR(effectiveBudget * 0.28)}</div>
                </div>
                <div className="p-3 rounded-xl bg-white dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
                  <div className="text-xs text-stone-400">Venue (22%)</div>
                  <div className="font-bold text-sm mt-1">{formatINR(effectiveBudget * 0.22)}</div>
                </div>
                <div className="p-3 rounded-xl bg-white dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
                  <div className="text-xs text-stone-400">Decor (16%)</div>
                  <div className="font-bold text-sm mt-1">{formatINR(effectiveBudget * 0.16)}</div>
                </div>
                <div className="p-3 rounded-xl bg-white dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
                  <div className="text-xs text-stone-400">Contingency (4%)</div>
                  <div className="font-bold text-sm mt-1">{formatINR(effectiveBudget * 0.04)}</div>
                </div>
              </div>
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

        {/* STEP 4: Review & Final Synthesis */}
        {step === 4 && (
          <div className="p-8 rounded-3xl glass-card shadow-xl space-y-6">
            <div>
              <h2 className="text-2xl font-serif font-semibold mb-1">Review Celebration Blueprint</h2>
              <p className="text-stone-500 text-sm">
                Confirm your parameters before our deterministic engines assemble the master itinerary.
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
                  <strong className="text-stone-900 dark:text-white">{formData.city} • {tierLabel}</strong>
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
                  <span className="text-stone-400 block text-xs">Budget Envelope:</span>
                  <strong className="text-stone-900 dark:text-white">{formatINR(effectiveBudget)}</strong>
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
                    <span>Composing Celebration Plan...</span>
                  </>
                ) : (
                  <span>✨ Synthesize Master Plan</span>
                )}
              </button>
            </div>
          </div>
        )}

        {/* STEP 5: Master Plan Reveal Result */}
        {step === 5 && generatedPlan && (
          <div className="space-y-8 animate-fadeIn">
            {/* Top Celebration Card */}
            <div className="p-8 rounded-3xl glass-card shadow-2xl border-2 border-haldi/60 relative overflow-hidden">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-stone-200 dark:border-stone-800">
                <div>
                  <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 text-xs font-semibold mb-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>Celebration Blueprint Synthesized</span>
                  </div>
                  <h1 className="text-3xl font-serif font-bold">{generatedPlan.name}</h1>
                  <p className="text-stone-500 text-sm mt-1">
                    {generatedPlan.city_tier} • {generatedPlan.guest_count} Guests • Total Budget: {formatINR(generatedPlan.total_budget)}
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
                  Multi-Day Sub-Events Schedule
                </h3>
                <div className="grid sm:grid-cols-2 gap-4">
                  {generatedPlan.sub_events.map((se, idx) => (
                    <div key={idx} className="p-5 rounded-2xl bg-white dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800 relative">
                      {se.is_muhurat_locked && (
                        <span className="absolute top-4 right-4 px-2.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 text-xs font-bold font-mono">
                          🕉️ Muhurat Locked
                        </span>
                      )}
                      <h4 className="font-semibold text-base mb-1">{se.name}</h4>
                      <div className="text-xs text-stone-500 mb-2">{se.duration}</div>
                      <div className="text-xs text-stone-600 dark:text-stone-400">
                        📍 Venue: {se.venue} {se.is_outdoor ? '(Outdoor Lawn)' : '(Indoor Banquet)'}
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

              {/* Itemized Budget Allocations */}
              <div className="mt-8">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-marigold mb-4">
                  Calibrated Budget Allocations
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {generatedPlan.budget_breakdown.map((b, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-stone-50 dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
                      <div className="text-xs text-stone-400">{b.category} ({b.percentage}%)</div>
                      <div className="font-bold text-sm mt-1">{formatINR(b.amount)}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Scheduled Milestones */}
              <div className="mt-8">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-marigold mb-4">
                  Critical Path Milestones (DAG Scheduled)
                </h3>
                <div className="space-y-2">
                  {generatedPlan.tasks.map((task, idx) => (
                    <div key={idx} className="p-3.5 rounded-xl bg-white dark:bg-stone-900/40 border border-stone-200 dark:border-stone-800 flex items-center justify-between text-xs">
                      <span className="font-medium text-stone-800 dark:text-stone-200">{task.title}</span>
                      <div className="flex items-center space-x-3 text-stone-500">
                        <span className="px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800 font-mono">{task.role}</span>
                        <span className="font-semibold text-kumkum dark:text-haldi">{task.timeline}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8">
                <ElderDisclaimerBanner />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
