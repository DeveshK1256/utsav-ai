'use client';

import React from 'react';
import Link from 'next/link';
import { ElderDisclaimerBanner } from '@/components/ui/ElderDisclaimerBanner';

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-card border-b border-stone-200/60 dark:border-stone-800">
        <div className="max-w-7xl mx-auto px-6 h-18 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#8B1E28] via-[#E67E22] to-[#F4B41A] flex items-center justify-center text-white font-serif text-xl shadow-md">
              उ
            </div>
            <div>
              <span className="text-xl font-serif font-bold tracking-wider">UTSAV</span>
              <span className="text-xs ml-1 text-amber-600 font-semibold tracking-widest uppercase">उत्सव AI</span>
            </div>
          </div>
          <Link
            href="/onboarding"
            className="px-6 py-2.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-stone-900 text-white dark:bg-[#F4B41A] dark:text-stone-950 hover:opacity-90 transition-all shadow-sm"
          >
            Compose Celebration
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-40 pb-24 px-6 text-center max-w-5xl mx-auto">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-amber-100/70 dark:bg-amber-950/40 border border-amber-300 text-amber-900 dark:text-amber-300 text-xs font-semibold mb-8">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
          <span>GenAI Operating System for Indian Celebrations</span>
        </div>

        <h1 className="text-4xl md:text-7xl font-serif font-semibold tracking-tight leading-tight mb-6">
          Celebrations, <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#8B1E28] via-[#E67E22] to-[#C69214]">
            Composed.
          </span>
        </h1>

        <p className="max-w-2xl mx-auto text-lg md:text-xl text-stone-600 dark:text-stone-300 font-light mb-10 leading-relaxed">
          Say goodbye to 15 fragmented WhatsApp groups, surprise 25% vendor markups, and forgotten ritual samagri.
          Utsav is your 24/7 autonomous celebration director.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/onboarding"
            className="w-full sm:w-auto px-8 py-4 rounded-full bg-[#8B1E28] text-white hover:bg-stone-900 dark:hover:bg-[#F4B41A] dark:hover:text-stone-950 font-medium text-sm tracking-wide transition-all shadow-lg"
          >
            Launch Conversational Intake Studio →
          </Link>
        </div>

        <div className="mt-14 max-w-2xl mx-auto text-left">
          <ElderDisclaimerBanner />
        </div>
      </section>
    </div>
  );
}
