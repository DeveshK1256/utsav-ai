'use client';

import React, { useState, useEffect } from 'react';
import { EyeOff, Play } from 'lucide-react';

export function MotionToggle() {
  const [isReduced, setIsReduced] = useState(false);

  useEffect(() => {
    // Check initial state
    const saved = localStorage.getItem('utsav_reduced_motion');
    const systemPrefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const initialReduced = saved !== null ? saved === 'true' : systemPrefersReduced;

    setIsReduced(initialReduced);
    if (initialReduced) {
      document.documentElement.classList.add('reduced-motion');
    } else {
      document.documentElement.classList.remove('reduced-motion');
    }
  }, []);

  const toggleMotion = () => {
    const nextState = !isReduced;
    setIsReduced(nextState);
    localStorage.setItem('utsav_reduced_motion', String(nextState));
    if (nextState) {
      document.documentElement.classList.add('reduced-motion');
    } else {
      document.documentElement.classList.remove('reduced-motion');
    }
  };

  return (
    <button
      onClick={toggleMotion}
      type="button"
      className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-stone-300/80 dark:border-stone-700 bg-stone-100/90 dark:bg-stone-900/90 text-stone-700 dark:text-stone-300 hover:text-stone-950 dark:hover:text-white transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 active:scale-95 shadow-xs"
      title={isReduced ? 'Motion: Off (Reduced) — click to enable animations' : 'Motion: Dynamic 3D — click to reduce motion'}
    >
      {isReduced ? (
        <>
          <Play className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
          <span>Motion: Off (Reduced)</span>
        </>
      ) : (
        <>
          <EyeOff className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" aria-hidden="true" />
          <span>Motion: Dynamic 3D</span>
        </>
      )}
    </button>
  );
}
