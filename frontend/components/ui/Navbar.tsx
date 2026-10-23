'use client';

import React from 'react';
import Link from 'next/link';
import { ThemeToggle } from './ThemeToggle';

interface NavbarProps {
  badge?: string;
  rightAction?: React.ReactNode;
}

export function Navbar({ badge, rightAction }: NavbarProps) {
  return (
    <header className="sticky top-0 left-0 right-0 z-50 glass-card border-b border-stone-200/70 dark:border-stone-800/80 transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 sm:h-18 flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#8B1E28] via-[#E67E22] to-[#F4B41A] flex items-center justify-center text-white font-devanagari text-xl shadow-md group-hover:scale-105 transition-transform duration-200">
            उ
          </div>
          <div className="flex items-center">
            <span className="text-xl font-serif font-bold tracking-wider text-stone-900 dark:text-stone-50">
              UTSAV
            </span>
            {badge ? (
              <span className="text-xs ml-2 px-2.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/70 border border-amber-300 dark:border-amber-800 text-amber-800 dark:text-amber-300 font-semibold uppercase tracking-wider">
                {badge}
              </span>
            ) : (
              <span className="text-xs ml-1.5 text-amber-600 dark:text-amber-400 font-semibold tracking-widest uppercase">
                उत्सव AI
              </span>
            )}
          </div>
        </Link>

        <div className="flex items-center space-x-3">
          {rightAction}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
