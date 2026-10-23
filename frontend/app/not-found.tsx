'use client';

import React from 'react';
import Link from 'next/link';
import { Navbar } from '@/components/ui/Navbar';

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar badge="404" />

      <main className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="glass-card rounded-3xl p-8 sm:p-12 max-w-md text-center shadow-xl">
          <div className="w-16 h-16 rounded-2xl bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 flex items-center justify-center text-3xl mx-auto mb-5 shadow-sm">
            🪔
          </div>
          <h1 className="text-3xl font-serif font-bold text-stone-900 dark:text-stone-50 mb-2">
            Page Not Found
          </h1>
          <p className="text-stone-600 dark:text-stone-300 text-sm mb-8 leading-relaxed">
            The celebration path you are looking for has either concluded or hasn’t been composed yet.
          </p>

          <Link
            href="/"
            className="px-6 py-3 rounded-full bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 text-xs font-bold uppercase tracking-wider transition-all shadow-md active:scale-95 inline-block"
          >
            ← Return to Celebration Home
          </Link>
        </div>
      </main>
    </div>
  );
}
