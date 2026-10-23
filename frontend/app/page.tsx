'use client';

import React from 'react';
import Link from 'next/link';
import { Navbar } from '@/components/ui/Navbar';
import { ElderDisclaimerBanner } from '@/components/ui/ElderDisclaimerBanner';

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Navigation with Theme Toggle */}
      <Navbar
        rightAction={
          <Link
            href="/onboarding"
            className="px-5 py-2 rounded-full text-xs font-semibold tracking-wider uppercase bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 transition-all shadow-sm active:scale-95"
          >
            Compose Celebration
          </Link>
        }
      />

      {/* Hero Section */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 pt-16 pb-20 text-center">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-amber-100/80 dark:bg-amber-950/60 border border-amber-300/80 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs font-semibold mb-8 shadow-sm">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
          <span>GenAI Operating System for Indian Celebrations</span>
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-serif font-bold tracking-tight leading-[1.15] mb-6 text-stone-900 dark:text-stone-50">
          Celebrations, <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#8B1E28] via-[#E67E22] to-[#C69214] dark:from-[#E05263] dark:via-[#F59E0B] dark:to-[#F4B41A]">
            Composed.
          </span>
        </h1>

        <p className="max-w-2xl mx-auto text-base sm:text-lg text-stone-600 dark:text-stone-300 font-normal mb-10 leading-relaxed">
          Say goodbye to 15 fragmented WhatsApp groups, surprise 25% vendor markups, and forgotten ritual samagri.
          Utsav is your 24/7 autonomous cultural celebration director.
        </p>

        {/* Primary CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <Link
            href="/onboarding"
            className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-[#8B1E28] hover:bg-[#6e151e] text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 font-semibold text-sm tracking-wide transition-all shadow-lg active:scale-95 flex items-center justify-center space-x-2"
          >
            <span>Launch Conversational Intake Studio</span>
            <span>→</span>
          </Link>
          <Link
            href="/dashboard/vendors/quotes"
            className="w-full sm:w-auto px-7 py-4 rounded-2xl glass-card hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-800 dark:text-stone-200 font-semibold text-sm tracking-wide transition-all shadow-sm active:scale-95 border border-stone-300/80 dark:border-stone-700"
          >
            Audit Vendor Quotes
          </Link>
        </div>

        {/* Core Feature Bento Grid */}
        <div className="grid sm:grid-cols-3 gap-6 max-w-5xl mx-auto text-left mb-16">
          <Link
            href="/onboarding"
            className="p-6 rounded-3xl glass-card hover:border-amber-400/60 dark:hover:border-amber-500/50 transition-all group shadow-sm hover:shadow-md"
          >
            <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-950/80 flex items-center justify-center text-xl mb-4 group-hover:scale-110 transition-transform">
              ✨
            </div>
            <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100 mb-2">
              Intake Studio
            </h3>
            <p className="text-xs sm:text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
              Synthesize regional Vedic schedules, budget envelopes, and sub-event timelines in seconds with deterministic math.
            </p>
          </Link>

          <Link
            href="/dashboard/vendors/quotes"
            className="p-6 rounded-3xl glass-card hover:border-rose-400/60 dark:hover:border-rose-500/50 transition-all group shadow-sm hover:shadow-md"
          >
            <div className="w-10 h-10 rounded-xl bg-rose-100 dark:bg-rose-950/80 flex items-center justify-center text-xl mb-4 group-hover:scale-110 transition-transform">
              📑
            </div>
            <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100 mb-2">
              Hidden-Cost Detector
            </h3>
            <p className="text-xs sm:text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
              Upload PDF or image quotes. Gemini extracts line items while deterministic checks benchmark costs & flag missing generator fuel/GST.
            </p>
          </Link>

          <Link
            href="/dashboard/events/default/vibe"
            className="p-6 rounded-3xl glass-card hover:border-orange-400/60 dark:hover:border-orange-500/50 transition-all group shadow-sm hover:shadow-md"
          >
            <div className="w-10 h-10 rounded-xl bg-orange-100 dark:bg-orange-950/80 flex items-center justify-center text-xl mb-4 group-hover:scale-110 transition-transform">
              🎨
            </div>
            <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100 mb-2">
              Vibe-to-Plan
            </h3>
            <p className="text-xs sm:text-sm text-stone-600 dark:text-stone-400 leading-relaxed">
              Upload moodboard inspiration photos. Multimodal AI extracts cultural palettes, generated collages, and itemized decor estimates.
            </p>
          </Link>
        </div>

        {/* Mandatory Elder Verification Banner */}
        <div className="max-w-2xl mx-auto text-left">
          <ElderDisclaimerBanner />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-stone-200/80 dark:border-stone-800/80 py-8 text-center text-xs text-stone-500 dark:text-stone-400">
        <p>© 2026 Utsav AI. Composed with respect for Indian heritage traditions.</p>
      </footer>
    </div>
  );
}
