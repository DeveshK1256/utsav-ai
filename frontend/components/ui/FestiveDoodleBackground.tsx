'use client';

import React from 'react';

export function FestiveDoodleBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden select-none"
    >
      {/* Subtle festive ambient gradient orbs */}
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-gradient-to-br from-amber-400/10 via-rose-500/5 to-transparent blur-3xl dark:from-amber-500/10 dark:via-rose-600/5" />
      <div className="absolute top-1/3 -right-32 w-[32rem] h-[32rem] rounded-full bg-gradient-to-bl from-orange-400/10 via-amber-300/5 to-transparent blur-3xl dark:from-orange-500/10 dark:via-amber-400/5" />
      <div className="absolute -bottom-32 left-1/4 w-[28rem] h-[28rem] rounded-full bg-gradient-to-tr from-rose-500/10 via-amber-400/5 to-transparent blur-3xl dark:from-rose-600/10 dark:via-amber-500/5" />

      {/* SVG Pattern of Festive Event Doodles */}
      <svg
        className="absolute inset-0 w-full h-full opacity-[0.045] dark:opacity-[0.07] text-stone-900 dark:text-amber-400 transition-opacity duration-300"
        xmlns="http://www.w3.org/2000/svg"
        width="100%"
        height="100%"
      >
        <defs>
          <pattern
            id="utsav-festive-doodles"
            width="320"
            height="320"
            patternUnits="userSpaceOnUse"
          >
            {/* 1. Auspicious Diya (Oil Lamp) at (40, 40) */}
            <g transform="translate(30, 30)">
              {/* Flame */}
              <path
                d="M 25 2 C 28 8, 32 15, 25 22 C 18 15, 22 8, 25 2 Z"
                fill="currentColor"
                opacity="0.9"
              />
              <path
                d="M 25 8 C 26 12, 28 16, 25 19 C 22 16, 24 12, 25 8 Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.2"
              />
              {/* Diya Base */}
              <path
                d="M 5 24 Q 25 38 45 24 Q 38 34 25 34 Q 12 34 5 24 Z"
                fill="currentColor"
              />
              <path
                d="M 12 34 L 10 38 L 40 38 L 38 34 Z"
                fill="currentColor"
              />
            </g>

            {/* 2. Shehnai / Music Horn at (200, 35) */}
            <g transform="translate(190, 30) rotate(-25)">
              <path
                d="M 4 8 L 50 14 L 62 26 L 62 4 L 50 16 L 4 20 Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="16" cy="14" r="1.5" fill="currentColor" />
              <circle cx="26" cy="15" r="1.5" fill="currentColor" />
              <circle cx="36" cy="16" r="1.5" fill="currentColor" />
              <circle cx="44" cy="16.5" r="1.5" fill="currentColor" />
              {/* Musical celebration notes */}
              <path d="M 66 10 Q 72 6 78 12" stroke="currentColor" strokeWidth="1.2" fill="none" />
              <circle cx="78" cy="12" r="2" fill="currentColor" />
              <path d="M 72 24 Q 78 20 84 26" stroke="currentColor" strokeWidth="1.2" fill="none" />
              <circle cx="84" cy="26" r="2" fill="currentColor" />
            </g>

            {/* 3. Auspicious Kalash with Mango Leaves & Coconut at (50, 190) */}
            <g transform="translate(40, 180)">
              {/* Coconut */}
              <circle cx="25" cy="16" r="10" fill="none" stroke="currentColor" strokeWidth="1.6" />
              {/* Mango leaves fan */}
              <path d="M 15 20 Q 25 4 35 20" stroke="currentColor" strokeWidth="1.5" fill="none" />
              <path d="M 10 22 Q 18 10 25 22" stroke="currentColor" strokeWidth="1.4" fill="none" />
              <path d="M 25 22 Q 32 10 40 22" stroke="currentColor" strokeWidth="1.4" fill="none" />
              {/* Pot Neck & Body */}
              <rect x="18" y="22" width="14" height="4" rx="2" fill="currentColor" />
              <path
                d="M 18 26 C 6 32 6 48 25 50 C 44 48 44 32 32 26 Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinejoin="round"
              />
              {/* Sacred Swastik / Tilak lines on pot */}
              <line x1="25" y1="32" x2="25" y2="44" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              <line x1="19" y1="38" x2="31" y2="38" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </g>

            {/* 4. Marigold Flower / Radial Mandala at (190, 180) */}
            <g transform="translate(190, 180)">
              <circle cx="30" cy="30" r="7" fill="currentColor" />
              {/* 8 Petals */}
              {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => (
                <ellipse
                  key={i}
                  cx="30"
                  cy="14"
                  rx="4.5"
                  ry="9"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  transform={`rotate(${angle} 30 30)`}
                />
              ))}
              <circle cx="30" cy="30" r="18" stroke="currentColor" strokeWidth="0.8" strokeDasharray="2 2" fill="none" />
            </g>

            {/* 5. Dholak / Drum with celebration sticks at (115, 105) */}
            <g transform="translate(110, 100) rotate(15)">
              <ellipse cx="14" cy="22" rx="6" ry="14" fill="none" stroke="currentColor" strokeWidth="1.6" />
              <ellipse cx="50" cy="22" rx="6" ry="14" fill="none" stroke="currentColor" strokeWidth="1.6" />
              <path d="M 14 8 Q 32 5 50 8 M 14 36 Q 32 39 50 36" stroke="currentColor" strokeWidth="1.6" fill="none" />
              {/* Diagonal tightening ropes */}
              <line x1="14" y1="8" x2="32" y2="39" stroke="currentColor" strokeWidth="1.2" />
              <line x1="32" y1="39" x2="50" y2="8" stroke="currentColor" strokeWidth="1.2" />
              <line x1="14" y1="36" x2="32" y2="5" stroke="currentColor" strokeWidth="1.2" />
              <line x1="32" y1="5" x2="50" y2="36" stroke="currentColor" strokeWidth="1.2" />
            </g>

            {/* 6. Hanging Toran & Mango Leaf Garland Garland at (275, 110) */}
            <g transform="translate(260, 95)">
              <path d="M 0 10 Q 25 24 50 10 Q 75 24 100 10" stroke="currentColor" strokeWidth="1.6" fill="none" />
              {/* Hanging leaf triangular tassels */}
              <path d="M 15 16 L 25 32 L 35 16 Z" fill="none" stroke="currentColor" strokeWidth="1.2" />
              <path d="M 65 16 L 75 32 L 85 16 Z" fill="none" stroke="currentColor" strokeWidth="1.2" />
              <circle cx="25" cy="35" r="2.5" fill="currentColor" />
              <circle cx="75" cy="35" r="2.5" fill="currentColor" />
            </g>

            {/* 7. Auspicious Paisley / Kalka at (270, 260) */}
            <g transform="translate(260, 245) rotate(-15)">
              <path
                d="M 20 40 C 5 40 2 26 12 16 C 18 10 26 4 28 0 C 30 6 34 16 30 24 C 26 30 35 34 20 40 Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
              <circle cx="20" cy="26" r="3.5" fill="currentColor" />
            </g>

            {/* 8. Starburst celebration sparkles scattered */}
            <g transform="translate(130, 20)">
              <line x1="10" y1="4" x2="10" y2="16" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              <line x1="4" y1="10" x2="16" y2="10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              <line x1="6" y1="6" x2="14" y2="14" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
              <line x1="6" y1="14" x2="14" y2="6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </g>
            <g transform="translate(140, 260)">
              <line x1="8" y1="3" x2="8" y2="13" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
              <line x1="3" y1="8" x2="13" y2="8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </g>
            <g transform="translate(15, 120)">
              <line x1="6" y1="2" x2="6" y2="10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
              <line x1="2" y1="6" x2="10" y2="6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </g>
          </pattern>
        </defs>

        <rect width="100%" height="100%" fill="url(#utsav-festive-doodles)" />
      </svg>
    </div>
  );
}
