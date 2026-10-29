"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Sparkles, ArrowRight } from "lucide-react";
import { useReducedMotion } from "@/lib/useReducedMotion";

export function DiyaLightingInteraction() {
  const [isLit, setIsLit] = useState(false);
  const reducedMotion = useReducedMotion();

  return (
    <section className="relative w-full max-w-4xl mx-auto px-4 py-16 text-center">
      <div className="relative p-8 sm:p-12 rounded-3xl glass-card border border-amber-500/40 shadow-2xl overflow-hidden bg-gradient-to-b from-amber-50/50 via-white to-orange-50/30 dark:from-stone-900/90 dark:via-stone-900/90 dark:to-stone-950">
        {/* Glow halo behind Diya */}
        <div
          className={`absolute left-1/2 top-1/3 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full blur-3xl pointer-events-none transition-all duration-700 ${
            isLit
              ? "bg-amber-400/30 dark:bg-amber-400/20 scale-125"
              : "bg-amber-400/10 scale-90"
          }`}
          aria-hidden="true"
        />

        {/* Floating Petals when lit */}
        {isLit && !reducedMotion && (
          <div
            className="absolute inset-0 pointer-events-none overflow-hidden"
            aria-hidden="true"
          >
            <span className="absolute left-[20%] bottom-8 text-amber-500 text-lg animate-bounce duration-1000">
              🌸
            </span>
            <span className="absolute right-[25%] bottom-12 text-rose-500 text-base animate-bounce duration-700">
              🌼
            </span>
            <span className="absolute left-[35%] bottom-16 text-amber-400 text-sm animate-bounce duration-500">
              ✨
            </span>
            <span className="absolute right-[40%] bottom-10 text-orange-500 text-lg animate-bounce duration-800">
              🌸
            </span>
          </div>
        )}

        {/* Interactive Diya Graphic */}
        <div className="flex flex-col items-center justify-center mb-6">
          <button
            type="button"
            onClick={() => setIsLit((prev) => !prev)}
            className="group relative cursor-pointer focus:outline-none focus-visible:ring-4 focus-visible:ring-amber-500 rounded-full p-2 transition-transform active:scale-95"
            aria-label={
              isLit
                ? "Extinguish celebratory diya"
                : "Light auspicious celebratory diya"
            }
          >
            <svg
              className={`w-24 h-24 sm:w-28 sm:h-28 transition-transform duration-300 ${isLit ? "scale-105" : "scale-100 opacity-80 group-hover:opacity-100"}`}
              viewBox="0 0 64 64"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Flame (Only visible or glowing when lit) */}
              {isLit ? (
                <g className={reducedMotion ? "" : "animate-pulse"}>
                  {/* Outer Flame Glow */}
                  <ellipse
                    cx="32"
                    cy="22"
                    rx="14"
                    ry="18"
                    fill="#F59E0B"
                    fillOpacity="0.25"
                  />
                  {/* Flame Outer */}
                  <path
                    d="M32 6 C38 14, 42 22, 40 28 C38 34, 34 36, 32 36 C30 34, 26 34, 24 28 C22 22, 26 14, 32 6 Z"
                    fill="#F4B41A"
                  />
                  {/* Flame Inner Core */}
                  <path
                    d="M32 14 C35 19, 37 24, 36 27 C35 30, 33 31, 32 31 C31 31, 29 30, 28 27 C27 24, 29 19, 32 14 Z"
                    fill="#FFF9C4"
                  />
                </g>
              ) : (
                /* Unlit Wick */
                <path
                  d="M32 28 C32.5 25, 33 22, 33 20"
                  stroke="#78716C"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
              )}

              {/* Diya Clay / Brass Bowl */}
              <path d="M12 36 C12 52, 52 52, 52 36 Z" fill="#8B1E28" />
              {/* Golden Rim */}
              <ellipse
                cx="32"
                cy="36"
                rx="20"
                ry="4.5"
                fill="#F4B41A"
                stroke="#C69214"
                strokeWidth="1.5"
              />
              {/* Inner Bowl Shadow */}
              <ellipse cx="32" cy="36" rx="16" ry="2.5" fill="#6B121A" />
              {/* Spout */}
              <polygon points="32,32 27,37 37,37" fill="#F4B41A" />
            </svg>
          </button>

          <span className="text-xs font-semibold text-stone-500 dark:text-stone-400 mt-2">
            {isLit
              ? "✨ Auspicious Diya Lit • Click to extinguish"
              : "👉 Tap to Light an Auspicious Diya for Your Celebration"}
          </span>
        </div>

        {/* Auspicious Inscription */}
        <div className="max-w-xl mx-auto mb-8">
          <div className="text-xs font-serif font-bold tracking-widest text-[#8B1E28] dark:text-[#FF8F9B] mb-2 uppercase">
            ॥ शुभं करोति कल्याणम् आरोग्यम् धनसंपदा ॥
          </div>
          <h3 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900 dark:text-stone-100 mb-3">
            Every celebration deserves calm, dignity, and joy.
          </h3>
          <p className="text-sm text-stone-600 dark:text-stone-300">
            Let Utsav handle the spreadsheets, quote renegotiations, and
            logistical DAGs so you can celebrate with your family.
          </p>
        </div>

        {/* Final CTA */}
        <div className="flex justify-center">
          <Link
            href="/onboarding"
            className="px-8 py-4 rounded-2xl bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 font-semibold text-sm tracking-wide transition-all shadow-xl active:scale-95 flex items-center space-x-2 group focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
          >
            <span>Begin Composing Your Celebration</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </section>
  );
}
