'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Calculator, 
  FileSearch, 
  Sun, 
  Mail, 
  Check, 
  AlertCircle, 
  ArrowRight,
  ShieldCheck,
  Compass
} from 'lucide-react';
import { Interactive3DCard } from './Interactive3DCard';

export function FeatureShowcase3D() {
  const [reducedMotion, setReducedMotion] = useState(false);

  // Feature 1: Budget Rescaler State
  const [guestCount, setGuestCount] = useState<number>(200);
  const baseBudget = 1500000;
  // Catering scales per-guest from baseline 200 guests (₹5,00,000 baseline)
  const cateringAmount = Math.round(500000 * (guestCount / 200));
  // Decor tiered: <=150: 250k, 151-250: 320k, >250: 420k
  const decorAmount = guestCount <= 150 ? 250000 : guestCount <= 250 ? 320000 : 420000;
  const venueFixed = 400000;
  const photoFixed = 150000;
  const ritualsFixed = 130000;
  const calculatedTotal = cateringAmount + decorAmount + venueFixed + photoFixed + ritualsFixed;

  // Feature 2: Quote Scanner State
  const [isScanning, setIsScanning] = useState(false);
  const [scanComplete, setScanComplete] = useState(false);

  const runScan = () => {
    setIsScanning(true);
    setScanComplete(false);
    setTimeout(() => {
      setIsScanning(false);
      setScanComplete(true);
    }, reducedMotion ? 100 : 1200);
  };

  // Feature 3: Tradition Fusion State
  const [traditionA, setTraditionA] = useState('maharashtrian_vedic');
  const [traditionB, setTraditionB] = useState('punjabi_anand_karaj');

  // Feature 4: Invitation Card Variant
  const [selectedLayout, setSelectedLayout] = useState<'classic_arch' | 'royal_floral' | 'modern_minimalist'>('classic_arch');

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches || document.documentElement.classList.contains('reduced-motion'));

    const handler = (e: MediaQueryListEvent) => {
      setReducedMotion(e.matches || document.documentElement.classList.contains('reduced-motion'));
    };
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return (
    <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 py-16 space-y-28">
      
      {/* =========================================================================
          FEATURE 1: Deterministic Budget Rescaling Engine (F1 & F18)
          ========================================================================= */}
      <section className="grid lg:grid-cols-2 gap-10 items-center">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-800 dark:text-emerald-300 text-xs font-semibold mb-4">
            <Calculator className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>Milestone M1 • DEC-018</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-stone-900 dark:text-stone-50 mb-4">
            Deterministic Budget Math. <br />
            <span className="text-emerald-700 dark:text-emerald-400">Zero Hallucinated Totals.</span>
          </h2>
          <p className="text-stone-600 dark:text-stone-300 text-sm sm:text-base leading-relaxed mb-6">
            Generic LLMs guess percentages that don&apos;t add up to 100%. Utsav uses a strict deterministic engine: Catering scales per-guest, Decor adapts in tiered venue brackets, and contracted categories remain fixed.
          </p>
          <div className="p-4 rounded-2xl bg-stone-100/80 dark:bg-stone-900/80 border border-stone-200 dark:border-stone-800 mb-6">
            <label htmlFor="guest-slider" className="flex justify-between items-center text-xs font-bold text-stone-800 dark:text-stone-200 mb-2">
              <span>Simulate Guest Surge (Interactive 3D):</span>
              <span className="text-emerald-700 dark:text-emerald-400 font-mono text-sm">{guestCount} Guests</span>
            </label>
            <input
              id="guest-slider"
              type="range"
              min="100"
              max="350"
              step="10"
              value={guestCount}
              onChange={(e) => setGuestCount(parseInt(e.target.value, 10))}
              className="w-full h-2 bg-stone-300 dark:bg-stone-700 rounded-lg appearance-none cursor-pointer accent-emerald-600"
            />
            <div className="flex justify-between text-[10px] text-stone-700 dark:text-stone-300 mt-1 font-mono font-medium">
              <span>100 (Intimate)</span>
              <span>200 (Baseline)</span>
              <span>350 (Grand Vivah)</span>
            </div>
          </div>
          <Link
            href="/onboarding"
            className="inline-flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 hover:text-emerald-800 dark:hover:text-emerald-300 group focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          >
            <span>Explore Custom Budget Allocation</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        {/* 3D Dynamic Budget Breakdown Card */}
        <Interactive3DCard className="p-6 sm:p-8 rounded-3xl glass-card border border-emerald-500/30 shadow-2xl bg-white/95 dark:bg-stone-900/95">
          <div className="flex items-center justify-between border-b border-stone-200 dark:border-stone-800 pb-4 mb-4">
            <div>
              <div className="text-[10px] uppercase font-bold text-stone-600 dark:text-stone-300 tracking-wider">Live Calculated Total</div>
              <div className="font-serif text-2xl sm:text-3xl font-bold text-stone-900 dark:text-stone-100">
                ₹{calculatedTotal.toLocaleString('en-IN')}
              </div>
            </div>
            <span className="px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 text-xs font-mono font-bold">
              100.0% Exact
            </span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            {/* Catering item */}
            <div className="p-2.5 rounded-xl bg-stone-50 dark:bg-stone-950/80 border border-stone-200 dark:border-stone-800 flex justify-between items-center">
              <div>
                <span className="font-bold text-stone-900 dark:text-stone-100">Catering (Per-Guest)</span>
                <span className="block text-[10px] text-stone-700 dark:text-stone-300">Formula: ₹5,00,000 * ({guestCount}/200)</span>
              </div>
              <div className="text-right">
                <span className="font-bold text-emerald-800 dark:text-emerald-300">₹{cateringAmount.toLocaleString('en-IN')}</span>
                <span className="block text-[9px] text-emerald-800 dark:text-emerald-300 font-medium">Linear scaling</span>
              </div>
            </div>

            {/* Decor item */}
            <div className="p-2.5 rounded-xl bg-stone-50 dark:bg-stone-950/80 border border-stone-200 dark:border-stone-800 flex justify-between items-center">
              <div>
                <span className="font-bold text-stone-900 dark:text-stone-100">Decor (Tiered Space)</span>
                <span className="block text-[10px] text-stone-700 dark:text-stone-300">
                  {guestCount <= 150 ? 'Tier: Intimate (<150)' : guestCount <= 250 ? 'Tier: Standard (151-250)' : 'Tier: Grand Lawn (>250)'}
                </span>
              </div>
              <div className="text-right">
                <span className="font-bold text-amber-800 dark:text-amber-300">₹{decorAmount.toLocaleString('en-IN')}</span>
                <span className="block text-[9px] text-amber-800 dark:text-amber-300 font-medium">Tier bracket</span>
              </div>
            </div>

            {/* Fixed items */}
            <div className="p-2.5 rounded-xl bg-stone-50 dark:bg-stone-950/80 border border-stone-200 dark:border-stone-800 flex justify-between items-center">
              <div>
                <span className="font-bold text-stone-900 dark:text-stone-100">Venue Rental (Contracted)</span>
                <span className="block text-[10px] text-stone-700 dark:text-stone-300">Fixed rate — invariant to guest count</span>
              </div>
              <div className="text-right">
                <span className="font-bold text-stone-800 dark:text-stone-200">₹{venueFixed.toLocaleString('en-IN')}</span>
                <span className="block text-[9px] text-stone-700 dark:text-stone-300 font-medium">Fixed (Δ 0.0)</span>
              </div>
            </div>
          </div>
        </Interactive3DCard>
      </section>


      {/* =========================================================================
          FEATURE 2: Hidden Cost Radar & Quote Auditor (F5)
          ========================================================================= */}
      <section className="grid lg:grid-cols-2 gap-10 items-center">
        {/* 3D Holographic Quote Scanner Card */}
        <Interactive3DCard className="relative p-6 sm:p-8 rounded-3xl glass-card border border-rose-500/30 shadow-2xl bg-white/95 dark:bg-stone-900/95 order-2 lg:order-1">
          {/* Scanning Beam (animated when scanning) */}
          {isScanning && !reducedMotion && (
            <div 
              className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-rose-500 to-transparent blur-xs z-20 animate-bounce"
              style={{ top: '40%' }}
              aria-hidden="true"
            />
          )}

          <div className="flex items-center justify-between mb-4 border-b border-stone-200 dark:border-stone-800 pb-3">
            <div className="flex items-center space-x-2">
              <FileSearch className="w-5 h-5 text-rose-600 dark:text-rose-400" />
              <span className="font-bold text-stone-900 dark:text-stone-100 text-sm">Vendor Quote: Royal Caterers</span>
            </div>
            <button
              type="button"
              onClick={runScan}
              disabled={isScanning}
              className="px-3 py-1 rounded-full text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition-all shadow-xs disabled:opacity-50"
            >
              {isScanning ? 'Auditing...' : 'Run Holographic Audit'}
            </button>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 rounded-xl bg-stone-50 dark:bg-stone-950/80 border border-stone-200 dark:border-stone-800">
              <div className="flex justify-between text-stone-800 dark:text-stone-200 font-bold mb-1">
                <span>Rajasthani Royal Thali (250 plates)</span>
                <span>₹2,50,000</span>
              </div>
              <div className="text-[10px] text-stone-600 dark:text-stone-300">Unit rate: ₹1,000 / plate • Tier-1 Median: ₹1,150 (Fair)</div>
            </div>

            {/* Hidden Cost Detection Tags */}
            <div className={`space-y-2 transition-opacity duration-300 ${scanComplete || isScanning ? 'opacity-100' : 'opacity-70'}`}>
              <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200 text-xs flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-rose-950 dark:text-rose-100">Missing: Crockery & Cutlery Breakage</span>
                  <span className="block text-[11px] text-rose-950 dark:text-rose-200">
                    Quote mentions no replacement limit. Typical post-event shock: +₹25,000.
                  </span>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-amber-950 dark:text-amber-100">Ambiguous: Staff Overtime Past Midnight</span>
                  <span className="block text-[11px] text-amber-950 dark:text-amber-200">
                    Banquets typically run until 1:30 AM. Suggested ask: &quot;Fix ₹3,000/hr cap in contract.&quot;
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Interactive3DCard>

        <div className="order-1 lg:order-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-800 dark:text-rose-300 text-xs font-semibold mb-4">
            <FileSearch className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
            <span>Milestone M1 • DEC-014 / DEC-017</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-stone-900 dark:text-stone-50 mb-4">
            The Hidden-Cost Radar. <br />
            <span className="text-rose-700 dark:text-rose-400">Never Sign a Blind Quote.</span>
          </h2>
          <p className="text-stone-600 dark:text-stone-300 text-sm sm:text-base leading-relaxed mb-6">
            Vendors often omit generator fuel, service staff overtime, and crockery breakage from initial estimates. Utsav scans your uploaded PDF or JPEG quote, flags missing clauses, and benchmarks rates against real city-tier medians.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href="/dashboard/vendors/quotes"
              className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-[#8B1E28] text-white hover:bg-stone-900 font-semibold text-xs tracking-wider uppercase transition-all shadow-md active:scale-95"
            >
              Audit A Vendor Quote Free
            </Link>
          </div>
        </div>
      </section>


      {/* =========================================================================
          FEATURE 3: Astronomical Panchang & Ritual Intelligence (M5 & F2)
          ========================================================================= */}
      <section className="grid lg:grid-cols-2 gap-10 items-center">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 text-xs font-semibold mb-4">
            <Sun className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            <span>Milestone M5 • DEC-027</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-stone-900 dark:text-stone-50 mb-4">
            Astronomical Panchang. <br />
            <span className="text-amber-700 dark:text-amber-400">Respectful Cultural Harmony.</span>
          </h2>
          <p className="text-stone-600 dark:text-stone-300 text-sm sm:text-base leading-relaxed mb-6">
            Computed directly via astronomical ephemeris for exact lat/long coordinates. Avoids Rahu Kaal, identifies auspicious Abhijit Muhurat, and provides curated samagri checklists for 8+ regional traditions.
          </p>
          
          {/* Elder Consultation Guarantee Banner */}
          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-900 dark:text-amber-200 mb-6 flex items-start space-x-3">
            <ShieldCheck className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block mb-1">Mandatory Elder & Priest Consultation Safeguard (DEC-009)</span>
              Utsav provides astronomical calculation guidance, never absolute religious dogma. All muhurats and fusion timelines are marked for family elder and priest confirmation.
            </div>
          </div>
        </div>

        {/* 3D Celestial Dial / Fusion Card */}
        <Interactive3DCard className="p-6 sm:p-8 rounded-3xl glass-card border border-amber-500/30 shadow-2xl bg-white/95 dark:bg-stone-900/95">
          <div className="flex items-center justify-between mb-4 border-b border-stone-200 dark:border-stone-800 pb-3">
            <div className="flex items-center space-x-2">
              <Compass className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              <span className="font-bold text-stone-900 dark:text-stone-100 text-sm">Cross-Tradition Fusion Merging</span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 font-bold">
              Conflict-Free
            </span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2.5 rounded-xl bg-stone-100 dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
                <span className="text-[10px] text-stone-700 dark:text-stone-300 block font-medium">Primary Tradition</span>
                <span className="font-bold text-stone-900 dark:text-stone-100">Maharashtrian Vedic</span>
              </div>
              <div className="p-2.5 rounded-xl bg-stone-100 dark:bg-stone-950 border border-stone-200 dark:border-stone-800">
                <span className="text-[10px] text-stone-700 dark:text-stone-300 block font-medium">Secondary Tradition</span>
                <span className="font-bold text-stone-900 dark:text-stone-100">Punjabi Anand Karaj</span>
              </div>
            </div>

            <div className="p-3 rounded-2xl bg-stone-50 dark:bg-stone-950/80 border border-stone-200 dark:border-stone-800 space-y-2">
              <div className="text-[11px] font-bold text-stone-900 dark:text-stone-100 flex items-center justify-between">
                <span>Unified Run-of-Show:</span>
                <span className="text-emerald-800 dark:text-emerald-300 font-semibold text-[10px]">Harmonized DAG</span>
              </div>
              <div className="space-y-1.5 text-[11px] text-stone-700 dark:text-stone-300">
                <div className="flex items-center space-x-2">
                  <span className="text-amber-800 dark:text-amber-300 font-bold">09:00 AM</span>
                  <span>Sakharpuda & Chooda Ceremony (Non-overlapping)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-emerald-800 dark:text-emerald-300 font-bold">11:30 AM</span>
                  <span className="font-bold text-stone-900 dark:text-stone-100">Lagna Samaroh (Abhijit Muhurat Locked)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-amber-800 dark:text-amber-300 font-bold">07:00 PM</span>
                  <span>Grand Sangeet & Milni Reception</span>
                </div>
              </div>
            </div>
          </div>
        </Interactive3DCard>
      </section>


      {/* =========================================================================
          FEATURE 4: Lossless 3D Invitation Studio (M10 & F16)
          ========================================================================= */}
      <section className="grid lg:grid-cols-2 gap-10 items-center">
        {/* 3D Tactile Invitation Card */}
        <Interactive3DCard className="relative p-6 sm:p-8 rounded-3xl glass-card border border-rose-500/30 shadow-2xl bg-white/95 dark:bg-stone-900/95 order-2 lg:order-1">
          {/* Card Frame with Gold Rim */}
          <div className="p-6 rounded-2xl border-2 border-amber-400/70 dark:border-amber-500/60 bg-gradient-to-br from-amber-50/80 via-white to-rose-50/80 dark:from-stone-900 dark:via-stone-900 dark:to-stone-950 text-center shadow-lg">
            <div className="text-xs uppercase tracking-widest text-amber-800 dark:text-amber-300 font-serif font-bold mb-1">
              ॥ श्री गणेशाय नमः ॥
            </div>
            <div className="font-serif text-2xl font-bold text-stone-900 dark:text-stone-100 mb-1">
              Aarav & Meera Vivah
            </div>
            <div className="text-xs text-stone-600 dark:text-stone-400 mb-4">
              With the blessings of our elders, we invite you to celebrate.
            </div>

            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-950 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs font-semibold mb-4">
              <Sun className="w-3.5 h-3.5" />
              <span>Abhijit Muhurat: 11:30 AM</span>
            </div>

            <div className="text-xs text-stone-700 dark:text-stone-300 border-t border-stone-200 dark:border-stone-800 pt-3">
              📍 Mahalaxmi Lawns, Karve Nagar, Pune
            </div>

            <div className="mt-4 flex justify-center space-x-2 text-[10px] font-mono text-stone-800 dark:text-stone-200 font-medium">
              <span className="px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800">FlateDecode Lossless</span>
              <span className="px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800">300 DPI Print</span>
              <span className="px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800">Digital PNG</span>
            </div>
          </div>
        </Interactive3DCard>

        <div className="order-1 lg:order-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-800 dark:text-rose-300 text-xs font-semibold mb-4">
            <Mail className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
            <span>Milestone M10 • DEC-028 / DEC-030</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-serif font-bold text-stone-900 dark:text-stone-50 mb-4">
            Print-Quality Lossless Cards. <br />
            <span className="text-rose-700 dark:text-rose-400">Zero Blur. Zero Placeholders.</span>
          </h2>
          <p className="text-stone-600 dark:text-stone-300 text-sm sm:text-base leading-relaxed mb-6">
            While generic generative AI produces blurry text and made-up names, Utsav renders crisp, lossless 300 DPI PDFs using Pillow and true Devanagari typography. Real confirmed venue details and locked muhurats flow straight to your cards.
          </p>
          <Link
            href="/dashboard/events/default/invitations"
            className="inline-flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-rose-700 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-300 group focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
          >
            <span>Preview Card Studio</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </section>

    </div>
  );
}
