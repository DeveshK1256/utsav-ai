"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/ui/Navbar";
import { getAuthHeaders } from "@/lib/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== "undefined" &&
  window.location.hostname.includes("netlify.app")
    ? "/api/v1"
    : "https://utsav-ai-ycg2.onrender.com/api/v1");

interface BudgetItemDiff {
  budget_item_id: string;
  category: string;
  name: string;
  scaling_rule: string;
  old_amount: number;
  new_amount: number;
  difference: number;
  formula: string;
}

interface TaskDiff {
  added_tasks: Array<{
    title: string;
    description?: string;
    assigned_role?: string;
    duration_minutes?: number;
  }>;
  moved_tasks: Array<{
    task_id: string;
    title: string;
    old_start?: string;
    new_start?: string;
    days_shifted?: number;
    formula?: string;
  }>;
  cancelled_tasks: string[];
}

interface ChangeProposal {
  change_id: string;
  event_id: string;
  change_type: string;
  status: string; // pending, queued, applied, rejected, blocked_infeasible
  summary: string;
  budget_diff: BudgetItemDiff[];
  budget_total_old: number;
  budget_total_new: number;
  budget_total_delta: number;
  task_diff: TaskDiff;
  vendor_re_quote_categories: string[];
  capacity_warning?: string | null;
  infeasibility_reason?: string | null;
  explanation?: string | null;
  mitigation_suggestions: string[];
  created_at: string;
}

export default function ChangeProposalDiffClient() {
  const params = useParams();
  const eventId = (params?.id as string) || "";
  const changeId = (params?.change_id as string) || "";

  const [proposal, setProposal] = useState<ChangeProposal | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [hasUnsavedOverrides, setHasUnsavedOverrides] =
    useState<boolean>(false);

  // Event Context & Simulator State
  const [eventData, setEventData] = useState<{
    name: string;
    guest_count: number;
    total_budget: number;
    city: string;
  } | null>(null);
  const [existingProposals, setExistingProposals] = useState<ChangeProposal[]>(
    [],
  );
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [customGuestCount, setCustomGuestCount] = useState<number>(300);

  const fetchProposal = useCallback(
    async (targetChangeId: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE_URL}/events/${eventId}/changes/${targetChangeId}`,
          {
            headers: getAuthHeaders(eventId),
          },
        );
        if (!res.ok) {
          throw new Error(`Failed to load change proposal (${res.status})`);
        }
        const data: ChangeProposal = await res.json();
        setProposal(data);
        const initialOverrides: Record<string, number> = {};
        data.budget_diff?.forEach((item) => {
          initialOverrides[item.budget_item_id] = item.new_amount;
        });
        setOverrides(initialOverrides);
      } catch (err: unknown) {
        setError(
          (err instanceof Error
            ? err instanceof Error
              ? err.message
              : String(err)
            : String(err)) || "Error loading replanning diff",
        );
      } finally {
        setLoading(false);
      }
    },
    [eventId],
  );

  useEffect(() => {
    if (!eventId || eventId === "default") {
      setLoading(false);
      return;
    }

    // 1. Fetch Event Info
    fetch(`${API_BASE_URL}/events/${eventId}`, {
      headers: getAuthHeaders(eventId),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          setEventData({
            name: data.name,
            guest_count: data.guest_count,
            total_budget: Number(data.total_budget),
            city: data.city,
          });
          setCustomGuestCount((data.guest_count || 250) + 50);
        }
      })
      .catch((e) => console.warn("Could not fetch event context:", e));

    // 2. Fetch Existing Proposals for this Event
    fetch(`${API_BASE_URL}/events/${eventId}/changes`, {
      headers: getAuthHeaders(eventId),
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((proposals) => {
        if (Array.isArray(proposals)) {
          setExistingProposals(proposals);
        }
      })
      .catch(() => {});

    // 3. Fetch specific proposal if changeId is valid
    if (changeId && changeId !== "default") {
      fetchProposal(changeId);
    } else {
      setLoading(false);
    }
  }, [eventId, changeId, fetchProposal]);

  const handleSimulateScenario = async (
    changeType: string,
    payload: Record<string, unknown>,
  ) => {
    setIsSimulating(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/changes`, {
        method: "POST",
        headers: getAuthHeaders(eventId, {
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({
          change_type: changeType,
          payload: payload,
        }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(
          errJson.detail || `Replanning failed with status ${res.status}`,
        );
      }
      const created: ChangeProposal = await res.json();
      setProposal(created);
      setExistingProposals((prev) => [
        created,
        ...prev.filter((p) => p.change_id !== created.change_id),
      ]);
      const initialOverrides: Record<string, number> = {};
      created.budget_diff?.forEach((item) => {
        initialOverrides[item.budget_item_id] = item.new_amount;
      });
      setOverrides(initialOverrides);
    } catch (err: unknown) {
      setError(
        (err instanceof Error
          ? err instanceof Error
            ? err.message
            : String(err)
          : String(err)) || "Failed to simulate replanning scenario",
      );
    } finally {
      setIsSimulating(false);
    }
  };

  const handleAccept = async () => {
    if (!proposal) return;
    setActionLoading(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/events/${eventId}/changes/${changeId}/accept`,
        {
          method: "POST",
          headers: getAuthHeaders(eventId),
        },
      );
      if (!res.ok) {
        throw new Error(`Failed to apply proposal (${res.status})`);
      }
      const updated: ChangeProposal = await res.json();
      setProposal(updated);
    } catch (err: unknown) {
      alert(
        `Error accepting proposal: ${err instanceof Error ? err.message : String(err)}`,
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!proposal) return;
    setActionLoading(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/events/${eventId}/changes/${changeId}/reject`,
        {
          method: "POST",
          headers: getAuthHeaders(eventId),
        },
      );
      if (!res.ok) {
        throw new Error(`Failed to reject proposal (${res.status})`);
      }
      const updated: ChangeProposal = await res.json();
      setProposal(updated);
    } catch (err: unknown) {
      alert(
        `Error rejecting proposal: ${err instanceof Error ? err.message : String(err)}`,
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveOverrides = async () => {
    if (!proposal) return;
    setActionLoading(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/events/${eventId}/changes/${changeId}/overrides`,
        {
          method: "PATCH",
          headers: getAuthHeaders(eventId, {
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({ item_overrides: overrides }),
        },
      );
      if (!res.ok) {
        throw new Error(`Failed to save overrides (${res.status})`);
      }
      const updated: ChangeProposal = await res.json();
      setProposal(updated);
      setHasUnsavedOverrides(false);
    } catch (err: unknown) {
      alert(
        `Error saving overrides: ${err instanceof Error ? err.message : String(err)}`,
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleAmountChange = (budgetItemId: string, value: string) => {
    const num = parseFloat(value) || 0;
    setOverrides((prev) => ({ ...prev, [budgetItemId]: num }));
    setHasUnsavedOverrides(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-stone-600 dark:text-stone-300 font-medium">
            Evaluating plan modifications & deterministic impact...
          </p>
        </div>
      </div>
    );
  }

  if (!proposal) {
    return (
      <div className="min-h-screen pb-20">
        <Navbar
          badge="Plan B Engine"
          rightAction={
            <Link
              href={`/dashboard/events/${eventId}`}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-800 hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 transition-colors"
            >
              ← Back to Event
            </Link>
          }
        />

        <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 space-y-8">
          {/* Breadcrumb Navigation */}
          <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400 font-medium">
            <Link
              href="/"
              className="hover:text-stone-900 dark:hover:text-white transition-colors"
            >
              Home
            </Link>
            <span>/</span>
            <Link
              href={`/dashboard/events/${eventId}`}
              className="hover:text-stone-900 dark:hover:text-white transition-colors"
            >
              {eventData?.name || "Celebration"}
            </Link>
            <span>/</span>
            <span className="text-stone-700 dark:text-stone-300">
              Plan B Replanning
            </span>
          </div>

          {/* Header Hero */}
          <div className="glass-card rounded-3xl p-6 sm:p-8 border border-stone-200 dark:border-stone-800 shadow-sm space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
              Deterministic Replanning Studio
            </span>
            <h1 className="text-3xl font-serif font-bold text-stone-900 dark:text-stone-50">
              Simulate Live Plan B Scenarios
            </h1>
            <p className="text-sm text-stone-600 dark:text-stone-300 max-w-3xl leading-relaxed">
              Disruptions happen. Test schedule shifts, guest surges, or budget
              tightening with zero-LLM math. Every rupee delta and task shift is
              computed strictly in deterministic Python code before requiring
              explicit human confirmation.
            </p>
            {eventData && (
              <div className="flex flex-wrap gap-2 pt-2 text-xs font-mono text-stone-600 dark:text-stone-400">
                <span className="px-2.5 py-1 rounded-md bg-stone-100 dark:bg-stone-800">
                  Target Event: <strong>{eventData.name}</strong>
                </span>
                <span className="px-2.5 py-1 rounded-md bg-stone-100 dark:bg-stone-800">
                  Current Headcount: {eventData.guest_count}
                </span>
                <span className="px-2.5 py-1 rounded-md bg-stone-100 dark:bg-stone-800">
                  Total Budget: ₹
                  {eventData.total_budget.toLocaleString("en-IN")}
                </span>
              </div>
            )}
          </div>

          {error && (
            <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex justify-between items-center shadow-sm">
              <span>⚠️ {error}</span>
              <button onClick={() => setError(null)} className="font-bold ml-2">
                ✕
              </button>
            </div>
          )}

          {/* Instant Scenario Trigger Cards */}
          <div className="space-y-4">
            <h2 className="text-base font-serif font-bold text-stone-900 dark:text-stone-100">
              Select a Disruption Scenario to Compute Plan B Diff
            </h2>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Scenario 1: Guest Surge */}
              <div className="glass-card p-5 rounded-2xl border border-stone-200 dark:border-stone-800 hover:border-amber-400 dark:hover:border-amber-500 transition-all flex flex-col justify-between space-y-4 shadow-sm">
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 flex items-center justify-center text-xl">
                    👥
                  </div>
                  <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                    Guest Surge (+50)
                  </h3>
                  <p className="text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
                    Relatives arrive unexpectedly. Tests per-guest scaling on
                    catering, seating, and venue capacity.
                  </p>
                </div>
                <button
                  onClick={() =>
                    handleSimulateScenario("guest_count_changed", {
                      from_guest_count: eventData?.guest_count || 250,
                      to_guest_count: (eventData?.guest_count || 250) + 50,
                    })
                  }
                  disabled={isSimulating}
                  className="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs transition-all shadow-xs disabled:opacity-50"
                >
                  {isSimulating
                    ? "Computing Diff..."
                    : "Simulate Guest Surge →"}
                </button>
              </div>

              {/* Scenario 2: Emergency Budget Cut */}
              <div className="glass-card p-5 rounded-2xl border border-stone-200 dark:border-stone-800 hover:border-amber-400 dark:hover:border-amber-500 transition-all flex flex-col justify-between space-y-4 shadow-sm">
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 flex items-center justify-center text-xl">
                    📉
                  </div>
                  <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                    Budget Cut (-15%)
                  </h3>
                  <p className="text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
                    Envelope reduced by 15%. Rescales discretionary categories
                    while protecting sacred rituals.
                  </p>
                </div>
                <button
                  onClick={() =>
                    handleSimulateScenario("budget_cut", {
                      new_budget: Math.round(
                        (eventData?.total_budget || 3500000) * 0.85,
                      ),
                    })
                  }
                  disabled={isSimulating}
                  className="w-full py-2.5 rounded-xl bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900 font-semibold text-xs transition-all shadow-xs disabled:opacity-50"
                >
                  {isSimulating ? "Computing Diff..." : "Simulate Budget Cut →"}
                </button>
              </div>

              {/* Scenario 3: Weather Delay */}
              <div className="glass-card p-5 rounded-2xl border border-stone-200 dark:border-stone-800 hover:border-amber-400 dark:hover:border-amber-500 transition-all flex flex-col justify-between space-y-4 shadow-sm">
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 flex items-center justify-center text-xl">
                    🌧️
                  </div>
                  <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                    Date Shift (+2 Days)
                  </h3>
                  <p className="text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
                    Severe rain or travel delay. Shifts DAG schedule while
                    locking sacred muhurat anchors.
                  </p>
                </div>
                <button
                  onClick={() =>
                    handleSimulateScenario("date_moved", {
                      days_shifted: 2,
                    })
                  }
                  disabled={isSimulating}
                  className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-all shadow-xs disabled:opacity-50"
                >
                  {isSimulating ? "Computing Diff..." : "Simulate Date Shift →"}
                </button>
              </div>

              {/* Scenario 4: Vendor Cancellation */}
              <div className="glass-card p-5 rounded-2xl border border-stone-200 dark:border-stone-800 hover:border-amber-400 dark:hover:border-amber-500 transition-all flex flex-col justify-between space-y-4 shadow-sm">
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300 flex items-center justify-center text-xl">
                    ❌
                  </div>
                  <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                    Caterer Cancelled
                  </h3>
                  <p className="text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
                    Primary vendor defaults 10 days before wedding. Triggers
                    emergency RFP & re-quote workflow.
                  </p>
                </div>
                <button
                  onClick={() =>
                    handleSimulateScenario("vendor_cancelled", {
                      category: "catering",
                    })
                  }
                  disabled={isSimulating}
                  className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs transition-all shadow-xs disabled:opacity-50"
                >
                  {isSimulating
                    ? "Computing Diff..."
                    : "Simulate Cancellation →"}
                </button>
              </div>
            </div>
          </div>

          {/* Past Change Proposals List */}
          {existingProposals.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-stone-500">
                Existing Change Proposals ({existingProposals.length})
              </h2>
              <div className="grid gap-3">
                {existingProposals.map((p) => (
                  <div
                    key={p.change_id}
                    onClick={() => {
                      setProposal(p);
                      const initialOverrides: Record<string, number> = {};
                      p.budget_diff?.forEach((item) => {
                        initialOverrides[item.budget_item_id] = item.new_amount;
                      });
                      setOverrides(initialOverrides);
                    }}
                    className="p-4 rounded-2xl glass-card border border-stone-200 dark:border-stone-800 hover:border-amber-400 flex items-center justify-between cursor-pointer transition-all shadow-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs uppercase px-2 py-0.5 rounded-md bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300">
                          {p.change_type.replace("_", " ")}
                        </span>
                        <span
                          className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full ${
                            p.status === "applied"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                              : p.status === "rejected"
                                ? "bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-400"
                                : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                          }`}
                        >
                          {p.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-xs text-stone-700 dark:text-stone-300 font-medium mt-1">
                        {p.summary}
                      </p>
                    </div>

                    <span className="text-xs font-bold text-amber-700 dark:text-amber-400">
                      Review Diff →
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    );
  }

  const isPending = proposal.status === "pending";
  const isInfeasible = proposal.status === "blocked_infeasible";

  return (
    <div className="min-h-screen pb-20">
      {/* Universal Top Navigation */}
      <Navbar
        badge="Plan B Engine"
        rightAction={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setProposal(null)}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-800 hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 transition-colors"
            >
              🔄 New Scenario
            </button>
            <Link
              href={`/dashboard/events/${eventId}`}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-800 hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 transition-colors"
            >
              ← Back to Event
            </Link>
          </div>
        }
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 space-y-6">
        {/* Proposal Header Banner */}
        <div className="glass-card rounded-3xl p-6 sm:p-7 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 font-mono">
                Proposal ID: {proposal.change_id.slice(0, 8)}
              </span>
              <span
                className={`px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider border ${
                  proposal.status === "applied"
                    ? "bg-emerald-100 dark:bg-emerald-950/80 border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
                    : proposal.status === "rejected"
                      ? "bg-stone-200 dark:bg-stone-800 border-stone-300 dark:border-stone-700 text-stone-700 dark:text-stone-300"
                      : proposal.status === "blocked_infeasible"
                        ? "bg-rose-100 dark:bg-rose-950/80 border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300"
                        : proposal.status === "queued"
                          ? "bg-amber-100 dark:bg-amber-950/80 border-amber-300 dark:border-amber-800 text-amber-800 dark:text-amber-300"
                          : "bg-blue-100 dark:bg-blue-950/80 border-blue-300 dark:border-blue-800 text-blue-800 dark:text-blue-300"
                }`}
              >
                {proposal.status.replace("_", " ")}
              </span>
            </div>
            <h1 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-50">
              {proposal.summary}
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {isPending && (
              <>
                {hasUnsavedOverrides && (
                  <button
                    onClick={handleSaveOverrides}
                    disabled={actionLoading}
                    className="px-4 py-2 text-xs font-bold uppercase tracking-wider bg-amber-600 hover:bg-amber-700 text-white rounded-xl shadow-sm transition active:scale-95"
                  >
                    Save Custom Overrides
                  </button>
                )}
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="px-4 py-2 text-xs font-bold uppercase tracking-wider border border-stone-300 dark:border-stone-700 text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-xl transition active:scale-95"
                >
                  Reject Proposal
                </button>
                <button
                  onClick={handleAccept}
                  disabled={actionLoading}
                  className="px-5 py-2 text-xs font-bold uppercase tracking-wider bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-md transition active:scale-95 flex items-center space-x-1.5"
                >
                  <span>✓</span>
                  <span>Accept & Apply</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Capacity Warning Banner */}
        {proposal.capacity_warning && (
          <div className="bg-amber-50 dark:bg-amber-950/50 border-l-4 border-amber-500 p-4 rounded-2xl shadow-sm">
            <div className="flex items-start">
              <span className="text-amber-600 dark:text-amber-400 text-xl font-bold mr-3">
                ⚠️
              </span>
              <div>
                <h3 className="text-amber-900 dark:text-amber-200 font-bold text-sm uppercase tracking-wide">
                  Capacity Constraint Exceeded
                </h3>
                <p className="text-amber-800 dark:text-amber-300 text-xs sm:text-sm mt-0.5 leading-relaxed">
                  {proposal.capacity_warning}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Infeasibility Alert Banner */}
        {isInfeasible && proposal.infeasibility_reason && (
          <div className="bg-rose-50 dark:bg-rose-950/60 border-l-4 border-rose-500 p-4 rounded-2xl shadow-sm">
            <div className="flex items-start">
              <span className="text-rose-600 dark:text-rose-400 text-xl font-bold mr-3">
                🚫
              </span>
              <div>
                <h3 className="text-rose-900 dark:text-rose-200 font-bold text-sm uppercase tracking-wide">
                  Proposal Blocked as Infeasible
                </h3>
                <p className="text-rose-800 dark:text-rose-300 text-xs sm:text-sm mt-0.5 leading-relaxed">
                  {proposal.infeasibility_reason}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Impact Summary & Plain-Language Explanation */}
        <section className="glass-card rounded-3xl p-6 sm:p-8 shadow-sm space-y-4">
          <h2 className="text-xs font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider">
            Deterministic Replanning Assessment
          </h2>
          <p className="text-stone-800 dark:text-stone-200 text-sm sm:text-base leading-relaxed">
            {proposal.explanation || proposal.summary}
          </p>

          {/* Mitigation Suggestions */}
          {proposal.mitigation_suggestions &&
            proposal.mitigation_suggestions.length > 0 && (
              <div className="mt-4 pt-4 border-t border-stone-200 dark:border-stone-800">
                <h4 className="text-xs font-bold text-stone-700 dark:text-stone-300 uppercase tracking-wider mb-2.5">
                  Recommended Mitigations:
                </h4>
                <ul className="list-disc pl-5 text-xs sm:text-sm text-stone-600 dark:text-stone-300 space-y-1.5">
                  {proposal.mitigation_suggestions.map((sug, idx) => (
                    <li key={idx}>{sug}</li>
                  ))}
                </ul>
              </div>
            )}
        </section>

        {/* Budget Items Diff Table */}
        <section className="glass-card rounded-3xl shadow-sm overflow-hidden">
          <div className="px-6 py-5 border-b border-stone-200 dark:border-stone-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-serif font-bold text-stone-900 dark:text-stone-50">
                Budget Impact Breakdown
              </h2>
              <p className="text-xs text-stone-500 dark:text-stone-400 mt-0.5">
                Calculated strictly in Python via BudgetScalingEngine (Zero LLM
                math)
              </p>
            </div>
            <div className="text-right">
              <span className="text-xs text-stone-500 dark:text-stone-400 mr-2">
                Total Delta:
              </span>
              <span
                className={`font-mono font-bold text-base ${
                  proposal.budget_total_delta > 0
                    ? "text-rose-600 dark:text-rose-400"
                    : proposal.budget_total_delta < 0
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-stone-700 dark:text-stone-300"
                }`}
              >
                {proposal.budget_total_delta >= 0 ? "+" : ""}₹
                {proposal.budget_total_delta.toLocaleString("en-IN", {
                  minimumFractionDigits: 2,
                })}
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-stone-100 dark:bg-stone-800/80 text-stone-600 dark:text-stone-300 uppercase tracking-wider border-b border-stone-200 dark:border-stone-800 font-semibold">
                <tr>
                  <th className="px-6 py-3">Category</th>
                  <th className="px-4 py-3">Scaling Rule</th>
                  <th className="px-4 py-3 text-right">Current Amount</th>
                  <th className="px-4 py-3 text-right">Proposed Amount</th>
                  <th className="px-4 py-3 text-right">Delta</th>
                  <th className="px-6 py-3">Calculation Formula</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                {proposal.budget_diff && proposal.budget_diff.length > 0 ? (
                  proposal.budget_diff.map((item) => (
                    <tr
                      key={item.budget_item_id}
                      className="hover:bg-stone-50/60 dark:hover:bg-stone-800/40 transition-colors"
                    >
                      <td className="px-6 py-4 font-semibold text-stone-900 dark:text-stone-100">
                        {item.name}
                      </td>
                      <td className="px-4 py-4">
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 text-stone-700 dark:text-stone-300 uppercase">
                          {item.scaling_rule}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-stone-600 dark:text-stone-300">
                        ₹
                        {item.old_amount.toLocaleString("en-IN", {
                          minimumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-4 py-4 text-right">
                        {isPending ? (
                          <input
                            type="number"
                            value={
                              overrides[item.budget_item_id] ?? item.new_amount
                            }
                            onChange={(e) =>
                              handleAmountChange(
                                item.budget_item_id,
                                e.target.value,
                              )
                            }
                            className="w-32 px-2.5 py-1 text-right font-mono text-stone-900 dark:text-stone-100 bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-700 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none transition-colors"
                          />
                        ) : (
                          <span className="font-mono text-stone-900 dark:text-stone-100 font-bold">
                            ₹
                            {item.new_amount.toLocaleString("en-IN", {
                              minimumFractionDigits: 2,
                            })}
                          </span>
                        )}
                      </td>
                      <td
                        className={`px-4 py-4 text-right font-mono font-bold ${
                          item.difference > 0
                            ? "text-rose-600 dark:text-rose-400"
                            : item.difference < 0
                              ? "text-emerald-600 dark:text-emerald-400"
                              : "text-stone-400"
                        }`}
                      >
                        {item.difference >= 0 ? "+" : ""}₹
                        {item.difference.toLocaleString("en-IN", {
                          minimumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-6 py-4 font-mono text-[11px] text-stone-500 dark:text-stone-400">
                        {item.formula}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-6 py-8 text-center text-stone-500 dark:text-stone-400"
                    >
                      No budget items altered in this proposal.
                    </td>
                  </tr>
                )}
              </tbody>
              <tfoot className="bg-stone-100/70 dark:bg-stone-800/60 font-semibold border-t-2 border-stone-200 dark:border-stone-800">
                <tr>
                  <td
                    colSpan={2}
                    className="px-6 py-3.5 text-stone-900 dark:text-stone-100 font-serif"
                  >
                    Total Budget Summary
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono text-stone-700 dark:text-stone-300">
                    ₹
                    {proposal.budget_total_old.toLocaleString("en-IN", {
                      minimumFractionDigits: 2,
                    })}
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono text-stone-900 dark:text-stone-100 font-bold text-sm">
                    ₹
                    {proposal.budget_total_new.toLocaleString("en-IN", {
                      minimumFractionDigits: 2,
                    })}
                  </td>
                  <td
                    className={`px-4 py-3.5 text-right font-mono font-bold text-sm ${
                      proposal.budget_total_delta > 0
                        ? "text-rose-600 dark:text-rose-400"
                        : proposal.budget_total_delta < 0
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-stone-700 dark:text-stone-300"
                    }`}
                  >
                    {proposal.budget_total_delta >= 0 ? "+" : ""}₹
                    {proposal.budget_total_delta.toLocaleString("en-IN", {
                      minimumFractionDigits: 2,
                    })}
                  </td>
                  <td className="px-6 py-3.5"></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </section>

        {/* Task Timeline Modifications */}
        {proposal.task_diff && (
          <section className="glass-card rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
            <h2 className="text-lg font-serif font-bold text-stone-900 dark:text-stone-50">
              Task Schedule & Vendor Re-Engagement
            </h2>

            {/* Moved Tasks */}
            {proposal.task_diff.moved_tasks &&
              proposal.task_diff.moved_tasks.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-2.5">
                    Shifted Milestones
                  </h3>
                  <div className="space-y-2">
                    {proposal.task_diff.moved_tasks.map((task) => (
                      <div
                        key={task.task_id}
                        className="p-3.5 rounded-xl bg-stone-50 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800 flex items-center justify-between text-xs"
                      >
                        <span className="font-semibold text-stone-900 dark:text-stone-100">
                          {task.title}
                        </span>
                        <div className="flex items-center space-x-3 text-stone-600 dark:text-stone-300 font-mono">
                          <span className="line-through text-stone-400">
                            {task.old_start}
                          </span>
                          <span>&rarr;</span>
                          <span className="font-bold text-amber-700 dark:text-amber-400">
                            {task.new_start}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 font-bold">
                            {task.days_shifted && task.days_shifted > 0
                              ? `+${task.days_shifted}d`
                              : `${task.days_shifted}d`}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Added Tasks */}
            {proposal.task_diff.added_tasks &&
              proposal.task_diff.added_tasks.length > 0 && (
                <div className="pt-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mb-2.5">
                    Newly Inserted Verification Tasks
                  </h3>
                  <div className="space-y-2">
                    {proposal.task_diff.added_tasks.map((task, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs flex justify-between items-center"
                      >
                        <div>
                          <h4 className="font-semibold text-emerald-950 dark:text-emerald-200">
                            {task.title}
                          </h4>
                          {task.description && (
                            <p className="text-emerald-800/80 dark:text-emerald-300 text-[11px] mt-0.5">
                              {task.description}
                            </p>
                          )}
                        </div>
                        <span className="font-mono text-emerald-800 dark:text-emerald-300 px-2.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/60 font-semibold">
                          {task.assigned_role}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Vendor Re-Quote Flags */}
            {proposal.vendor_re_quote_categories &&
              proposal.vendor_re_quote_categories.length > 0 && (
                <div className="pt-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-rose-700 dark:text-rose-400 mb-2">
                    Vendors Requiring Re-Quote / Capacity Check
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {proposal.vendor_re_quote_categories.map((cat, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-100 dark:bg-rose-950/80 border border-rose-300 dark:border-rose-900 text-rose-800 dark:text-rose-300"
                      >
                        ⚠️ {cat}
                      </span>
                    ))}
                  </div>
                </div>
              )}
          </section>
        )}
      </main>
    </div>
  );
}
