"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Navbar } from "@/components/ui/Navbar";
import { GuestCoordinationModule } from "@/components/ui/GuestCoordinationModule";
import { ElderDisclaimerBanner } from "@/components/ui/ElderDisclaimerBanner";
import { getAuthHeaders } from "@/lib/auth";

export default function GuestPageClient() {
  const params = useParams();
  const router = useRouter();
  const rawEventId = (params?.id as string) || "";

  const [eventName, setEventName] = useState<string>("Celebration");
  const [targetId, setTargetId] = useState<string>(rawEventId);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const getApiBase = () => {
    return typeof window !== "undefined" &&
      window.location.hostname.includes("netlify.app")
      ? "/api/v1"
      : "https://utsav-ai-ycg2.onrender.com/api/v1";
  };

  useEffect(() => {
    let ignore = false;
    const init = async () => {
      await Promise.resolve();
      if (ignore) return;

      let resolvedId = rawEventId;
      if (!resolvedId || resolvedId === "default") {
        try {
          const saved = localStorage.getItem("utsav_last_event_id");
          if (saved && saved !== "default") {
            resolvedId = saved;
            router.replace(`/dashboard/events/${saved}/guests`);
            return;
          }
        } catch (e) {
          // ignore
        }
        setIsLoading(false);
        setErrorMessage(
          "No celebration event selected. Please launch an event from the dashboard.",
        );
        return;
      }

      setTargetId(resolvedId);

      // Fetch event basic metadata
      try {
        const res = await fetch(`${getApiBase()}/events/${resolvedId}`, {
          headers: getAuthHeaders(resolvedId),
        });
        if (!ignore) {
          if (res.ok) {
            const data = await res.json();
            setEventName(data.name || "Celebration");
          } else if (res.status === 404) {
            setErrorMessage(`Event "${resolvedId}" not found in database.`);
          }
        }
      } catch (err: unknown) {
        console.error("Failed to fetch event:", err);
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    init();
    return () => {
      ignore = true;
    };
  }, [rawEventId, router]);

  if (errorMessage) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] dark:bg-[#0C0F14] text-[#1C1917] dark:text-[#F8FAFC]">
        <Navbar />
        <main className="max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
          <div className="p-8 rounded-3xl glass-card border border-rose-200 dark:border-rose-900/60 bg-rose-50/30 dark:bg-rose-950/20 space-y-3">
            <div className="text-3xl">⚠️</div>
            <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-50">
              Event Not Found
            </h2>
            <p className="text-xs text-stone-600 dark:text-stone-400 max-w-md mx-auto">
              {errorMessage}
            </p>
            <Link
              href="/"
              className="inline-block mt-3 px-6 py-2.5 rounded-full bg-[#8B1E28] text-white text-xs font-semibold"
            >
              Return to Intake Wizard
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF7F2] dark:bg-[#0C0F14] text-[#1C1917] dark:text-[#F8FAFC]">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between pb-2">
          <Link
            href={`/dashboard/events/${targetId}`}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#8B1E28] dark:text-[#F4B41A] hover:underline"
          >
            ← Back to Unified Event Workspace ({eventName})
          </Link>
          <span className="text-xs text-stone-400 font-mono">
            Event ID: {targetId}
          </span>
        </div>

        {/* Guest Coordination Module */}
        <GuestCoordinationModule
          eventId={targetId}
          eventName={eventName}
          apiBase={getApiBase()}
        />

        <section className="pt-4">
          <ElderDisclaimerBanner />
        </section>
      </main>
    </div>
  );
}
