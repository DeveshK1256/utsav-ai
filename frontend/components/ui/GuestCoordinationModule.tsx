'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { getAuthHeaders } from '@/lib/auth';

interface Guest {
  id: string;
  name: string;
  phone: string;
  group_side?: string;
  diet?: string;
  mobility_needs?: boolean;
  kids_count?: number;
  headcount: number;
  rsvp_status: string;
  accommodation?: boolean;
  language?: string;
  notes?: string;
  needs_host_review?: boolean;
  created_at: string;
}

interface RSVPSummary {
  total_guests: number;
  attending_count: number;
  declined_count: number;
  maybe_count: number;
  pending_count: number;
  total_confirmed_headcount: number;
  diet_breakdown: { [key: string]: number };
  mobility_needs_count: number;
  kids_count: number;
  accommodation_needed_count: number;
}

interface FactSheet {
  venue_address?: string;
  parking_info?: string;
  dress_code?: string;
  timing_notes?: string;
  map_link?: string;
  other_facts?: { [key: string]: any };
}

interface GuestCoordinationModuleProps {
  eventId: string;
  eventName: string;
  apiBase: string;
}

export function GuestCoordinationModule({ eventId, eventName, apiBase }: GuestCoordinationModuleProps) {
  const [guests, setGuests] = useState<Guest[]>([]);
  const [summary, setSummary] = useState<RSVPSummary | null>(null);
  const [factSheet, setFactSheet] = useState<FactSheet>({});
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Modals state
  const [isImportModalOpen, setIsImportModalOpen] = useState<boolean>(false);
  const [isFactSheetModalOpen, setIsFactSheetModalOpen] = useState<boolean>(false);
  const [isSendingInvites, setIsSendingInvites] = useState<boolean>(false);

  // Trigger and modal refs for accessible focus trapping & restoration
  const importTriggerRef = useRef<HTMLButtonElement | null>(null);
  const factSheetTriggerRef = useRef<HTMLButtonElement | null>(null);
  const importModalRef = useRef<HTMLDivElement | null>(null);
  const factSheetModalRef = useRef<HTMLDivElement | null>(null);

  // Focus trap & restore for Import Modal
  useEffect(() => {
    if (isImportModalOpen) {
      // Focus first element after modal DOM node mounts
      setTimeout(() => {
        const modalEl = importModalRef.current;
        if (modalEl) {
          const focusable = modalEl.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          );
          if (focusable.length > 0) focusable[0].focus();
        }
      }, 50);

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape' || e.key === 'Esc') {
          e.preventDefault();
          console.log('[DEBUG-MODAL] Escape key pressed, closing import modal');
          setIsImportModalOpen(false);
          importTriggerRef.current?.focus();
          return;
        }

        if (e.key === 'Tab') {
          const modalEl = importModalRef.current;
          if (!modalEl) return;
          const focusable = Array.from(modalEl.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          ));
          if (focusable.length === 0) return;
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (e.shiftKey) {
            if (document.activeElement === first || document.activeElement === modalEl) {
              e.preventDefault();
              last.focus();
            }
          } else {
            if (document.activeElement === last) {
              e.preventDefault();
              first.focus();
            }
          }
        }
      };

      window.addEventListener('keydown', handleKeyDown, true);
      return () => {
        window.removeEventListener('keydown', handleKeyDown, true);
      };
    }
  }, [isImportModalOpen]);

  // Focus trap & restore for Fact Sheet Modal
  useEffect(() => {
    if (isFactSheetModalOpen) {
      setTimeout(() => {
        const modalEl = factSheetModalRef.current;
        if (modalEl) {
          const focusable = modalEl.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          );
          if (focusable.length > 0) focusable[0].focus();
        }
      }, 50);

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape' || e.key === 'Esc') {
          e.preventDefault();
          setIsFactSheetModalOpen(false);
          factSheetTriggerRef.current?.focus();
          return;
        }

        if (e.key === 'Tab') {
          const modalEl = factSheetModalRef.current;
          if (!modalEl) return;
          const focusable = Array.from(modalEl.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          ));
          if (focusable.length === 0) return;
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (e.shiftKey) {
            if (document.activeElement === first || document.activeElement === modalEl) {
              e.preventDefault();
              last.focus();
            }
          } else {
            if (document.activeElement === last) {
              e.preventDefault();
              first.focus();
            }
          }
        }
      };

      window.addEventListener('keydown', handleKeyDown, true);
      return () => {
        window.removeEventListener('keydown', handleKeyDown, true);
      };
    }
  }, [isFactSheetModalOpen]);

  // Import form state
  const [importText, setImportText] = useState<string>('');
  const [importErrors, setImportErrors] = useState<any[]>([]);

  // Fetch all guest data
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [gRes, sRes, fRes] = await Promise.all([
        fetch(`${apiBase}/events/${eventId}/guests`, { headers: getAuthHeaders(eventId) }),
        fetch(`${apiBase}/events/${eventId}/guests/rsvp-summary`, { headers: getAuthHeaders(eventId) }),
        fetch(`${apiBase}/events/${eventId}/fact-sheet`, { headers: getAuthHeaders(eventId) })
      ]);

      if (gRes.ok) {
        setGuests(await gRes.json());
      }
      if (sRes.ok) {
        setSummary(await sRes.json());
      }
      if (fRes.ok) {
        setFactSheet(await fRes.json());
      }
    } catch (err: any) {
      console.error('Failed to load guest data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [apiBase, eventId]);

  useEffect(() => {
    if (eventId && eventId !== 'default') {
      fetchData();
    }
  }, [fetchData, eventId]);

  // Handle Send Batch Invitations
  const handleSendInvitations = async () => {
    if (!confirm('Send WhatsApp invitation templates to all pending guests? This will check opt-outs before sending.')) {
      return;
    }

    setIsSendingInvites(true);
    setActionMessage(null);
    try {
      const res = await fetch(`${apiBase}/events/${eventId}/guests/send-invitations`, {
        method: 'POST',
        headers: getAuthHeaders(eventId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify({})
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const result = await res.json();
      setActionMessage({
        type: 'success',
        text: `Invitations processed! Sent: ${result.sent_count}, Blocked by opt-outs: ${result.blocked_opt_out_count}, Failed: ${result.failed_count}.`
      });
      fetchData();
    } catch (e: any) {
      setActionMessage({
        type: 'error',
        text: `Failed to trigger WhatsApp invitations: ${e.message || 'Network error'}`
      });
    } finally {
      setIsSendingInvites(false);
    }
  };

  // Handle Manual/Pasted Guest Import
  const handleImportSubmit = async () => {
    setImportErrors([]);
    if (!importText.trim()) return;

    // Parse CSV or line-by-line: Name, Phone, Group/Side, Diet, Kids
    const lines = importText.trim().split('\n');
    const rows = lines.map(line => {
      const parts = line.split(',').map(p => p.trim());
      return {
        name: parts[0] || '',
        phone: parts[1] || '',
        group_side: parts[2] || 'general',
        diet: parts[3] || 'veg',
        kids_count: parseInt(parts[4] || '0', 10) || 0
      };
    });

    try {
      const res = await fetch(`${apiBase}/events/${eventId}/guests/import`, {
        method: 'POST',
        headers: getAuthHeaders(eventId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify({ guests: rows })
      });

      const data = await res.json();
      if (res.ok) {
        if (data.invalid_rows_count > 0) {
          setImportErrors(data.errors || []);
          setActionMessage({
            type: 'info',
            text: `Imported ${data.successful_count} guests. ${data.skipped_duplicates_count} duplicates skipped. ${data.invalid_rows_count} rows rejected due to invalid numbers.`
          });
        } else {
          setActionMessage({
            type: 'success',
            text: `Successfully imported ${data.successful_count} guests (${data.skipped_duplicates_count} duplicates skipped).`
          });
          setIsImportModalOpen(false);
          setImportText('');
        }
        fetchData();
      } else {
        setActionMessage({
          type: 'error',
          text: data.detail || 'Failed to import guests.'
        });
      }
    } catch (e: any) {
      setActionMessage({
        type: 'error',
        text: `Network error during guest import: ${e.message}`
      });
    }
  };

  // Handle Fact Sheet Save
  const handleSaveFactSheet = async () => {
    try {
      const res = await fetch(`${apiBase}/events/${eventId}/fact-sheet`, {
        method: 'POST',
        headers: getAuthHeaders(eventId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify(factSheet)
      });
      if (res.ok) {
        setActionMessage({
          type: 'success',
          text: 'Verified event fact sheet saved. WhatsApp Concierge bot will now answer guest FAQs from this data.'
        });
        setIsFactSheetModalOpen(false);
      }
    } catch (e: any) {
      setActionMessage({
        type: 'error',
        text: `Failed to update fact sheet: ${e.message}`
      });
    }
  };

  // Handle Guest Privacy Purge
  const handleDeleteGuest = async (guestId: string, guestName: string) => {
    if (!confirm(`Purge all personal data for "${guestName}" per privacy policy? This action is permanent.`)) {
      return;
    }

    try {
      const res = await fetch(`${apiBase}/events/${eventId}/guests/${guestId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(eventId)
      });
      if (res.ok) {
        setActionMessage({
          type: 'success',
          text: `Guest data for "${guestName}" permanently deleted.`
        });
        fetchData();
      }
    } catch (e: any) {
      setActionMessage({
        type: 'error',
        text: `Failed to delete guest: ${e.message}`
      });
    }
  };

  // Filtered guests
  const filteredGuests = guests.filter(g => {
    if (activeFilter === 'all') return true;
    return g.rsvp_status.toLowerCase() === activeFilter.toLowerCase();
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Action Message Toast */}
      {actionMessage && (
        <div className={`p-4 rounded-2xl text-xs font-semibold flex items-center justify-between border ${
          actionMessage.type === 'success' 
            ? 'bg-emerald-50 text-emerald-900 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
            : actionMessage.type === 'error'
            ? 'bg-rose-50 text-rose-900 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800'
            : 'bg-amber-50 text-amber-900 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800'
        }`}>
          <span>{actionMessage.text}</span>
          <button onClick={() => setActionMessage(null)} className="ml-3 hover:opacity-75">✕</button>
        </div>
      )}

      {/* Header Controls & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-5 rounded-3xl glass-card border border-stone-200/80 dark:border-stone-800/80">
        <div>
          <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-50 flex items-center gap-2">
            <span>💌</span> WhatsApp Guest Concierge & RSVP Hub
          </h3>
          <p className="text-xs text-stone-500 dark:text-stone-400 mt-0.5">
            Zero-app guest coordination via Meta WhatsApp Business Cloud API with deterministic opt-out safety.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            ref={factSheetTriggerRef}
            onClick={() => setIsFactSheetModalOpen(true)}
            className="px-4 py-2 rounded-xl bg-stone-100 hover:bg-stone-200 dark:bg-stone-800 dark:hover:bg-stone-700 text-stone-800 dark:text-stone-200 text-xs font-semibold transition-colors flex items-center gap-1.5"
          >
            <span>📋</span> Fact Sheet Editor
          </button>

          <button
            ref={importTriggerRef}
            onClick={() => setIsImportModalOpen(true)}
            className="px-4 py-2 rounded-xl bg-stone-100 hover:bg-stone-200 dark:bg-stone-800 dark:hover:bg-stone-700 text-stone-800 dark:text-stone-200 text-xs font-semibold transition-colors flex items-center gap-1.5"
          >
            <span>📥</span> Import Guests
          </button>

          <button
            onClick={handleSendInvitations}
            disabled={isSendingInvites || guests.length === 0}
            className="px-5 py-2 rounded-xl bg-[#8B1E28] hover:bg-[#721921] text-white text-xs font-semibold shadow-xs disabled:opacity-50 transition-all flex items-center gap-1.5"
          >
            <span>⚡</span> {isSendingInvites ? 'Transmitting Invites...' : 'Broadcast WhatsApp Invites'}
          </button>
        </div>
      </div>

      {/* Live RSVP Summary Cards (Deterministic Metrics) */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
        <div className="glass-card p-4 rounded-2xl border border-stone-200/80 dark:border-stone-800/80 space-y-1">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-stone-500">Total Roster</div>
          <div className="text-2xl font-bold font-serif text-stone-900 dark:text-stone-50">
            {summary?.total_guests || 0}
          </div>
          <div className="text-[10px] text-stone-400">Imported guests</div>
        </div>

        <div className="glass-card p-4 rounded-2xl border border-emerald-200/60 dark:border-emerald-900/60 bg-emerald-50/20 space-y-1">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-emerald-800 dark:text-emerald-400">Attending</div>
          <div className="text-2xl font-bold font-serif text-emerald-700 dark:text-emerald-400">
            {summary?.attending_count || 0}
          </div>
          <div className="text-[10px] text-emerald-600 dark:text-emerald-500 font-medium">
            {summary?.total_confirmed_headcount || 0} confirmed seats
          </div>
        </div>

        <div className="glass-card p-4 rounded-2xl border border-stone-200/80 dark:border-stone-800/80 space-y-1">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400">Maybe</div>
          <div className="text-2xl font-bold font-serif text-amber-700 dark:text-amber-400">
            {summary?.maybe_count || 0}
          </div>
          <div className="text-[10px] text-amber-600/80">Tentative replies</div>
        </div>

        <div className="glass-card p-4 rounded-2xl border border-stone-200/80 dark:border-stone-800/80 space-y-1">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-rose-700 dark:text-rose-400">Declined</div>
          <div className="text-2xl font-bold font-serif text-rose-700 dark:text-rose-400">
            {summary?.declined_count || 0}
          </div>
          <div className="text-[10px] text-rose-600/80">Cannot attend</div>
        </div>

        <div className="glass-card p-4 rounded-2xl border border-stone-200/80 dark:border-stone-800/80 space-y-1">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-stone-500">Pending</div>
          <div className="text-2xl font-bold font-serif text-stone-600 dark:text-stone-300">
            {summary?.pending_count || 0}
          </div>
          <div className="text-[10px] text-stone-400">Awaiting RSVP</div>
        </div>
      </div>

      {/* Dietary & Hospitality Breakdown Bar */}
      {summary && (
        <div className="p-4 rounded-2xl glass-card border border-stone-200/70 dark:border-stone-800/70 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-stone-800 dark:text-stone-200">Catering Breakdown:</span>
            <span className="px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 font-medium">
              Pure Veg: {summary.diet_breakdown?.veg || 0}
            </span>
            <span className="px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 font-medium">
              Jain: {summary.diet_breakdown?.jain || 0}
            </span>
            <span className="px-2 py-0.5 rounded-md bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 font-medium">
              Non-Veg: {summary.diet_breakdown?.non_veg || 0}
            </span>
          </div>

          <div className="flex items-center gap-3 text-stone-600 dark:text-stone-300 font-medium">
            <span>♿ Wheelchair: {summary.mobility_needs_count || 0}</span>
            <span>👶 Children: {summary.kids_count || 0}</span>
            <span>🏨 Accommodation: {summary.accommodation_needed_count || 0}</span>
          </div>
        </div>
      )}

      {/* WhatsApp Compliance & Opt-Out Notice */}
      <div className="p-4 rounded-2xl bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-900/60 flex items-start gap-3">
        <span className="text-base">🛡️</span>
        <div className="text-xs text-amber-900 dark:text-amber-200 space-y-1">
          <div className="font-bold">WhatsApp Business Opt-Out & Privacy Guardrail (F3 Requirement)</div>
          <p className="leading-relaxed">
            All outbound broadcasts are rate-limited to 20 msg/sec. If any guest replies with <strong>&quot;STOP&quot;</strong>, they are immediately added to the send-layer blocklist and will never receive further automated messages. Individual guest PII can be purged at any time using the Delete action below.
          </p>
        </div>
      </div>

      {/* Guest Roster Table */}
      <div className="glass-card rounded-3xl border border-stone-200/80 dark:border-stone-800/80 overflow-hidden shadow-xs">
        {/* Table Filter Tabs */}
        <div className="flex items-center justify-between p-4 border-b border-stone-200/60 dark:border-stone-800/60 overflow-x-auto gap-2">
          <div className="flex items-center gap-1.5">
            {['all', 'attending', 'pending', 'maybe', 'declined'].map(filterKey => (
              <button
                key={filterKey}
                onClick={() => setActiveFilter(filterKey)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold capitalize transition-colors ${
                  activeFilter === filterKey
                    ? 'bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900 shadow-xs'
                    : 'text-stone-500 hover:text-stone-900 dark:hover:text-stone-200'
                }`}
              >
                {filterKey} ({filterKey === 'all' ? guests.length : guests.filter(g => g.rsvp_status.toLowerCase() === filterKey).length})
              </button>
            ))}
          </div>
          <span className="text-xs text-stone-400 font-mono">
            Showing {filteredGuests.length} of {guests.length}
          </span>
        </div>

        {/* Table Body */}
        {filteredGuests.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-stone-50 dark:bg-stone-900/40 text-stone-500 uppercase tracking-wider font-semibold border-b border-stone-200/60 dark:border-stone-800/60">
                <tr>
                  <th className="py-3 px-4">Guest Name</th>
                  <th className="py-3 px-4">WhatsApp Phone</th>
                  <th className="py-3 px-4">Side / Group</th>
                  <th className="py-3 px-4">RSVP Status</th>
                  <th className="py-3 px-4">Headcount</th>
                  <th className="py-3 px-4">Diet & Hospitality</th>
                  <th className="py-3 px-4 text-right">Privacy Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200/60 dark:divide-stone-800/60">
                {filteredGuests.map(g => (
                  <tr key={g.id} className="hover:bg-stone-50/50 dark:hover:bg-stone-900/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                      <span>{g.name}</span>
                      {g.needs_host_review && (
                        <span className="px-1.5 py-0.5 rounded-md bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 text-[10px] font-bold">
                          Review Needed
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-stone-600 dark:text-stone-400">
                      {g.phone}
                    </td>
                    <td className="py-3 px-4 capitalize text-stone-600 dark:text-stone-400">
                      {g.group_side || 'general'}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold inline-block capitalize ${
                        g.rsvp_status === 'attending'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                          : g.rsvp_status === 'declined'
                          ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                          : g.rsvp_status === 'maybe'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                          : 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300'
                      }`}>
                        {g.rsvp_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-semibold text-stone-900 dark:text-stone-100">
                      {g.headcount}
                    </td>
                    <td className="py-3 px-4 space-x-1.5">
                      <span className="capitalize px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 text-[10px]">
                        {g.diet || 'veg'}
                      </span>
                      {g.mobility_needs && (
                        <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300 text-[10px]">
                          ♿ Wheelchair
                        </span>
                      )}
                      {(g.kids_count || 0) > 0 && (
                        <span className="px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300 text-[10px]">
                          👶 {g.kids_count} Kids
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDeleteGuest(g.id, g.name)}
                        className="px-2.5 py-1 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-[11px] font-medium transition-colors"
                        title="Purge personal data per privacy policy"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center space-y-3">
            <div className="text-3xl">👥</div>
            <div className="font-serif font-bold text-base text-stone-800 dark:text-stone-200">
              No guests found matching this filter
            </div>
            <p className="text-xs text-stone-500 max-w-sm mx-auto">
              Import your guest contacts via CSV or text to start sending WhatsApp digital invitations and tracking live RSVPs.
            </p>
          </div>
        )}
      </div>

      {/* Guest Import Modal */}
      {isImportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn">
          <div
            ref={importModalRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="import-modal-title"
            onKeyDown={(e) => {
              if (e.key === 'Escape' || e.key === 'Esc') {
                e.stopPropagation();
                setIsImportModalOpen(false);
                importTriggerRef.current?.focus();
              }
            }}
            className="glass-card max-w-xl w-full p-6 sm:p-7 rounded-3xl shadow-xl border border-stone-200 dark:border-stone-800 space-y-5 animate-scaleUp"
          >
            <div className="flex items-center justify-between pb-3 border-b border-stone-200/60 dark:border-stone-800/60">
              <h3 id="import-modal-title" className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100 flex items-center gap-2">
                <span>📥</span> Import Guest Roster
              </h3>
              <button
                onClick={() => {
                  setIsImportModalOpen(false);
                  importTriggerRef.current?.focus();
                }}
                aria-label="Close import dialog"
                className="text-stone-400 hover:text-stone-700 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-stone-600 dark:text-stone-400">
                Paste one guest per line in the format: <br />
                <code className="p-1 rounded bg-stone-100 dark:bg-stone-800 text-stone-900 dark:text-stone-100 font-mono">
                  Full Name, Phone Number, Group/Side, Diet (veg/jain/non_veg), Kids Count
                </code>
              </p>
              <textarea
                value={importText}
                onChange={e => setImportText(e.target.value)}
                placeholder="Rohan Sharma, +919876543210, groom, veg, 0&#10;Priya Patel, 9822233344, bride, jain, 1&#10;Sunil Verma, 09811122233, general, non_veg, 2"
                rows={6}
                className="w-full p-3.5 rounded-2xl bg-stone-50 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 font-mono text-xs text-stone-900 dark:text-stone-100 focus:outline-none focus:ring-2 focus:ring-[#8B1E28]"
              />

              {/* Validation Errors Preview */}
              {importErrors.length > 0 && (
                <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 space-y-1.5">
                  <div className="font-bold text-rose-900 dark:text-rose-200 text-xs">
                    ⚠️ {importErrors.length} rows rejected due to phone validation errors:
                  </div>
                  <div className="max-h-28 overflow-y-auto space-y-1 text-[11px] text-rose-800 dark:text-rose-300 font-mono">
                    {importErrors.map((err, i) => (
                      <div key={i}>
                        Row {err.row_number}: &quot;{err.name}&quot; ({err.phone_raw || 'empty'}) — {err.reason}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setIsImportModalOpen(false);
                  importTriggerRef.current?.focus();
                }}
                className="px-4 py-2 rounded-xl text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-200 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleImportSubmit}
                disabled={!importText.trim()}
                className="px-5 py-2 rounded-xl bg-[#8B1E28] hover:bg-[#721921] text-white text-xs font-semibold shadow-xs disabled:opacity-50"
              >
                Validate & Import
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fact Sheet Editor Modal */}
      {isFactSheetModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn">
          <div
            ref={factSheetModalRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="factsheet-modal-title"
            onKeyDown={(e) => {
              if (e.key === 'Escape' || e.key === 'Esc') {
                e.stopPropagation();
                setIsFactSheetModalOpen(false);
                factSheetTriggerRef.current?.focus();
              }
            }}
            className="glass-card max-w-xl w-full p-6 sm:p-7 rounded-3xl shadow-xl border border-stone-200 dark:border-stone-800 space-y-5 animate-scaleUp max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between pb-3 border-b border-stone-200/60 dark:border-stone-800/60">
              <h3 id="factsheet-modal-title" className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100 flex items-center gap-2">
                <span>📋</span> Verified Event Fact Sheet
              </h3>
              <button
                onClick={() => {
                  setIsFactSheetModalOpen(false);
                  factSheetTriggerRef.current?.focus();
                }}
                aria-label="Close fact sheet dialog"
                className="text-stone-400 hover:text-stone-700 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <p className="text-stone-600 dark:text-stone-400 text-[11px] leading-relaxed">
                The AI Guest Concierge bot strictly answers questions using only the facts specified below. Any out-of-scope question will be politely deferred to the host.
              </p>

              <div>
                <label className="block text-[11px] font-semibold text-stone-700 dark:text-stone-300 mb-1">
                  Venue Full Address
                </label>
                <input
                  type="text"
                  value={factSheet.venue_address || ''}
                  onChange={e => setFactSheet({ ...factSheet, venue_address: e.target.value })}
                  placeholder="e.g. Grand Heritage Palace, MG Road, Jaipur"
                  className="w-full p-2.5 rounded-xl bg-stone-50 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-xs"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-stone-700 dark:text-stone-300 mb-1">
                  Google Maps Link
                </label>
                <input
                  type="url"
                  value={factSheet.map_link || ''}
                  onChange={e => setFactSheet({ ...factSheet, map_link: e.target.value })}
                  placeholder="https://maps.google.com/?q=..."
                  className="w-full p-2.5 rounded-xl bg-stone-50 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-stone-700 dark:text-stone-300 mb-1">
                  Parking & Valet Information
                </label>
                <input
                  type="text"
                  value={factSheet.parking_info || ''}
                  onChange={e => setFactSheet({ ...factSheet, parking_info: e.target.value })}
                  placeholder="e.g. Complimentary valet parking available at Gate 2"
                  className="w-full p-2.5 rounded-xl bg-stone-50 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-xs"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-stone-700 dark:text-stone-300 mb-1">
                  Dress Code & Attire Palette
                </label>
                <input
                  type="text"
                  value={factSheet.dress_code || ''}
                  onChange={e => setFactSheet({ ...factSheet, dress_code: e.target.value })}
                  placeholder="e.g. Royal Traditional Indian / Pastel Ethnic"
                  className="w-full p-2.5 rounded-xl bg-stone-50 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-xs"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-stone-700 dark:text-stone-300 mb-1">
                  Key Timings & Assembly Notes
                </label>
                <textarea
                  value={factSheet.timing_notes || ''}
                  onChange={e => setFactSheet({ ...factSheet, timing_notes: e.target.value })}
                  placeholder="e.g. Baraat arrives at 5:30 PM; Pheras scheduled at 8:00 PM; Dinner served from 8:30 PM."
                  rows={3}
                  className="w-full p-2.5 rounded-xl bg-stone-50 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-stone-200/60 dark:border-stone-800/60">
              <button
                onClick={() => {
                  setIsFactSheetModalOpen(false);
                  factSheetTriggerRef.current?.focus();
                }}
                className="px-4 py-2 rounded-xl text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-200 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveFactSheet}
                className="px-5 py-2 rounded-xl bg-[#8B1E28] hover:bg-[#721921] text-white text-xs font-semibold shadow-xs"
              >
                Save Fact Sheet
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
