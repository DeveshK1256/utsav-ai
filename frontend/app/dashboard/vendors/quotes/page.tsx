"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Navbar } from "@/components/ui/Navbar";

export default function GenericQuotesRedirect() {
  const router = useRouter();

  useEffect(() => {
    try {
      const saved = localStorage.getItem("utsav_last_event_id");
      if (saved && saved !== "default") {
        router.replace(`/dashboard/events/${saved}/vendors/quotes`);
        return;
      }
    } catch (e) {
      // ignore
    }
  }, [router]);

  return (
    <div className="min-h-screen pb-20">
      <Navbar badge="Vendor Hub" />
      <div className="max-w-md mx-auto pt-20 px-4 text-center space-y-4">
        <div className="w-14 h-14 bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 rounded-2xl flex items-center justify-center mx-auto text-2xl font-bold shadow-sm">
          📑
        </div>
        <h2 className="text-xl font-serif font-bold text-stone-900 dark:text-stone-50">
          Select Celebration to Manage Quotes
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
          Vendor quotations, OCR line item audits, and benchmark comparisons are
          strictly scoped to specific celebration events.
        </p>
        <div className="pt-2">
          <Link
            href="/onboarding"
            className="px-6 py-2.5 rounded-xl bg-[#8B1E28] hover:bg-[#721820] text-white dark:bg-[#F4B41A] dark:text-stone-950 text-xs font-semibold shadow-md inline-block transition-all"
          >
            + Create New Celebration
          </Link>
        </div>
      </div>
    </div>
  );
}
