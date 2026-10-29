"use client";

import React from "react";
import Link from "next/link";
import { Navbar } from "@/components/ui/Navbar";
import { ElderDisclaimerBanner } from "@/components/ui/ElderDisclaimerBanner";
import { HeroChaosToComposed } from "@/components/3d/HeroChaosToComposed";
import { WalkthroughVideoPlayer } from "@/components/ui/WalkthroughVideoPlayer";
import { FeatureShowcase3D } from "@/components/3d/FeatureShowcase3D";
import { DiyaLightingInteraction } from "@/components/3d/DiyaLightingInteraction";

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col bg-[#FAF7F2] dark:bg-[#0C0E12] text-stone-900 dark:text-stone-100 transition-colors duration-200">
      {/* Top Sticky Navigation with Theme & Motion Toggles */}
      <Navbar
        rightAction={
          <Link
            href="/onboarding"
            className="px-4 sm:px-5 py-2 rounded-full text-xs font-semibold tracking-wider uppercase bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 transition-all shadow-sm active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
          >
            Compose Celebration
          </Link>
        }
      />

      {/* Main Content Flow */}
      <main id="main-content" className="flex-1">
        {/* 1. Hero: From Planning Chaos to Composed Celebration */}
        <HeroChaosToComposed />

        {/* 2. Real Product Walkthrough Video (Synchronized Voiceover & Captions) */}
        <WalkthroughVideoPlayer />

        {/* 3. Feature Showcase: 4 Depth-First 3D Interactive Feature Sections */}
        <FeatureShowcase3D />

        {/* 4. Mandatory Cultural Elder Verification Safeguard Banner */}
        <div className="max-w-3xl mx-auto px-4 sm:px-6 my-12">
          <ElderDisclaimerBanner />
        </div>

        {/* 5. Auspicious Interactive Diya Lighting Micro-Interaction */}
        <DiyaLightingInteraction />
      </main>

      {/* Accessible Footer */}
      <footer className="border-t border-stone-200/80 dark:border-stone-800/80 py-10 bg-white/50 dark:bg-stone-950/50 backdrop-blur-md text-xs text-stone-600 dark:text-stone-400">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-[#8B1E28] to-[#F4B41A] flex items-center justify-center text-white font-devanagari text-xs shadow-xs">
              उ
            </div>
            <p className="font-medium text-stone-800 dark:text-stone-200">
              © 2026 Utsav AI. Composed with deep respect for Indian heritage
              traditions.
            </p>
          </div>

          <div className="flex items-center space-x-6">
            <Link
              href="/onboarding"
              className="hover:text-stone-900 dark:hover:text-white transition-colors underline-offset-4 hover:underline"
            >
              Intake Studio
            </Link>
            <Link
              href="/dashboard/vendors/quotes"
              className="hover:text-stone-900 dark:hover:text-white transition-colors underline-offset-4 hover:underline"
            >
              Quote Auditor
            </Link>
            <Link
              href="/privacy"
              className="hover:text-stone-900 dark:hover:text-white transition-colors underline-offset-4 hover:underline"
            >
              Privacy Policy
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
