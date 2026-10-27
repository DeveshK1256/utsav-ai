'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Navbar } from '@/components/ui/Navbar';
import { getAuthHeaders, getEventOwnerToken } from '@/lib/auth';

interface LineItem {
  name: string;
  qty: number;
  unit: string;
  unit_price: number;
  total: number;
  category_tag?: string;
  notes?: string;
}

interface HiddenCostAlert {
  code: string;
  name: string;
  description: string;
  typical_impact: string;
  suggested_question: string;
  status: 'missing_from_quote' | 'explicitly_covered' | 'ambiguous';
}

interface BenchmarkComparison {
  category: string;
  city_tier: string;
  sample_size: number;
  median_unit_cost?: number;
  quote_unit_cost?: number;
  cost_status: string;
  percentage_diff_vs_median?: number;
  is_limited_data: boolean;
  reasoning: Record<string, any>;
}

interface QuoteDocument {
  id: string;
  event_id: string;
  vendor_id?: string;
  vendor_name: string;
  category: string;
  file_name: string;
  file_type: string;
  extraction_status: string;
  total_quoted_amount?: number;
  tax_amount?: number;
  line_items: LineItem[];
  hidden_cost_alerts: HiddenCostAlert[];
  benchmark_comparison?: BenchmarkComparison;
  uploaded_at: string;
}

interface ComparedQuote {
  quote_id: string;
  vendor_name: string;
  raw_total: number;
  effective_total_with_hidden_buffer: number;
  normalized_cost_per_guest: number;
  line_items: LineItem[];
  hidden_cost_risk_count: number;
  hidden_cost_risks: string[];
}

interface ComparisonResult {
  event_id: string;
  category: string;
  guest_count: number;
  compared_quotes: ComparedQuote[];
  benchmark_median_unit_cost?: number;
  benchmark_sample_size: number;
  benchmark_is_limited_data: boolean;
  best_value_quote_id?: string;
  reasoning: Record<string, any>;
}

interface NegotiationDrafts {
  polite: { english: string; hindi: string };
  firm: { english: string; hindi: string };
  bundle_ask: { english: string; hindi: string };
}

interface EventMetadata {
  name: string;
  city: string;
  guest_count: number;
  total_budget: number;
}

export default function ScopedQuotesDashboardClient() {
  const params = useParams();
  const eventId = (params?.id as string) || '';

  const [eventMeta, setEventMeta] = useState<EventMetadata | null>(null);
  const [quotes, setQuotes] = useState<QuoteDocument[]>([]);
  const [selectedQuoteIds, setSelectedQuoteIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadCategory, setUploadCategory] = useState<string>('caterer');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Active / Detailed view
  const [activeQuote, setActiveQuote] = useState<QuoteDocument | null>(null);

  // Side-by-side comparison
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);

  // Negotiation Drawer State
  const [isDraftDrawerOpen, setIsDraftDrawerOpen] = useState<boolean>(false);
  const [draftTargetQuote, setDraftTargetQuote] = useState<QuoteDocument | null>(null);
  const [draftVariants, setDraftVariants] = useState<NegotiationDrafts | null>(null);
  const [activeVariantTab, setActiveVariantTab] = useState<'polite' | 'firm' | 'bundle_ask'>('polite');
  const [draftLanguage, setDraftLanguage] = useState<'english' | 'hindi'>('english');
  const [copySuccessMsg, setCopySuccessMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const getApiBase = () => {
    return typeof window !== 'undefined' && window.location.hostname.includes('netlify.app')
      ? '/api/v1'
      : 'https://utsav-ai-ycg2.onrender.com/api/v1';
  };

  const loadQuotes = useCallback(async (targetEventId: string) => {
    setIsLoading(true);
    try {
      const apiBase = getApiBase();
      const res = await fetch(`${apiBase}/quotes/event/${targetEventId}`, {
        headers: getAuthHeaders(targetEventId)
      });
      if (res.ok) {
        const data = await res.json();
        setQuotes(data);
        if (data.length > 0 && !activeQuote) {
          setActiveQuote(data[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load scoped quotes:', err);
    } finally {
      setIsLoading(false);
    }
  }, [activeQuote]);

  // 1. Fetch Event Metadata & Scoped Quotes
  useEffect(() => {
    if (!eventId || eventId === 'default') {
      setIsLoading(false);
      return;
    }

    const apiBase = getApiBase();

    // Fetch Event Metadata
    fetch(`${apiBase}/events/${eventId}`, {
      headers: getAuthHeaders(eventId)
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setEventMeta({
            name: data.name,
            city: data.city,
            guest_count: data.guest_count,
            total_budget: Number(data.total_budget)
          });
        }
      })
      .catch((err) => console.warn('Could not fetch event details:', err));

    // Fetch Quotes for this Event
    loadQuotes(eventId);
  }, [eventId, loadQuotes]);

  // Upload quote file for THIS event
  async function handleFileUpload(files: FileList | null) {
    if (!files || files.length === 0 || !eventId || eventId === 'default') {
      setErrorMsg('Cannot upload quote without a valid celebration event ID.');
      return;
    }
    const file = files[0];

    const form = new FormData();
    form.append('file', file);
    form.append('event_id', eventId);
    form.append('category', uploadCategory);
    const ownerToken = getEventOwnerToken(eventId);
    if (ownerToken) form.append('owner_token', ownerToken);

    setIsUploading(true);
    setErrorMsg(null);

    try {
      const apiBase = getApiBase();
      const res = await fetch(`${apiBase}/quotes/upload`, {
        method: 'POST',
        headers: getAuthHeaders(eventId),
        body: form
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Upload failed with status ${res.status}`);
      }
      const newQuote: QuoteDocument = await res.json();
      setQuotes((prev) => [newQuote, ...prev]);
      setActiveQuote(newQuote);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to upload quote document.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  function toggleQuoteSelection(id: string) {
    setSelectedQuoteIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }

  // Launch Side-by-Side Comparison using the event's real guest count
  async function handleCompareQuotes() {
    if (selectedQuoteIds.length < 2) return;
    setIsComparing(true);
    try {
      const apiBase = getApiBase();
      const res = await fetch(`${apiBase}/quotes/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quote_ids: selectedQuoteIds,
          target_guest_count: eventMeta?.guest_count || 250
        })
      });
      if (res.ok) {
        const data: ComparisonResult = await res.json();
        setComparisonResult(data);
      }
    } catch (err) {
      console.error('Failed to compare quotes', err);
    } finally {
      setIsComparing(false);
    }
  }

  // Open Negotiation Draft Drawer
  async function openNegotiationDrawer(quote: QuoteDocument) {
    setDraftTargetQuote(quote);
    setIsDraftDrawerOpen(true);
    setDraftVariants(null);
    setCopySuccessMsg(null);

    try {
      const apiBase = getApiBase();
      const competitorId = quotes.find((q) => q.id !== quote.id && q.category === quote.category)?.id;
      const res = await fetch(`${apiBase}/quotes/${quote.id}/negotiate-draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quote_id: quote.id,
          target_discount_percentage: 10.0,
          competing_quote_id: competitorId
        })
      });
      if (res.ok) {
        const data = await res.json();
        setDraftVariants(data.draft_variants);
      }
    } catch (err) {
      console.error('Failed to load negotiation drafts', err);
    }
  }

  function handleCopyText(text: string) {
    navigator.clipboard.writeText(text);
    setCopySuccessMsg('Draft copied to clipboard!');
    setTimeout(() => setCopySuccessMsg(null), 3000);
  }

  const formatCurrency = (amount?: number) => {
    if (amount === undefined || amount === null) return '—';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  return (
    <div className="min-h-screen pb-20">
      {/* Top Navigation with Scoped Return */}
      <Navbar
        badge="Vendor Hub"
        rightAction={
          <Link
            href={`/dashboard/events/${eventId}`}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-800 hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 transition-colors"
          >
            ← Back to Event
          </Link>
        }
      />

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 space-y-6">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400 font-medium">
          <Link href="/" className="hover:text-stone-900 dark:hover:text-white transition-colors">
            Home
          </Link>
          <span>/</span>
          <Link href={`/dashboard/events/${eventId}`} className="hover:text-stone-900 dark:hover:text-white transition-colors">
            {eventMeta?.name || 'Celebration'}
          </Link>
          <span>/</span>
          <span className="text-stone-700 dark:text-stone-300">Vendor Quotes</span>
        </div>

        {/* Event Scope Header */}
        <div className="glass-card rounded-3xl p-6 border border-stone-200 dark:border-stone-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#8B1E28] dark:text-[#F4B41A]">
              Scoped Vendor Management
            </span>
            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900 dark:text-stone-50 mt-0.5">
              {eventMeta?.name || 'Celebration Quotes'}
            </h1>
            <p className="text-xs text-stone-500 dark:text-stone-400 mt-1">
              Event ID: <span className="font-mono">{eventId}</span> • City: {eventMeta?.city || 'Calibrated'} • Guests: {eventMeta?.guest_count || 250}
            </p>
          </div>

          <Link
            href={`/dashboard/events/${eventId}`}
            className="self-start sm:self-auto px-4 py-2 rounded-xl bg-stone-100 dark:bg-stone-800 text-stone-800 dark:text-stone-200 text-xs font-semibold hover:bg-stone-200 dark:hover:bg-stone-700 transition-all shadow-xs"
          >
            Open Live Command Cockpit →
          </Link>
        </div>

        {/* Banner: Zero Autonomous Send */}
        <div className="p-4 rounded-2xl border border-amber-300/80 dark:border-amber-800/80 bg-amber-50/80 dark:bg-amber-950/40 flex items-start space-x-3 shadow-sm">
          <span className="text-xl">🛡️</span>
          <div>
            <h4 className="text-sm font-semibold text-amber-950 dark:text-amber-200">
              Deterministic Negotiation & Document Privacy
            </h4>
            <p className="text-xs text-amber-900/90 dark:text-amber-300/90 mt-0.5 leading-relaxed">
              Utsav never contacts vendors on your behalf. All extracted prices are grounded strictly in your uploaded contracts. Draft letters are provided for you to review, personalize, and send directly.
            </p>
          </div>
        </div>

        {errorMsg && (
          <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex justify-between items-center shadow-sm">
            <span>⚠️ {errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="font-bold ml-2 hover:opacity-75">✕</button>
          </div>
        )}

        {/* Upload Dropzone & Comparison Header */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Upload Dropzone */}
          <div className="lg:col-span-2 glass-card rounded-3xl p-6 sm:p-7 shadow-sm">
            <h2 className="text-lg font-serif font-bold text-stone-900 dark:text-stone-50 mb-1">
              Upload Vendor Quotation
            </h2>
            <p className="text-xs text-stone-600 dark:text-stone-400 mb-4">
              Upload PDF invoice or quotation image for {eventMeta?.name || 'this event'}. Line items, taxes, and hidden clauses are extracted deterministically.
            </p>

            <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-5">
              <label className="text-xs font-semibold text-stone-700 dark:text-stone-300">Category:</label>
              {(['caterer', 'venue', 'decorator', 'photographer'] as const).map((cat) => (
                <button
                  key={cat}
                  onClick={() => setUploadCategory(cat)}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-semibold capitalize transition-all active:scale-95 ${
                    uploadCategory === cat
                      ? 'bg-[#8B1E28] text-white dark:bg-[#F4B41A] dark:text-stone-950 shadow-sm'
                      : 'bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 hover:bg-stone-200 dark:hover:bg-stone-700 border border-stone-200 dark:border-stone-700'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                handleFileUpload(e.dataTransfer.files);
              }}
              className="border-2 border-dashed border-stone-300 dark:border-stone-700 hover:border-amber-500 dark:hover:border-amber-400 rounded-2xl p-8 text-center cursor-pointer transition-colors bg-stone-50/60 dark:bg-stone-950/40"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,image/*"
                className="hidden"
                onChange={(e) => handleFileUpload(e.target.files)}
              />
              <div className="text-4xl mb-2">📄</div>
              <p className="text-sm font-semibold text-stone-800 dark:text-stone-200">
                {isUploading ? 'Extracting & Auditing Quote with Gemini...' : 'Drag & drop quote PDF/image or click to browse'}
              </p>
              <p className="text-xs text-stone-500 dark:text-stone-400 mt-1">Supports PDF, PNG, JPG up to 10MB</p>
            </div>
          </div>

          {/* Comparison Trigger Card */}
          <div className="glass-card rounded-3xl p-6 sm:p-7 shadow-sm flex flex-col justify-between">
            <div>
              <h3 className="text-base font-serif font-bold text-stone-900 dark:text-stone-50 mb-1">
                Side-by-Side Comparison
              </h3>
              <p className="text-xs text-stone-600 dark:text-stone-400 mb-4">
                Select 2 or more quotes in the same category to calculate effective costs and hidden liability buffers.
              </p>
              <div className="p-4 rounded-2xl bg-stone-100 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800 space-y-2 mb-4">
                <div className="text-xs font-semibold text-stone-700 dark:text-stone-300">
                  Selected for Matrix:
                </div>
                <div className="text-2xl font-bold font-serif text-[#8B1E28] dark:text-[#F4B41A]">
                  {selectedQuoteIds.length} <span className="text-xs font-normal text-stone-500">quotes</span>
                </div>
              </div>
            </div>

            <button
              onClick={handleCompareQuotes}
              disabled={selectedQuoteIds.length < 2 || isComparing}
              className={`w-full py-3 rounded-xl text-xs font-bold uppercase tracking-wider transition-all shadow-sm active:scale-95 ${
                selectedQuoteIds.length >= 2 && !isComparing
                  ? 'bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950'
                  : 'bg-stone-200 dark:bg-stone-800 text-stone-400 cursor-not-allowed'
              }`}
            >
              {isComparing ? 'Computing Differential...' : 'Run Side-by-Side Comparison'}
            </button>
          </div>
        </div>

        {/* Comparison Result Section */}
        {comparisonResult && (
          <div className="glass-card rounded-3xl p-6 sm:p-8 shadow-sm border-2 border-amber-400/80 dark:border-amber-500/80 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-stone-200 dark:border-stone-800">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 font-mono">
                  Comparative Normalization Matrix
                </span>
                <h3 className="text-xl font-serif font-bold text-stone-900 dark:text-stone-50 capitalize">
                  {comparisonResult.category} Comparison ({comparisonResult.guest_count} Guests)
                </h3>
              </div>
              <button
                onClick={() => setComparisonResult(null)}
                className="text-xs text-stone-500 hover:text-stone-800 dark:hover:text-stone-200 underline"
              >
                Close Comparison
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {comparisonResult.compared_quotes.map((q) => {
                const isBest = q.quote_id === comparisonResult.best_value_quote_id;
                return (
                  <div
                    key={q.quote_id}
                    className={`rounded-2xl p-5 border relative flex flex-col justify-between ${
                      isBest
                        ? 'border-emerald-500 dark:border-emerald-400 bg-emerald-50/40 dark:bg-emerald-950/20 shadow-md'
                        : 'border-stone-200 dark:border-stone-800 bg-white/40 dark:bg-stone-900/40'
                    }`}
                  >
                    {isBest && (
                      <span className="absolute -top-3 right-4 px-2.5 py-0.5 rounded-full bg-emerald-600 text-white text-[10px] font-bold font-mono shadow-sm">
                        ⭐ Best Value
                      </span>
                    )}

                    <div className="space-y-3">
                      <div>
                        <h4 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                          {q.vendor_name}
                        </h4>
                        <div className="text-xs text-stone-500">Raw: {formatCurrency(q.raw_total)}</div>
                      </div>

                      <div className="p-3 rounded-xl bg-stone-100 dark:bg-stone-800/60 font-mono space-y-1 text-xs">
                        <div className="text-[10px] uppercase text-stone-500">Effective Total (+Hidden Risks)</div>
                        <div className="text-base font-bold text-stone-900 dark:text-stone-100">
                          {formatCurrency(q.effective_total_with_hidden_buffer)}
                        </div>
                        <div className="text-[11px] text-amber-700 dark:text-amber-400">
                          {formatCurrency(q.normalized_cost_per_guest)} / guest
                        </div>
                      </div>

                      {q.hidden_cost_risks.length > 0 && (
                        <div className="space-y-1">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400">
                            Missing Clauses ({q.hidden_cost_risks.length})
                          </div>
                          <ul className="text-[11px] text-stone-600 dark:text-stone-400 list-disc list-inside space-y-0.5">
                            {q.hidden_cost_risks.slice(0, 3).map((r, i) => (
                              <li key={i}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Quotes List and Detail View */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Quotes List */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-stone-600 dark:text-stone-400">
              Quotes for This Celebration ({quotes.length})
            </h3>

            {quotes.length === 0 ? (
              <div className="p-8 rounded-3xl glass-card text-center text-xs text-stone-500 border border-stone-200 dark:border-stone-800">
                No quotes uploaded yet for this event. Drag and drop a vendor quote above to begin auditing.
              </div>
            ) : (
              quotes.map((q) => {
                const isSelected = selectedQuoteIds.includes(q.id);
                const isActive = activeQuote?.id === q.id;
                return (
                  <div
                    key={q.id}
                    onClick={() => setActiveQuote(q)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer relative shadow-xs ${
                      isActive
                        ? 'border-amber-500 dark:border-amber-400 bg-amber-50/50 dark:bg-amber-950/20'
                        : 'border-stone-200 dark:border-stone-800 bg-white/60 dark:bg-stone-900/60 hover:bg-stone-50 dark:hover:bg-stone-800/40'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300">
                          {q.category}
                        </span>
                        <h4 className="font-semibold text-sm text-stone-900 dark:text-stone-100 mt-1">
                          {q.vendor_name}
                        </h4>
                        <div className="text-xs text-stone-500 mt-0.5">{q.file_name}</div>
                      </div>

                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                          e.stopPropagation();
                          toggleQuoteSelection(q.id);
                        }}
                        className="w-4 h-4 rounded text-amber-600 focus:ring-amber-500 mt-1 cursor-pointer"
                      />
                    </div>

                    <div className="mt-3 pt-2 border-t border-stone-200/60 dark:border-stone-800/60 flex items-center justify-between text-xs">
                      <span className="font-mono font-bold text-stone-900 dark:text-stone-100">
                        {formatCurrency(q.total_quoted_amount)}
                      </span>
                      {q.hidden_cost_alerts.filter((a) => a.status === 'missing_from_quote').length > 0 && (
                        <span className="text-rose-600 dark:text-rose-400 font-semibold text-[11px]">
                          ⚠️ {q.hidden_cost_alerts.filter((a) => a.status === 'missing_from_quote').length} hidden risks
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Active Quote Detail Pane */}
          <div className="lg:col-span-2 space-y-6">
            {activeQuote ? (
              <div className="glass-card rounded-3xl p-6 sm:p-8 border border-stone-200 dark:border-stone-800 shadow-sm space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-stone-200 dark:border-stone-800">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                      {activeQuote.category} Quotation Audit
                    </span>
                    <h3 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-50 mt-1">
                      {activeQuote.vendor_name}
                    </h3>
                    <div className="text-xs text-stone-500 font-mono mt-0.5">
                      File: {activeQuote.file_name} • Uploaded: {new Date(activeQuote.uploaded_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openNegotiationDrawer(activeQuote)}
                      className="px-4 py-2 rounded-xl bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900 text-xs font-semibold hover:opacity-90 shadow-sm transition-opacity"
                    >
                      Draft Negotiation ✍️
                    </button>
                  </div>
                </div>

                {/* Extracted Line Items Table */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                    Extracted Contract Line Items
                  </h4>
                  <div className="overflow-x-auto rounded-xl border border-stone-200 dark:border-stone-800">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-stone-100 dark:bg-stone-800/80 text-stone-700 dark:text-stone-300 font-mono uppercase text-[10px]">
                        <tr>
                          <th className="p-3">Deliverable Item</th>
                          <th className="p-3">Qty / Unit</th>
                          <th className="p-3 text-right">Unit Rate</th>
                          <th className="p-3 text-right">Subtotal</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                        {activeQuote.line_items.map((item, idx) => (
                          <tr key={idx} className="hover:bg-stone-50/50 dark:hover:bg-stone-800/30">
                            <td className="p-3 font-medium text-stone-900 dark:text-stone-100">
                              {item.name}
                              {item.category_tag && (
                                <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-mono bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400">
                                  {item.category_tag}
                                </span>
                              )}
                            </td>
                            <td className="p-3 text-stone-600 dark:text-stone-400 font-mono">
                              {item.qty} {item.unit}
                            </td>
                            <td className="p-3 text-right text-stone-700 dark:text-stone-300 font-mono">
                              {formatCurrency(item.unit_price)}
                            </td>
                            <td className="p-3 text-right font-mono font-semibold text-stone-900 dark:text-stone-100">
                              {formatCurrency(item.total)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-stone-50 dark:bg-stone-900/60 font-semibold font-mono border-t border-stone-200 dark:border-stone-800">
                        <tr>
                          <td colSpan={3} className="p-3 text-right">Total Quoted Amount:</td>
                          <td className="p-3 text-right text-base text-[#8B1E28] dark:text-[#F4B41A]">
                            {formatCurrency(activeQuote.total_quoted_amount)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>

                {/* 18 Hidden Cost Audit Red Flags */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-700 dark:text-rose-400">
                    Hidden Cost Red Flags & Contract Gaps (DEC-013 Check)
                  </h4>
                  <div className="grid sm:grid-cols-2 gap-3">
                    {activeQuote.hidden_cost_alerts.map((alert, idx) => (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
                          alert.status === 'missing_from_quote'
                            ? 'bg-rose-50/70 dark:bg-rose-950/30 border-rose-300 dark:border-rose-900 text-rose-950 dark:text-rose-200'
                            : alert.status === 'ambiguous'
                            ? 'bg-amber-50/70 dark:bg-amber-950/30 border-amber-300 dark:border-amber-900 text-amber-950 dark:text-amber-200'
                            : 'bg-emerald-50/70 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-900 text-emerald-950 dark:text-emerald-200'
                        }`}
                      >
                        <div className="flex items-center justify-between font-bold">
                          <span>{alert.name}</span>
                          <span className="font-mono text-[10px] uppercase">{alert.status.replace('_', ' ')}</span>
                        </div>
                        <p className="text-[11px] opacity-90 leading-relaxed">{alert.description}</p>
                        <div className="font-mono text-[10px] text-stone-500">Typical Impact: {alert.typical_impact}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-12 rounded-3xl glass-card text-center text-xs text-stone-500 border border-stone-200 dark:border-stone-800">
                Select a quote from the left to view extracted deliverables and hidden clause red flags.
              </div>
            )}
          </div>
        </div>

        {/* Negotiation Drafts Drawer Modal */}
        {isDraftDrawerOpen && draftTargetQuote && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn">
            <div className="glass-card max-w-2xl w-full p-6 sm:p-8 rounded-3xl shadow-2xl border border-stone-200 dark:border-stone-800 space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-stone-200/60 dark:border-stone-800/60">
                <div>
                  <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                    Draft Negotiation Template
                  </h3>
                  <p className="text-xs text-stone-500 mt-0.5">
                    Target Vendor: {draftTargetQuote.vendor_name} ({draftTargetQuote.category})
                  </p>
                </div>
                <button
                  onClick={() => setIsDraftDrawerOpen(false)}
                  className="w-8 h-8 rounded-full bg-stone-100 dark:bg-stone-800 text-stone-500 hover:text-stone-900 dark:hover:text-white flex items-center justify-center text-sm font-bold"
                >
                  ✕
                </button>
              </div>

              {/* Tone Variant Tabs */}
              <div className="flex border-b border-stone-200 dark:border-stone-800 gap-1 text-xs font-semibold">
                {(['polite', 'firm', 'bundle_ask'] as const).map((variant) => (
                  <button
                    key={variant}
                    onClick={() => setActiveVariantTab(variant)}
                    className={`px-4 py-2 border-b-2 capitalize transition-all ${
                      activeVariantTab === variant
                        ? 'border-[#8B1E28] dark:border-[#F4B41A] text-[#8B1E28] dark:text-[#F4B41A]'
                        : 'border-transparent text-stone-500 hover:text-stone-800'
                    }`}
                  >
                    {variant.replace('_', ' ')}
                  </button>
                ))}
                <div className="ml-auto flex items-center gap-1.5 text-xs">
                  <button
                    onClick={() => setDraftLanguage('english')}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-medium ${
                      draftLanguage === 'english' ? 'bg-stone-800 text-white dark:bg-stone-200 dark:text-stone-900' : 'text-stone-500'
                    }`}
                  >
                    English
                  </button>
                  <button
                    onClick={() => setDraftLanguage('hindi')}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-medium ${
                      draftLanguage === 'hindi' ? 'bg-stone-800 text-white dark:bg-stone-200 dark:text-stone-900' : 'text-stone-500'
                    }`}
                  >
                    Hindi
                  </button>
                </div>
              </div>

              {/* Text Area */}
              <div className="relative">
                <textarea
                  readOnly
                  rows={8}
                  className="w-full p-4 rounded-2xl bg-stone-50 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-xs text-stone-800 dark:text-stone-200 font-mono leading-relaxed focus:outline-none"
                  value={
                    draftVariants
                      ? draftVariants[activeVariantTab][draftLanguage]
                      : 'Synthesizing contextual negotiation brief from verified contract benchmarks...'
                  }
                />
                {copySuccessMsg && (
                  <div className="absolute top-2 right-2 px-3 py-1 bg-emerald-600 text-white rounded-lg text-xs font-semibold animate-fadeIn">
                    {copySuccessMsg}
                  </div>
                )}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    if (draftVariants) {
                      handleCopyText(draftVariants[activeVariantTab][draftLanguage]);
                    }
                  }}
                  disabled={!draftVariants}
                  className="flex-1 py-2.5 rounded-xl bg-[#8B1E28] hover:bg-[#721820] text-white dark:bg-[#F4B41A] dark:text-stone-950 font-semibold text-xs transition-opacity shadow-sm"
                >
                  📋 Copy to Clipboard
                </button>
                <button
                  onClick={() => setIsDraftDrawerOpen(false)}
                  className="px-5 py-2.5 rounded-xl border border-stone-300 dark:border-stone-700 text-xs font-semibold hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
