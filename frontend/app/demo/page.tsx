"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Navbar } from "@/components/ui/Navbar";
import { ElderDisclaimerBanner } from "@/components/ui/ElderDisclaimerBanner";

// Currency Formatter
const formatINR = (val: number) => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(val);
};

export default function DemoShowcasePage() {
  const [activeTab, setActiveTab] = useState<"overview" | "budget">("overview");

  const demoEvent = {
    name: "Ananya & Rohan's Celebration (Illustrative Demo)",
    host: "Rohan Joshi",
    city: "Pune",
    cityTier: "TIER 2",
    guestCount: 350,
    totalBudget: 3500000,
    tradition: "Maharashtrian Vedic Lagna 🕉️",
    subEvents: [
      {
        name: "Sakharpuda (Ring Ceremony)",
        time: "10:00 AM - 01:00 PM",
        venue: "The Heritage Banquets",
        muhurat: true,
      },
      {
        name: "Haldi & Sangeet Evening",
        time: "05:00 PM - 10:00 PM",
        venue: "Emerald Lawns (Open Air)",
        muhurat: false,
      },
      {
        name: "Mandap Muhurat & Lagna Vivah",
        time: "09:30 AM - 02:30 PM",
        venue: "Vedic Wedding Hall",
        muhurat: true,
      },
      {
        name: "Grand Reception & Gala Dinner",
        time: "07:00 PM - 11:30 PM",
        venue: "Grand Ballroom, JW Marriott",
        muhurat: false,
      },
    ],
    budgetItems: [
      { name: "Catering & Food Service", pct: 28, amount: 980000 },
      { name: "Venue & Banquet Rental", pct: 22, amount: 770000 },
      { name: "Mandap & Floral Decor", pct: 16, amount: 560000 },
      { name: "Photography & Cinematography", pct: 9, amount: 315000 },
      { name: "DJ, Sound & Sangeet Artists", pct: 7, amount: 245000 },
      { name: "Bridal & Groom Attire", pct: 6, amount: 210000 },
      { name: "Panditji Dakshina & Samagri", pct: 4, amount: 140000 },
      { name: "Guest Shuttles & Valet", pct: 4, amount: 140000 },
      { name: "Contingency & Fuel Buffer", pct: 4, amount: 140000 },
    ],
  };

  return (
    <div className="min-h-screen pb-24">
      {/* Prominent Demo Warning Banner */}
      <div className="bg-gradient-to-r from-amber-600 to-amber-700 text-white px-4 py-2.5 text-xs text-center font-bold tracking-wide shadow-md flex items-center justify-center gap-2">
        <span>⚠️ DEMO PREVIEW:</span>
        <span className="font-medium">
          This is an illustrative showcase using sample benchmark data. No live
          event database record is connected.
        </span>
        <Link
          href="/onboarding"
          className="ml-2 underline font-bold hover:text-amber-200 transition-colors"
        >
          Create Real Plan →
        </Link>
      </div>

      <Navbar
        badge="Demo Showcase"
        rightAction={
          <Link
            href="/onboarding"
            className="text-xs font-semibold px-4 py-2 rounded-xl bg-[#8B1E28] hover:bg-[#721820] text-white dark:bg-[#F4B41A] dark:text-stone-950 transition-all shadow-sm"
          >
            + Start Real Onboarding
          </Link>
        }
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 space-y-8">
        {/* Hero Header */}
        <section className="glass-card rounded-3xl p-6 sm:p-8 relative overflow-hidden shadow-sm border border-amber-300 dark:border-amber-800">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300">
                {demoEvent.tradition}
              </span>
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300">
                📍 {demoEvent.city} ({demoEvent.cityTier})
              </span>
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300">
                👥 {demoEvent.guestCount} Guests
              </span>
              <span className="px-2.5 py-1 rounded-full text-xs font-bold font-mono bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-400/40">
                DEMO PREVIEW
              </span>
            </div>

            <h1 className="text-3xl sm:text-4xl font-serif font-bold text-stone-900 dark:text-stone-50">
              {demoEvent.name}
            </h1>
            <p className="text-sm text-stone-600 dark:text-stone-300">
              Sample Host: <strong>{demoEvent.host}</strong> • Envelope:{" "}
              <strong className="text-stone-900 dark:text-stone-100">
                {formatINR(demoEvent.totalBudget)}
              </strong>
            </p>
          </div>
        </section>

        {/* Tab Controls */}
        <section className="flex border-b border-stone-200 dark:border-stone-800 gap-2">
          {[
            { key: "overview", label: "Overview & Schedule", icon: "⚡" },
            { key: "budget", label: "Itemized Budget Preview", icon: "💰" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as "overview" | "budget")}
              className={`flex items-center gap-2 px-5 py-3 text-xs sm:text-sm font-semibold transition-all border-b-2 ${
                activeTab === tab.key
                  ? "border-amber-600 text-amber-700 dark:text-amber-400"
                  : "border-transparent text-stone-500 hover:text-stone-800"
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </section>

        {/* Content */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
              Sample Run-of-Show Timetable
            </h3>
            <div className="grid sm:grid-cols-2 gap-4">
              {demoEvent.subEvents.map((se, i) => (
                <div
                  key={i}
                  className="glass-card p-5 rounded-2xl border border-stone-200 dark:border-stone-800 space-y-2"
                >
                  <div className="flex justify-between items-start">
                    <h4 className="font-semibold text-sm text-stone-900 dark:text-stone-100">
                      {se.name}
                    </h4>
                    {se.muhurat && (
                      <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300">
                        🕉️ Muhurat Locked
                      </span>
                    )}
                  </div>
                  <div className="text-xs font-mono text-stone-500">
                    {se.time}
                  </div>
                  <div className="text-xs text-stone-600 dark:text-stone-400">
                    📍 {se.venue}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "budget" && (
          <div className="space-y-4">
            <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
              Sample Deterministic Budget Breakdown
            </h3>
            <div className="grid sm:grid-cols-3 gap-3">
              {demoEvent.budgetItems.map((b, i) => (
                <div
                  key={i}
                  className="glass-card p-4 rounded-xl border border-stone-200 dark:border-stone-800 space-y-1"
                >
                  <div className="flex justify-between text-xs text-stone-500 font-medium">
                    <span>{b.name}</span>
                    <span>{b.pct}%</span>
                  </div>
                  <div className="font-bold text-base text-stone-900 dark:text-stone-100">
                    {formatINR(b.amount)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <ElderDisclaimerBanner />
      </main>
    </div>
  );
}
