"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { Interactive3DCard } from "./Interactive3DCard";

export function HeroChaosToComposed() {
  const [isComposed, setIsComposed] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(
      mediaQuery.matches ||
        document.documentElement.classList.contains("reduced-motion"),
    );

    const handler = (e: MediaQueryListEvent) => {
      setReducedMotion(
        e.matches ||
          document.documentElement.classList.contains("reduced-motion"),
      );
    };
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  return (
    <section className="relative w-full max-w-6xl mx-auto px-4 sm:px-6 pt-6 pb-20 overflow-hidden">
      {/* Background festive glow */}
      <div
        className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gradient-to-r from-amber-500/15 via-rose-500/10 to-amber-400/15 rounded-full blur-3xl pointer-events-none -z-10 animate-diya-halo"
        aria-hidden="true"
      />

      {/* Hero Badge */}
      <div className="flex justify-center mb-6">
        <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs font-semibold shadow-xs">
          <span
            className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"
            aria-hidden="true"
          ></span>
          <span>GenAI Operating System for Indian Celebrations</span>
        </div>
      </div>

      {/* Main Headline */}
      <div className="text-center max-w-4xl mx-auto mb-8">
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-serif font-bold tracking-tight text-stone-900 dark:text-stone-50 leading-[1.12] mb-6">
          Indian Celebrations, <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#8B1E28] via-[#D97706] to-[#B45309] dark:from-[#FF8F9B] dark:via-[#FBBF24] dark:to-[#F59E0B]">
            Harmoniously Composed.
          </span>
        </h1>
        <p className="max-w-2xl mx-auto text-base sm:text-lg text-stone-600 dark:text-stone-300 font-normal leading-relaxed">
          From 15 noisy WhatsApp groups, surprise 25% vendor markups, and
          forgotten ritual samagri — to one calm, culture-native orchestration
          engine.
        </p>
      </div>

      {/* Interactive 3D Transformation Stage */}
      <div className="my-10">
        {/* Toggle Control */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-8">
          <div className="inline-flex items-center p-1 rounded-2xl bg-stone-200/80 dark:bg-stone-800/80 border border-stone-300/80 dark:border-stone-700 shadow-inner">
            <button
              type="button"
              onClick={() => setIsComposed(false)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                !isComposed
                  ? "bg-white dark:bg-stone-900 text-rose-700 dark:text-rose-400 shadow-xs"
                  : "text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-200"
              }`}
            >
              <span className="inline-flex items-center space-x-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>The Planning Chaos</span>
              </span>
            </button>
            <button
              type="button"
              onClick={() => setIsComposed(true)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                isComposed
                  ? "bg-[#8B1E28] text-white dark:bg-[#F4B41A] dark:text-stone-950 shadow-md"
                  : "text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-200"
              }`}
            >
              <span className="inline-flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Utsav Composed Solution</span>
              </span>
            </button>
          </div>

          <button
            type="button"
            onClick={() => setIsComposed((prev) => !prev)}
            className="text-xs text-stone-700 dark:text-stone-300 hover:text-stone-900 dark:hover:text-stone-100 inline-flex items-center space-x-1 underline underline-offset-4"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Click to toggle state</span>
          </button>
        </div>

        {/* 3D Scene Viewport */}
        <div className="relative min-h-[460px] sm:min-h-[420px] w-full max-w-4xl mx-auto perspective-1000">
          {!isComposed ? (
            /* CHAOS STATE: Scattered 3D cards representing real pain points */
            <div
              className={`relative w-full h-full min-h-[440px] preserve-3d transition-all duration-700 ${reducedMotion ? "" : "sm:scale-95"}`}
            >
              {/* Chaos Card 1: WhatsApp Panic */}
              <div
                className={`absolute top-0 left-0 sm:left-4 max-w-[310px] sm:max-w-xs p-4 rounded-2xl bg-white/95 dark:bg-stone-900/95 border-2 border-rose-300 dark:border-rose-900/80 shadow-xl transition-all duration-500 preserve-3d ${
                  reducedMotion
                    ? ""
                    : "sm:-rotate-6 sm:-translate-y-2 sm:translate-z-8"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-emerald-500 text-sm font-bold">
                      💬 WhatsApp (37 unread)
                    </span>
                  </div>
                  <span className="text-[10px] bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-400 px-2 py-0.5 rounded-full font-bold">
                    URGENT
                  </span>
                </div>
                <p className="text-xs text-stone-700 dark:text-stone-300 italic mb-2">
                  “Panditji says Abhijit Muhurat is at 11:30 sharp! But Caterer
                  says lunch counter won’t open before 1 PM! Also, who confirmed
                  the Dholwala??”
                </p>
                <div className="text-[10px] text-stone-600 dark:text-stone-400 font-medium flex items-center justify-between">
                  <span>Mami (Wedding Group #4)</span>
                  <span>10:48 PM</span>
                </div>
              </div>

              {/* Chaos Card 2: Surprise Vendor Markup */}
              <div
                className={`absolute top-28 sm:top-8 right-0 sm:right-6 max-w-[320px] sm:max-w-sm p-4 rounded-2xl bg-amber-50/95 dark:bg-stone-900/95 border-2 border-amber-400 dark:border-amber-700/80 shadow-xl transition-all duration-500 preserve-3d ${
                  reducedMotion
                    ? ""
                    : "sm:rotate-4 sm:translate-y-4 sm:translate-z-12"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-amber-900 dark:text-amber-300">
                    📄 Vendor Quote: Decorator
                  </span>
                  <span className="text-[10px] bg-amber-200 dark:bg-amber-950 text-amber-800 dark:text-amber-300 px-2 py-0.5 rounded-full font-semibold">
                    Unitemized
                  </span>
                </div>
                <div className="font-mono text-sm font-bold text-stone-900 dark:text-stone-100 mb-1">
                  Tent & Stage: ₹4,50,000
                </div>
                <div className="p-2 rounded-lg bg-rose-100/90 dark:bg-rose-950/80 border border-rose-300 dark:border-rose-800 text-[11px] text-rose-950 dark:text-rose-200 font-medium">
                  ⚠️ Surprise fine print: Generator diesel, extra lights past 10
                  PM, and breakage deposits NOT included (Typical +₹85,000
                  surprise).
                </div>
              </div>

              {/* Chaos Card 3: Broken Excel Sheet */}
              <div
                className={`absolute top-64 sm:top-56 left-4 sm:left-24 max-w-[310px] sm:max-w-xs p-4 rounded-2xl bg-white/95 dark:bg-stone-900/95 border-2 border-stone-300 dark:border-stone-700 shadow-xl transition-all duration-500 preserve-3d ${
                  reducedMotion ? "" : "sm:rotate-3 sm:translate-y-2"
                }`}
              >
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xs font-bold text-stone-800 dark:text-stone-200">
                    📊 Wedding_Budget_Final_v19.xlsx
                  </span>
                </div>
                <div className="font-mono text-xs space-y-1 bg-stone-100 dark:bg-stone-950 p-2 rounded">
                  <div className="flex justify-between text-stone-800 dark:text-stone-300 font-medium">
                    <span>Venue Rent:</span>
                    <span>₹6,00,000</span>
                  </div>
                  <div className="flex justify-between text-rose-950 dark:text-rose-200 font-bold">
                    <span>Catering (250p):</span>
                    <span>#REF! Error</span>
                  </div>
                  <div className="flex justify-between text-stone-900 dark:text-stone-100 font-bold border-t border-stone-300 dark:border-stone-800 pt-1">
                    <span>Total Calculated:</span>
                    <span>₹ ???</span>
                  </div>
                </div>
              </div>

              {/* Chaos Card 4: Missing Samagri Panic */}
              <div
                className={`absolute top-84 sm:top-48 right-2 sm:right-28 max-w-[280px] sm:max-w-xs p-3.5 rounded-2xl bg-orange-50/95 dark:bg-stone-900/95 border-2 border-orange-300 dark:border-orange-800 shadow-xl transition-all duration-500 preserve-3d ${
                  reducedMotion ? "" : "sm:-rotate-3 sm:translate-z-4"
                }`}
              >
                <div className="text-xs font-bold text-orange-950 dark:text-orange-300 mb-1">
                  🪔 Havan Samagri List (Handwritten)
                </div>
                <p className="text-[11px] text-stone-700 dark:text-stone-300">
                  Visited 4 shops in old city. Mango wood bought, but pure Desi
                  Cow Ghee and customized Supari still missing 24h before Vivah!
                </p>
              </div>
            </div>
          ) : (
            /* COMPOSED STATE: Clean, unified, deterministic celebration engine */
            <div
              className={`grid sm:grid-cols-2 gap-4 w-full transition-all duration-700 preserve-3d ${reducedMotion ? "" : "scale-100"}`}
            >
              {/* Composed 1: Deterministic Budget Envelopes */}
              <Interactive3DCard className="p-5 rounded-3xl glass-card border-2 border-emerald-500/50 dark:border-emerald-500/40 shadow-xl bg-white/95 dark:bg-stone-900/95">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-300 flex items-center space-x-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span>Exact Budget Envelopes</span>
                  </span>
                  <span className="text-[10px] bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 px-2 py-0.5 rounded-full font-bold">
                    100.0% Exact
                  </span>
                </div>
                <div className="font-serif text-xl font-bold text-stone-900 dark:text-stone-100 mb-2">
                  ₹15,00,000 Allocation
                </div>
                <p className="text-xs text-stone-600 dark:text-stone-400 mb-3">
                  Deterministic scaling: Catering scales per-guest; Decor adapts
                  by venue size tier; Photography & Venue contracts remain
                  fixed. Zero hidden math.
                </p>
                <div className="w-full bg-stone-200 dark:bg-stone-800 h-2 rounded-full overflow-hidden flex">
                  <div
                    className="bg-amber-500 h-full w-[35%]"
                    title="Catering: 35%"
                  />
                  <div
                    className="bg-rose-500 h-full w-[25%]"
                    title="Venue: 25%"
                  />
                  <div
                    className="bg-orange-500 h-full w-[20%]"
                    title="Decor: 20%"
                  />
                  <div
                    className="bg-emerald-500 h-full w-[20%]"
                    title="Rituals & Photo: 20%"
                  />
                </div>
              </Interactive3DCard>

              {/* Composed 2: Real Panchang Muhurat Timing */}
              <Interactive3DCard className="p-5 rounded-3xl glass-card border-2 border-amber-500/50 dark:border-amber-500/40 shadow-xl bg-white/95 dark:bg-stone-900/95">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-amber-800 dark:text-amber-300 flex items-center space-x-1.5">
                    <CheckCircle2 className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                    <span>Auspicious Muhurat</span>
                  </span>
                  <span className="text-[10px] bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 px-2 py-0.5 rounded-full font-bold">
                    Astronomical Ephem
                  </span>
                </div>
                <div className="font-serif text-xl font-bold text-stone-900 dark:text-stone-100 mb-2">
                  11:30 AM — 01:00 PM
                </div>
                <p className="text-xs text-stone-600 dark:text-stone-400 mb-2">
                  Abhijit Muhurat locked for Lagna Samaroh. Rahu Kaal window
                  strictly bypassed.
                </p>
                <div className="text-[10px] text-amber-950 dark:text-amber-200 bg-amber-50 dark:bg-amber-950/60 p-2 rounded-lg border border-amber-300 dark:border-amber-800">
                  🙏 Mandatory Safeguard: Verified for guidance. Host confirmed
                  with family Guruji before locking.
                </div>
              </Interactive3DCard>

              {/* Composed 3: Real Venue Discovery */}
              <Interactive3DCard className="p-5 rounded-3xl glass-card border-2 border-stone-300 dark:border-stone-700 shadow-xl bg-white/95 dark:bg-stone-900/95">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-stone-700 dark:text-stone-300 flex items-center space-x-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    <span>Real Directory Venue</span>
                  </span>
                  <span className="text-[10px] bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 px-2 py-0.5 rounded-full font-medium">
                    Approx Locality
                  </span>
                </div>
                <div className="font-serif text-xl font-bold text-stone-900 dark:text-stone-100 mb-1">
                  Mahalaxmi Lawns
                </div>
                <p className="text-xs text-stone-600 dark:text-stone-400">
                  Karve Nagar, Pune • 14.8 km from host centroid. Honest
                  transparency: Unrated new profile, zero fabricated reviews.
                </p>
              </Interactive3DCard>

              {/* Composed 4: Lossless 300 DPI Invitation */}
              <Interactive3DCard className="p-5 rounded-3xl glass-card border-2 border-rose-500/50 dark:border-rose-500/40 shadow-xl bg-white/95 dark:bg-stone-900/95">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-rose-950 dark:text-rose-200 flex items-center space-x-1.5">
                    <CheckCircle2 className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                    <span>Print-Quality Invitation</span>
                  </span>
                  <span className="text-[10px] bg-rose-100 dark:bg-rose-950 text-rose-950 dark:text-rose-200 px-2 py-0.5 rounded-full font-bold">
                    Flate Lossless PDF
                  </span>
                </div>
                <div className="font-serif text-xl font-bold text-stone-900 dark:text-stone-100 mb-1">
                  ॥ शुभ विवाह ॥
                </div>
                <p className="text-xs text-stone-600 dark:text-stone-400">
                  Devanagari typography, verified venue, locked muhurat. Zero
                  placeholder leaks. Digital PNG & 300 DPI PDF ready.
                </p>
              </Interactive3DCard>
            </div>
          )}
        </div>
      </div>

      {/* Main Call to Action */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-8">
        <Link
          href="/onboarding"
          className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 font-semibold text-sm tracking-wide transition-all shadow-lg active:scale-95 flex items-center justify-center space-x-2 group focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
        >
          <span>Compose Your Celebration Now</span>
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
        <Link
          href="/dashboard/vendors/quotes"
          className="w-full sm:w-auto px-7 py-4 rounded-2xl glass-card hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-800 dark:text-stone-200 font-semibold text-sm tracking-wide transition-all shadow-sm active:scale-95 border border-stone-300/80 dark:border-stone-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
        >
          Audit Real Vendor Quotes
        </Link>
      </div>
    </section>
  );
}
