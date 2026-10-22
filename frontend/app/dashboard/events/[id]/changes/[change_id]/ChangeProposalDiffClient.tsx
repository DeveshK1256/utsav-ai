'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://utsav-ai-ycg2.onrender.com/api/v1';

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
  added_tasks: Array<{ title: string; description?: string; assigned_role?: string; duration_minutes?: number }>;
  moved_tasks: Array<{ task_id: string; title: string; old_start?: string; new_start?: string; days_shifted?: number; formula?: string }>;
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
  const eventId = (params?.id as string) || '';
  const changeId = (params?.change_id as string) || '';

  const [proposal, setProposal] = useState<ChangeProposal | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [hasUnsavedOverrides, setHasUnsavedOverrides] = useState<boolean>(false);

  useEffect(() => {
    if (eventId && changeId && changeId !== 'default') {
      fetchProposal();
    } else {
      setLoading(false);
    }
  }, [eventId, changeId]);

  const fetchProposal = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/changes/${changeId}`);
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
    } catch (err: any) {
      setError(err.message || 'Error fetching change proposal');
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async () => {
    if (!confirm('Are you sure you want to accept and apply these changes to the master plan?')) return;
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/changes/${changeId}/accept`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to accept proposal');
      }
      const updated = await res.json();
      setProposal(updated);
      alert('Plan B changes successfully applied to your master budget and schedule!');
    } catch (err: any) {
      alert(`Acceptance error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!confirm('Reject this proposal? The master budget and schedule will remain unchanged.')) return;
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/changes/${changeId}/reject`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to reject proposal');
      }
      const updated = await res.json();
      setProposal(updated);
      alert('Change proposal rejected. Master plan untouched.');
    } catch (err: any) {
      alert(`Rejection error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveOverrides = async () => {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/changes/${changeId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ budget_overrides: overrides })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to patch proposal');
      }
      const updated = await res.json();
      setProposal(updated);
      setHasUnsavedOverrides(false);
      alert('Manual overrides saved to proposal!');
    } catch (err: any) {
      alert(`Override error: ${err.message}`);
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
      <div className="min-h-screen bg-stone-50 flex items-center justify-center p-6">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-amber-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-stone-600 font-medium">Evaluating plan modifications & deterministic impact...</p>
        </div>
      </div>
    );
  }

  if (error || !proposal) {
    return (
      <div className="min-h-screen bg-stone-50 p-6 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow p-8 max-w-lg text-center border border-stone-200">
          <div className="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4 font-bold text-xl">!</div>
          <h2 className="text-xl font-bold text-stone-800 mb-2">Plan B Replanning Diff</h2>
          <p className="text-stone-600 mb-6">{error || 'Enter an active event and change ID to view the proposal diff.'}</p>
          <Link href="/dashboard" className="px-5 py-2.5 bg-stone-800 text-white rounded-lg hover:bg-stone-900 transition">
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const isPending = proposal.status === 'pending';
  const isInfeasible = proposal.status === 'blocked_infeasible';

  return (
    <div className="min-h-screen bg-stone-50 text-stone-900 pb-16">
      {/* Header bar */}
      <header className="bg-white border-b border-stone-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <Link href="/dashboard" className="text-stone-500 hover:text-stone-800 text-sm font-medium">
                &larr; Event Plan
              </Link>
              <span className="text-stone-300">/</span>
              <span className="text-sm font-semibold text-amber-700 uppercase tracking-wider">Plan B Replanning</span>
            </div>
            <h1 className="text-2xl font-bold text-stone-900 mt-1">{proposal.summary}</h1>
          </div>

          <div className="flex items-center gap-3">
            <span
              className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                proposal.status === 'applied'
                  ? 'bg-emerald-100 text-emerald-800'
                  : proposal.status === 'rejected'
                  ? 'bg-stone-200 text-stone-700'
                  : proposal.status === 'blocked_infeasible'
                  ? 'bg-rose-100 text-rose-800'
                  : proposal.status === 'queued'
                  ? 'bg-amber-100 text-amber-800'
                  : 'bg-blue-100 text-blue-800'
              }`}
            >
              Status: {proposal.status.replace('_', ' ')}
            </span>

            {isPending && (
              <>
                {hasUnsavedOverrides && (
                  <button
                    onClick={handleSaveOverrides}
                    disabled={actionLoading}
                    className="px-4 py-2 text-sm font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition"
                  >
                    Save Custom Overrides
                  </button>
                )}
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="px-4 py-2 text-sm font-medium border border-stone-300 text-stone-700 rounded-lg hover:bg-stone-100 transition"
                >
                  Reject Proposal
                </button>
                <button
                  onClick={handleAccept}
                  disabled={actionLoading}
                  className="px-5 py-2 text-sm font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 shadow-sm transition"
                >
                  Accept & Apply to Plan
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Capacity Warning Banner */}
        {proposal.capacity_warning && (
          <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-lg shadow-sm">
            <div className="flex items-start">
              <span className="text-amber-600 text-xl font-bold mr-3">⚠️</span>
              <div>
                <h3 className="text-amber-900 font-bold text-sm uppercase tracking-wide">Capacity Constraint Exceeded</h3>
                <p className="text-amber-800 text-sm mt-1">{proposal.capacity_warning}</p>
              </div>
            </div>
          </div>
        )}

        {/* Infeasibility Alert Banner */}
        {isInfeasible && proposal.infeasibility_reason && (
          <div className="bg-rose-50 border-l-4 border-rose-500 p-4 rounded-r-lg shadow-sm">
            <div className="flex items-start">
              <span className="text-rose-600 text-xl font-bold mr-3">🚫</span>
              <div>
                <h3 className="text-rose-900 font-bold text-sm uppercase tracking-wide">Proposal Blocked as Infeasible</h3>
                <p className="text-rose-800 text-sm mt-1">{proposal.infeasibility_reason}</p>
              </div>
            </div>
          </div>
        )}

        {/* Impact Summary & Plain-Language Explanation */}
        <section className="bg-white rounded-xl shadow-sm border border-stone-200 p-6">
          <h2 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">Replanning Assessment</h2>
          <p className="text-stone-800 text-base leading-relaxed">{proposal.explanation || proposal.summary}</p>

          {/* Mitigation Suggestions */}
          {proposal.mitigation_suggestions && proposal.mitigation_suggestions.length > 0 && (
            <div className="mt-4 pt-4 border-t border-stone-100">
              <h4 className="text-xs font-semibold text-amber-800 uppercase tracking-wider mb-2">Recommended Mitigations:</h4>
              <ul className="list-disc pl-5 text-sm text-stone-700 space-y-1">
                {proposal.mitigation_suggestions.map((sug, idx) => (
                  <li key={idx}>{sug}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Budget Items Diff Table */}
        <section className="bg-white rounded-xl shadow-sm border border-stone-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-stone-100 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-stone-800">Budget Impact Breakdown</h2>
              <p className="text-xs text-stone-500 mt-0.5">Calculated strictly via deterministic scaling rules — zero hallucinated math</p>
            </div>
            <div className="text-right">
              <div className="text-xs text-stone-500 uppercase">Net Budget Shift</div>
              <div
                className={`text-lg font-bold ${
                  proposal.budget_total_delta > 0
                    ? 'text-rose-600'
                    : proposal.budget_total_delta < 0
                    ? 'text-emerald-600'
                    : 'text-stone-700'
                }`}
              >
                {proposal.budget_total_delta >= 0 ? '+' : ''}₹{proposal.budget_total_delta.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-stone-600">
              <thead className="bg-stone-100 text-stone-700 text-xs uppercase font-semibold border-b border-stone-200">
                <tr>
                  <th className="px-6 py-3">Category & Item</th>
                  <th className="px-4 py-3">Rule</th>
                  <th className="px-4 py-3 text-right">Old Budget</th>
                  <th className="px-4 py-3 text-right">Revised Proposal</th>
                  <th className="px-4 py-3 text-right">Delta</th>
                  <th className="px-6 py-3">Transparent Formula</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {proposal.budget_diff && proposal.budget_diff.length > 0 ? (
                  proposal.budget_diff.map((item) => {
                    return (
                      <tr key={item.budget_item_id} className="hover:bg-stone-50/80 transition">
                        <td className="px-6 py-4 font-medium text-stone-900">
                          <div>{item.name}</div>
                          <span className="text-xs text-stone-500 uppercase tracking-wider">{item.category}</span>
                        </td>
                        <td className="px-4 py-4">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-semibold ${
                              item.scaling_rule === 'per_guest'
                                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                : item.scaling_rule === 'tiered'
                                ? 'bg-purple-50 text-purple-700 border border-purple-200'
                                : 'bg-stone-100 text-stone-700'
                            }`}
                          >
                            {item.scaling_rule}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-right font-mono text-stone-600">
                          ₹{item.old_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-4 text-right">
                          {isPending ? (
                            <input
                              type="number"
                              value={overrides[item.budget_item_id] ?? item.new_amount}
                              onChange={(e) => handleAmountChange(item.budget_item_id, e.target.value)}
                              className="w-32 px-2 py-1 text-right font-mono text-stone-900 border border-stone-300 rounded focus:ring-1 focus:ring-amber-500 focus:outline-none"
                            />
                          ) : (
                            <span className="font-mono text-stone-900 font-semibold">
                              ₹{item.new_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </span>
                          )}
                        </td>
                        <td
                          className={`px-4 py-4 text-right font-mono font-bold ${
                            item.difference > 0 ? 'text-rose-600' : item.difference < 0 ? 'text-emerald-600' : 'text-stone-400'
                          }`}
                        >
                          {item.difference >= 0 ? '+' : ''}₹{item.difference.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-6 py-4 font-mono text-xs text-stone-500 bg-stone-50/50">
                          {item.formula}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6} className="px-6 py-6 text-center text-stone-500">
                      No budget items altered in this proposal.
                    </td>
                  </tr>
                )}
              </tbody>
              <tfoot className="bg-stone-50 font-semibold border-t-2 border-stone-200">
                <tr>
                  <td colSpan={2} className="px-6 py-3 text-stone-800">Total Budget Summary</td>
                  <td className="px-4 py-3 text-right font-mono text-stone-700">
                    ₹{proposal.budget_total_old.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-stone-900 font-bold">
                    ₹{proposal.budget_total_new.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td
                    className={`px-4 py-3 text-right font-mono font-bold ${
                      proposal.budget_total_delta > 0 ? 'text-rose-600' : proposal.budget_total_delta < 0 ? 'text-emerald-600' : 'text-stone-700'
                    }`}
                  >
                    {proposal.budget_total_delta >= 0 ? '+' : ''}₹{proposal.budget_total_delta.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-3"></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </section>

        {/* Task & Schedule Shifts */}
        {((proposal.task_diff?.moved_tasks && proposal.task_diff.moved_tasks.length > 0) ||
          (proposal.task_diff?.added_tasks && proposal.task_diff.added_tasks.length > 0)) && (
          <section className="bg-white rounded-xl shadow-sm border border-stone-200 p-6">
            <h2 className="text-lg font-bold text-stone-800 mb-4">Schedule & Task Adjustments</h2>

            {/* Moved Tasks */}
            {proposal.task_diff.moved_tasks?.length > 0 && (
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">Shifted Tasks</h3>
                <div className="space-y-2">
                  {proposal.task_diff.moved_tasks.map((t, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-stone-50 rounded-lg border border-stone-200 text-sm">
                      <span className="font-medium text-stone-800">{t.title}</span>
                      <span className="font-mono text-xs text-stone-600">
                        Shifted {t.days_shifted && t.days_shifted > 0 ? `+${t.days_shifted}` : t.days_shifted} days ({t.new_start ? t.new_start.split('T')[0] : ''})
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Added Emergency Sourcing Tasks */}
            {proposal.task_diff.added_tasks?.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-amber-800 uppercase tracking-wider mb-2">Emergency Sourcing & Procurement Tasks</h3>
                <div className="space-y-2">
                  {proposal.task_diff.added_tasks.map((t, idx) => (
                    <div key={idx} className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-sm">
                      <div className="flex items-center justify-between font-medium text-amber-950">
                        <span>{t.title}</span>
                        <span className="text-xs bg-amber-200/80 px-2 py-0.5 rounded text-amber-900">{t.assigned_role || 'Lead'}</span>
                      </div>
                      {t.description && <p className="text-xs text-amber-800 mt-1">{t.description}</p>}
                    </div>
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
