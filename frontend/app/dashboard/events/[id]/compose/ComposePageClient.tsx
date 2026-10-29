"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Navbar } from "@/components/ui/Navbar";
import {
  VenueDiscoveryList,
  VendorDiscoveryItem,
} from "@/components/ui/VenueDiscoveryList";
import { WakingUpNotice } from "@/components/ui/WakingUpNotice";
import { getAuthHeaders } from "@/lib/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== "undefined" &&
  window.location.hostname.includes("netlify.app")
    ? "/api/v1"
    : "https://utsav-ai-ycg2.onrender.com/api/v1");

interface EventState {
  id: string;
  name: string;
  city: string;
  start_date?: string;
  metadata_json?: Record<string, unknown>;
  sub_events?: Array<{
    id: string;
    name: string;
    start_time: string;
    end_time: string;
    is_muhurat_locked: boolean;
  }>;
}

export default function ComposePageClient() {
  const params = useParams();
  const router = useRouter();
  const rawEventId = (params?.id as string) || "";

  const [eventId, setEventId] = useState<string>(rawEventId);
  const [eventData, setEventData] = useState<EventState | null>(null);
  const [currentStep, setCurrentStep] = useState<
    "venue" | "timing" | "invitation"
  >("venue");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step A: Selected Venue State
  const [selectedVenue, setSelectedVenue] =
    useState<VendorDiscoveryItem | null>(null);

  // Step B: Timing & Muhurat State
  const [muhuratOptions, setMuhuratOptions] = useState<
    Array<{
      name: string;
      time: string;
      type: string;
      notes: string;
    }>
  >([]);
  const [selectedMuhurat, setSelectedMuhurat] = useState<string>("");

  const loadEvent = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/events/${id}`, {
        headers: getAuthHeaders(id),
      });
      if (!res.ok) throw new Error("Event not found");
      const data: EventState = await res.json();
      setEventData(data);

      // Restore persisted step & picks if available
      const composeState =
        (data.metadata_json?.compose_celebration as
          Record<string, unknown> | undefined) || {};
      if (composeState.current_step === "timing") {
        setCurrentStep("timing");
      }

      // Populate candidate muhurat windows for Step B from real M5 ephemeris
      const eventDate =
        data.start_date || new Date().toISOString().split("T")[0];
      const cityCoords: Record<string, { lat: number; lng: number }> = {
        pune: { lat: 18.5204, lng: 73.8567 },
        jaipur: { lat: 26.9124, lng: 75.7873 },
        delhi: { lat: 28.6139, lng: 77.209 },
        mumbai: { lat: 18.922, lng: 72.8347 },
        bengaluru: { lat: 12.9716, lng: 77.5946 },
      };
      const cityKey = (data.city || "pune").toLowerCase();
      const coords = cityCoords[cityKey] || { lat: 18.5204, lng: 73.8567 };

      fetch(
        `${API_BASE_URL}/rituals/muhurat-candidates?event_date=${eventDate}&latitude=${coords.lat}&longitude=${coords.lng}`,
      )
        .then((r) => r.json())
        .then((res) => {
          if (res && res.candidates && res.candidates.length > 0) {
            setMuhuratOptions(
              res.candidates.map(
                (w: {
                  id: string;
                  name: string;
                  window: string;
                  suitability: string;
                  planetary_rationale?: string;
                }) => ({
                  name: w.name,
                  time: w.window,
                  type: w.suitability,
                  notes: w.planetary_rationale,
                }),
              ),
            );
          }
        })
        .catch(() => {});
    } catch (err: unknown) {
      setError(
        (err instanceof Error ? err.message : String(err)) ||
          "Failed to load celebration event",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let resolvedId = rawEventId;
    if (typeof window !== "undefined") {
      const segments = window.location.pathname.split("/").filter(Boolean);
      const evIdx = segments.indexOf("events");
      if (
        evIdx !== -1 &&
        segments[evIdx + 1] &&
        segments[evIdx + 1] !== "default"
      ) {
        resolvedId = segments[evIdx + 1] ?? rawEventId;
      } else if (!resolvedId || resolvedId === "default") {
        const stored =
          localStorage.getItem("current_event_id") ||
          localStorage.getItem("last_event_id");
        if (stored) resolvedId = stored;
      }
    }

    if (resolvedId && resolvedId !== "default") {
      setEventId(resolvedId);
      loadEvent(resolvedId);
    } else {
      setLoading(false);
    }
  }, [rawEventId, loadEvent]);

  // Step A: Save Venue or Skip
  const handleConfirmVenue = async (skip: boolean = false) => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { step: "venue" };
      if (skip) {
        payload.skip_venue = true;
      } else if (selectedVenue) {
        payload.vendor_profile_id = selectedVenue.id;
        payload.venue_name = selectedVenue.business_name;
        payload.venue_locality = selectedVenue.locality;
        payload.venue_city = selectedVenue.city;
        payload.latitude = selectedVenue.latitude;
        payload.longitude = selectedVenue.longitude;
        payload.source_notes = selectedVenue.source_notes;
      }

      const res = await fetch(`${API_BASE_URL}/events/${eventId}/compose`, {
        method: "POST",
        headers: getAuthHeaders(eventId, {
          "Content-Type": "application/json",
        }),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to update venue selection");
      const updated = await res.json();
      setEventData(updated);
      setCurrentStep("timing");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  // Step B: Save Muhurat or Skip -> Transition to Step C (Invitation Studio)
  const handleConfirmTiming = async (skip: boolean = false) => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { step: "invitation" };
      if (skip) {
        payload.skip_timing = true;
      } else if (selectedMuhurat) {
        payload.muhurat_time = selectedMuhurat;
        payload.muhurat_notes = "Confirmed via Compose Celebration";
      }

      const res = await fetch(`${API_BASE_URL}/events/${eventId}/compose`, {
        method: "POST",
        headers: getAuthHeaders(eventId, {
          "Content-Type": "application/json",
        }),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to update timing selection");

      // Navigate to Step C (existing Invitation Studio)
      router.push(`/dashboard/events/${eventId}/invitations`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-stone-50 dark:bg-stone-950 text-stone-900 dark:text-stone-100 flex flex-col font-sans">
        <Navbar />
        <main className="flex-1 max-w-lg w-full mx-auto px-4 pt-24 text-center space-y-4">
          <div className="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <h2 className="text-xl font-serif font-bold text-stone-900 dark:text-stone-100">
            Loading Celebration Workspace...
          </h2>
          <p className="text-xs text-stone-500 dark:text-stone-400 font-mono">
            Fetching event #{eventId || rawEventId} configuration
          </p>
          <WakingUpNotice
            isLoading={loading}
            timeoutMs={3500}
            className="mt-6"
          />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-50 dark:bg-stone-950 text-stone-900 dark:text-stone-100 flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 space-y-8">
        <WakingUpNotice isLoading={saving} timeoutMs={3500} />
        {/* Breadcrumb / Top Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-stone-200 dark:border-stone-800 pb-4">
          <div>
            <div className="flex items-center gap-2 text-xs text-stone-500 mb-1">
              <Link
                href={`/dashboard/events/${eventId}`}
                className="hover:underline"
              >
                ← Back to Event Cockpit
              </Link>
            </div>
            <h1 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-50">
              Compose Celebration (Stage 4)
            </h1>
            <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
              Guided end-to-end orchestration: Location & Venue → Muhurat Timing
              → Personalized Invitations.
            </p>
          </div>

          {/* Stepper Indicator */}
          <div className="flex items-center gap-2 text-xs font-semibold">
            <span
              className={`px-3 py-1 rounded-full border ${currentStep === "venue" ? "bg-[#8B1E28] text-white border-[#8B1E28]" : "bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300"}`}
            >
              Step A: Venue
            </span>
            <span className="text-stone-600 dark:text-stone-400 font-bold">
              →
            </span>
            <span
              className={`px-3 py-1 rounded-full border ${currentStep === "timing" ? "bg-[#8B1E28] text-white border-[#8B1E28]" : "bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300"}`}
            >
              Step B: Timing
            </span>
            <span className="text-stone-600 dark:text-stone-400 font-bold">
              →
            </span>
            <span
              className={`px-3 py-1 rounded-full border ${currentStep === "invitation" ? "bg-[#8B1E28] text-white border-[#8B1E28]" : "bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300"}`}
            >
              Step C: Invitation
            </span>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 text-red-700 text-xs rounded-xl border border-red-200">
            {error}
          </div>
        )}

        {/* STEP A: VENUE DISCOVERY & SELECTION */}
        {currentStep === "venue" && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-stone-900 p-6 rounded-2xl border border-stone-200 dark:border-stone-800 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-serif font-bold">
                    Step A: Select or Shortlist a Celebration Venue
                  </h2>
                  <p className="text-xs text-stone-600 dark:text-stone-400 mt-0.5">
                    Select a venue from our curated real directory, or skip to
                    proceed with a &quot;Venue to be confirmed&quot;
                    placeholder.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleConfirmVenue(true)}
                    disabled={saving}
                    className="text-xs px-4 py-2 text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-200 hover:underline"
                  >
                    Skip for now →
                  </button>
                  <button
                    onClick={() => handleConfirmVenue(false)}
                    disabled={!selectedVenue || saving}
                    className="text-xs px-5 py-2.5 bg-[#8B1E28] text-white rounded-xl font-semibold shadow hover:bg-[#721820] disabled:opacity-50 transition-all"
                  >
                    {saving ? "Saving..." : "Confirm Venue & Next →"}
                  </button>
                </div>
              </div>

              {/* Shortlist Transparency Banner */}
              <div className="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/50 rounded-xl text-xs text-amber-900 dark:text-amber-200">
                ℹ️ <strong>Honesty Standard:</strong> Selecting a venue here
                records your shortlist preference for invitation and planning
                logistics. It does <em>not</em> represent a confirmed booking
                (quote audit and vendor contracts occur in the Vendor Hub).
              </div>
            </div>

            <VenueDiscoveryList
              initialCity={eventData?.city || "Pune"}
              selectedVenueId={selectedVenue?.id}
              onSelectVenue={(v) => setSelectedVenue(v)}
            />
          </div>
        )}

        {/* STEP B: MUHURAT & TIMING SELECTION */}
        {currentStep === "timing" && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-stone-900 p-6 rounded-2xl border border-stone-200 dark:border-stone-800 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-serif font-bold">
                    Step B: Confirm Auspicious Muhurat Timing
                  </h2>
                  <p className="text-xs text-stone-600 dark:text-stone-400 mt-0.5">
                    Astronomical panchang windows computed for your date. You
                    can also skip if timing is still pending.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleConfirmTiming(true)}
                    disabled={saving}
                    className="text-xs px-4 py-2 text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-200 hover:underline"
                  >
                    Skip timing for now →
                  </button>
                  <button
                    onClick={() => handleConfirmTiming(false)}
                    disabled={!selectedMuhurat || saving}
                    className="text-xs px-5 py-2.5 bg-[#8B1E28] text-white rounded-xl font-semibold shadow hover:bg-[#721820] disabled:opacity-50 transition-all"
                  >
                    {saving ? "Saving..." : "Confirm Timing & Launch Studio →"}
                  </button>
                </div>
              </div>

              {/* Non-negotiable Elder Disclaimer (DEC-009 / M5) */}
              <div className="p-4 bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-900 rounded-xl text-xs text-amber-900 dark:text-amber-200 space-y-1">
                <div className="font-semibold flex items-center gap-1.5">
                  <span>🕉️</span> Mandatory Cultural Advisory (DEC-009):
                </div>
                <p>
                  Auspicious timings & ritual checklists are algorithmic
                  estimates computed via astronomical ephemeris models. Please
                  verify with your family Guruji or elders before making final
                  public commitments.
                </p>
              </div>

              {/* Muhurat Windows Options */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  Ephemeris Computed Windows
                </h3>

                <div className="grid md:grid-cols-3 gap-4">
                  {muhuratOptions.map((opt, i) => {
                    const isSelected = selectedMuhurat === opt.time;
                    return (
                      <div
                        key={i}
                        onClick={() => setSelectedMuhurat(opt.time)}
                        className={`p-4 rounded-xl border text-left cursor-pointer transition-all ${
                          isSelected
                            ? "border-[#8B1E28] bg-amber-50/50 dark:bg-amber-950/40 shadow-sm"
                            : "border-stone-200 dark:border-stone-800 hover:border-amber-400"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono font-semibold text-amber-800 dark:text-amber-300">
                            {opt.time}
                          </span>
                          {isSelected && (
                            <span className="text-xs text-[#8B1E28] font-bold">
                              ✓ Selected
                            </span>
                          )}
                        </div>
                        <h4 className="font-medium text-xs text-stone-900 dark:text-stone-100 mt-2">
                          {opt.name}
                        </h4>
                        <p className="text-[11px] text-stone-500 dark:text-stone-400 mt-1">
                          {opt.notes}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
