'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Navbar } from '@/components/ui/Navbar';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.hostname.includes('netlify.app')
    ? '/api/v1'
    : 'https://utsav-ai-ycg2.onrender.com/api/v1');

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

export default function QuotesDashboardPage() {
  const [eventId, setEventId] = useState<string>('');
  const [quotes, setQuotes] = useState<QuoteDocument[]>([]);
  const [selectedQuoteIds, setSelectedQuoteIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
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

  // 1. Fetch initial event or seed
  useEffect(() => {
    async function initEvent() {
      try {
        const res = await fetch(`${API_BASE_URL}/events`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: "Default Workspace Event",
            event_type: "wedding",
            city: "Jaipur",
            guest_count: 250,
            total_budget: 3500000.0,
            host_name: "Default Host",
            host_phone: "+919876543210"
          })
        });
        if (res.ok) {
          const data = await res.json();
          setEventId(data.id);
          loadQuotes(data.id);
        }
      } catch (err) {
        console.error("Failed to init event for quotes:", err);
      }
    }
    initEvent();
  }, []);

  async function loadQuotes(targetEventId: string) {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/quotes/event/${targetEventId}`);
      if (res.ok) {
        const data = await res.json();
        setQuotes(data);
        if (data.length > 0 && !activeQuote) {
          setActiveQuote(data[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load quotes:", err);
    } finally {
      setIsLoading(false);
    }
  }

  // Upload quote file
  async function handleFileUpload(files: FileList | null) {
    if (!files || files.length === 0 || !eventId) return;
    const file = files[0];

    const form = new FormData();
    form.append('file', file);
    form.append('event_id', eventId);
    form.append('category', uploadCategory);

    setIsUploading(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`${API_BASE_URL}/quotes/upload`, {
        method: 'POST',
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

  // Launch Side-by-Side Comparison
  async function handleCompareQuotes() {
    if (selectedQuoteIds.length < 2) return;
    setIsComparing(true);
    try {
      const res = await fetch(`${API_BASE_URL}/quotes/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quote_ids: selectedQuoteIds,
          target_guest_count: 250
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
      const competitorId = quotes.find((q) => q.id !== quote.id && q.category === quote.category)?.id;
      const res = await fetch(`${API_BASE_URL}/quotes/${quote.id}/negotiate-draft`, {
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

  return (
    <div className="min-h-screen pb-20">
      {/* Top Navigation */}
      <Navbar
        badge="Quote Auditor"
        rightAction={
          <Link
            href="/onboarding"
            className="text-xs font-semibold uppercase tracking-wider text-stone-600 dark:text-stone-300 hover:text-stone-900 dark:hover:text-white px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-800 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
          >
            ← Intake Studio
          </Link>
        }
      />

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-8">
        {/* Banner: Zero Autonomous Send */}
        <div className="mb-6 p-4 rounded-2xl border border-amber-300/80 dark:border-amber-800/80 bg-amber-50/80 dark:bg-amber-950/40 flex items-start space-x-3 shadow-sm">
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
          <div className="mb-6 p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex justify-between items-center shadow-sm">
            <span>⚠️ {errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="font-bold ml-2 hover:opacity-75">✕</button>
          </div>
        )}

        {/* Top Actions: Upload Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Upload Dropzone */}
          <div className="lg:col-span-2 glass-card rounded-3xl p-6 sm:p-7 shadow-sm">
            <h2 className="text-lg font-serif font-bold text-stone-900 dark:text-stone-50 mb-1">
              Upload Vendor Quotation
            </h2>
            <p className="text-xs text-stone-600 dark:text-stone-400 mb-4">
              Upload PDF invoice or quotation image. Line items, taxes, and hidden clauses will be extracted deterministically.
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

          {/* Side Overview / Comparison Trigger */}
          <div className="glass-card rounded-3xl p-6 sm:p-7 shadow-sm flex flex-col justify-between">
            <div>
              <h3 className="text-base font-serif font-bold text-stone-900 dark:text-stone-50 mb-2">
                Compare Quotes Side-by-Side
              </h3>
              <p className="text-xs text-stone-600 dark:text-stone-400 mb-4 leading-relaxed">
                Select 2 or more quotes of the same category to normalize costs against your guest count and benchmark medians.
              </p>
              <div className="space-y-1 mb-4 p-3 rounded-xl bg-stone-100/70 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800">
                <span className="text-xs text-stone-600 dark:text-stone-400 font-medium">Selected for comparison: </span>
                <span className="text-xs font-bold text-[#8B1E28] dark:text-[#F4B41A] block mt-0.5">
                  {selectedQuoteIds.length} quote(s)
                </span>
              </div>
            </div>

            <button
              onClick={handleCompareQuotes}
              disabled={selectedQuoteIds.length < 2 || isComparing}
              className={`w-full py-3 rounded-xl font-bold text-xs tracking-wider uppercase transition-all shadow-sm active:scale-95 ${
                selectedQuoteIds.length >= 2
                  ? 'bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950'
                  : 'bg-stone-200 dark:bg-stone-800 text-stone-400 dark:text-stone-600 cursor-not-allowed'
              }`}
            >
              {isComparing ? 'Analyzing Differences...' : 'Launch Side-by-Side Comparison'}
            </button>
          </div>
        </div>

        {/* Comparison Result Card */}
        {comparisonResult && (
          <div className="mb-8 glass-card rounded-3xl p-6 sm:p-8 border-2 border-amber-400/80 dark:border-amber-500/80 shadow-lg">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-6 pb-4 border-b border-stone-200 dark:border-stone-800">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                  Comparison Output
                </span>
                <h3 className="text-xl font-serif font-bold text-stone-900 dark:text-stone-50 capitalize mt-0.5">
                  {comparisonResult.category} Quotes Normalized to {comparisonResult.guest_count} Guests
                </h3>
              </div>
              <button
                onClick={() => setComparisonResult(null)}
                className="text-xs font-semibold px-3.5 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 dark:bg-stone-800 dark:hover:bg-stone-700 text-stone-700 dark:text-stone-300 border border-stone-200 dark:border-stone-700 transition-colors"
              >
                Close Comparison
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {comparisonResult.compared_quotes.map((cq) => (
                <div key={cq.quote_id} className="p-5 rounded-2xl border border-stone-200 dark:border-stone-800 bg-stone-50/80 dark:bg-stone-950/50 flex flex-col justify-between shadow-sm">
                  <div>
                    <h4 className="font-serif font-bold text-base text-stone-900 dark:text-stone-50">{cq.vendor_name}</h4>
                    <div className="mt-3 space-y-1.5 text-xs">
                      <div className="flex justify-between">
                        <span className="text-stone-500 dark:text-stone-400">Quoted Total:</span>
                        <span className="font-medium text-stone-900 dark:text-stone-100">₹{cq.raw_total.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-stone-500 dark:text-stone-400">Effective (w/ Risk Buffer):</span>
                        <span className="font-bold text-[#8B1E28] dark:text-[#F4B41A]">₹{cq.effective_total_with_hidden_buffer.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-stone-500 dark:text-stone-400">Effective Cost / Guest:</span>
                        <span className="font-semibold text-stone-900 dark:text-stone-100">₹{cq.normalized_cost_per_guest.toLocaleString('en-IN')}</span>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-stone-200 dark:border-stone-800">
                      <span className="text-xs font-semibold text-stone-700 dark:text-stone-300">Missing Provisions ({cq.hidden_cost_risk_count}):</span>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {cq.hidden_cost_risks.slice(0, 3).map((risk, idx) => (
                          <span key={idx} className="text-[10px] px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950/70 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 font-medium">
                            {risk}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      const match = quotes.find((q) => q.id === cq.quote_id);
                      if (match) openNegotiationDrawer(match);
                    }}
                    className="mt-5 w-full py-2.5 rounded-xl bg-stone-900 hover:bg-[#8B1E28] text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 text-xs font-bold transition-all shadow-sm active:scale-95"
                  >
                    Draft Negotiation Letter
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quotes List & Detail Split View */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Quotes Sidebar List */}
          <div className="space-y-3">
            <h3 className="text-sm font-serif font-bold text-stone-900 dark:text-stone-50 flex justify-between items-center px-1">
              <span>Saved Quotations</span>
              <span className="text-xs text-stone-500 dark:text-stone-400 font-mono font-normal">{quotes.length} total</span>
            </h3>

            {quotes.length === 0 ? (
              <div className="glass-card p-6 rounded-2xl text-center text-xs text-stone-500 dark:text-stone-400">
                No quotations uploaded yet. Use the upload box above.
              </div>
            ) : (
              quotes.map((q) => (
                <div
                  key={q.id}
                  onClick={() => setActiveQuote(q)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                    activeQuote?.id === q.id
                      ? 'bg-amber-50/90 dark:bg-amber-950/40 border-amber-500 dark:border-amber-400 shadow-md ring-1 ring-amber-400/30'
                      : 'glass-card hover:border-amber-400/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 border border-stone-200 dark:border-stone-700">
                        {q.category}
                      </span>
                      <h4 className="font-serif font-bold text-stone-900 dark:text-stone-100 text-sm mt-1">{q.vendor_name}</h4>
                    </div>
                    <input
                      type="checkbox"
                      checked={selectedQuoteIds.includes(q.id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleQuoteSelection(q.id);
                      }}
                      className="w-4 h-4 text-amber-600 rounded border-stone-300 dark:border-stone-700 focus:ring-amber-400"
                    />
                  </div>

                  <div className="mt-3 flex justify-between items-baseline text-xs">
                    <span className="text-stone-500 dark:text-stone-400">Quoted Total</span>
                    <span className="font-bold text-stone-900 dark:text-stone-100 font-mono">
                      ₹{(q.total_quoted_amount || 0).toLocaleString('en-IN')}
                    </span>
                  </div>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-stone-500 dark:text-stone-400">
                    <span>{q.line_items.length} line items</span>
                    <span className="text-rose-600 dark:text-rose-400 font-semibold">
                      {q.hidden_cost_alerts.filter((a) => a.status === 'missing_from_quote').length} flags
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Active Quote Detail Pane */}
          <div className="lg:col-span-2 space-y-6">
            {activeQuote ? (
              <>
                {/* Header Card */}
                <div className="glass-card rounded-3xl p-6 sm:p-7 shadow-sm">
                  <div className="flex flex-wrap justify-between items-start gap-4">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950/80 border border-amber-300 dark:border-amber-800 text-amber-800 dark:text-amber-300">
                          {activeQuote.category}
                        </span>
                        <span className="text-xs text-stone-500 dark:text-stone-400 font-mono">Status: {activeQuote.extraction_status}</span>
                      </div>
                      <h2 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-50 mt-1">{activeQuote.vendor_name}</h2>
                      <p className="text-xs text-stone-500 dark:text-stone-400 mt-0.5">Source: {activeQuote.file_name}</p>
                    </div>

                    <div className="text-right">
                      <div className="text-2xl font-bold font-mono text-[#8B1E28] dark:text-[#F4B41A]">
                        ₹{(activeQuote.total_quoted_amount || 0).toLocaleString('en-IN')}
                      </div>
                      {activeQuote.tax_amount ? (
                        <p className="text-xs text-stone-500 dark:text-stone-400">Includes ₹{activeQuote.tax_amount.toLocaleString('en-IN')} GST</p>
                      ) : null}
                      <button
                        onClick={() => openNegotiationDrawer(activeQuote)}
                        className="mt-3 px-5 py-2 rounded-xl bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 text-xs font-semibold transition-all shadow-sm active:scale-95 flex items-center space-x-1.5 ml-auto"
                      >
                        <span>Generate Negotiation Letters</span>
                        <span>→</span>
                      </button>
                    </div>
                  </div>

                  {/* Benchmark pill */}
                  {activeQuote.benchmark_comparison && (
                    <div className="mt-4 pt-4 border-t border-stone-200 dark:border-stone-800 flex items-center justify-between text-xs">
                      <span className="text-stone-600 dark:text-stone-400 font-medium">Regional Median Benchmark:</span>
                      {activeQuote.benchmark_comparison.is_limited_data ? (
                        <span className="px-2.5 py-0.5 rounded-full bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-300 font-medium border border-stone-200 dark:border-stone-700">
                          Limited data (n &lt; 5)
                        </span>
                      ) : (
                        <span
                          className={`px-2.5 py-0.5 rounded-full font-medium border ${
                            activeQuote.benchmark_comparison.cost_status === 'above_median'
                              ? 'bg-rose-100 dark:bg-rose-950/70 border-rose-300 dark:border-rose-900 text-rose-800 dark:text-rose-300'
                              : 'bg-emerald-100 dark:bg-emerald-950/70 border-emerald-300 dark:border-emerald-900 text-emerald-800 dark:text-emerald-300'
                          }`}
                        >
                          {activeQuote.benchmark_comparison.percentage_diff_vs_median}% vs {activeQuote.benchmark_comparison.city_tier} median (₹{activeQuote.benchmark_comparison.median_unit_cost?.toLocaleString('en-IN')})
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Hidden-Cost Alerts Checklist */}
                <div className="glass-card rounded-3xl p-6 sm:p-7 shadow-sm">
                  <h3 className="text-base font-serif font-bold text-stone-900 dark:text-stone-50 mb-4">
                    Deterministic Hidden-Cost Analysis
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    {activeQuote.hidden_cost_alerts.map((alert) => (
                      <div
                        key={alert.code}
                        className={`p-3.5 rounded-2xl border flex flex-col justify-between text-xs shadow-sm ${
                          alert.status === 'missing_from_quote'
                            ? 'bg-rose-50/70 dark:bg-rose-950/40 border-rose-200 dark:border-rose-900/60'
                            : alert.status === 'explicitly_covered'
                            ? 'bg-emerald-50/70 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-900/60'
                            : 'bg-amber-50/70 dark:bg-amber-950/40 border-amber-200 dark:border-amber-900/60'
                        }`}
                      >
                        <div>
                          <div className="flex justify-between items-center mb-1">
                            <span className="font-semibold text-stone-900 dark:text-stone-100">{alert.name}</span>
                            <span
                              className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                                alert.status === 'missing_from_quote'
                                  ? 'bg-rose-200 dark:bg-rose-900 text-rose-900 dark:text-rose-200'
                                  : 'bg-emerald-200 dark:bg-emerald-900 text-emerald-900 dark:text-emerald-200'
                              }`}
                            >
                              {alert.status === 'missing_from_quote' ? 'Missing' : 'Covered'}
                            </span>
                          </div>
                          <p className="text-stone-600 dark:text-stone-300 text-[11px] leading-relaxed mt-1">{alert.description}</p>
                        </div>
                        <div className="mt-2.5 pt-2 border-t border-stone-200/60 dark:border-stone-800/60 text-[11px] text-stone-500 dark:text-stone-400 italic">
                          Ask: "{alert.suggested_question}"
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Line Items Table */}
                <div className="glass-card rounded-3xl p-6 sm:p-7 shadow-sm overflow-hidden">
                  <h3 className="text-base font-serif font-bold text-stone-900 dark:text-stone-50 mb-4">
                    Extracted Line Items
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-stone-200 dark:border-stone-800 text-stone-500 dark:text-stone-400 font-semibold uppercase tracking-wider">
                          <th className="py-2.5 px-2">Item Description</th>
                          <th className="py-2.5 px-2 text-right">Qty</th>
                          <th className="py-2.5 px-2 text-right">Rate</th>
                          <th className="py-2.5 px-2 text-right">Total (₹)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
                        {activeQuote.line_items.map((li, idx) => (
                          <tr key={idx} className="hover:bg-stone-50/60 dark:hover:bg-stone-800/40 transition-colors">
                            <td className="py-3 px-2 font-medium text-stone-900 dark:text-stone-100">
                              <div>{li.name}</div>
                              {li.notes && <div className="text-[11px] text-stone-500 dark:text-stone-400 mt-0.5">{li.notes}</div>}
                            </td>
                            <td className="py-3 px-2 text-right text-stone-600 dark:text-stone-300 font-mono">
                              {li.qty} {li.unit}
                            </td>
                            <td className="py-3 px-2 text-right text-stone-600 dark:text-stone-300 font-mono">
                              ₹{li.unit_price.toLocaleString('en-IN')}
                            </td>
                            <td className="py-3 px-2 text-right font-bold text-stone-900 dark:text-stone-100 font-mono">
                              ₹{li.total.toLocaleString('en-IN')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            ) : (
              <div className="glass-card rounded-3xl p-12 text-center text-stone-500 dark:text-stone-400 text-sm">
                Select a quote on the left or upload a new one to view line items and hidden-cost audit.
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Negotiation Drafts Drawer / Modal */}
      {isDraftDrawerOpen && draftTargetQuote && (
        <div className="fixed inset-0 z-50 bg-stone-900/60 dark:bg-black/80 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-2xl bg-white dark:bg-stone-900 h-full shadow-2xl p-6 sm:p-7 overflow-y-auto flex flex-col justify-between border-l border-stone-200 dark:border-stone-800">
            <div>
              {/* Drawer Header */}
              <div className="flex justify-between items-start pb-4 border-b border-stone-200 dark:border-stone-800">
                <div>
                  <span className="text-xs uppercase font-bold text-[#8B1E28] dark:text-[#F4B41A]">Negotiation Assistant</span>
                  <h3 className="text-xl font-serif font-bold text-stone-900 dark:text-stone-50 mt-0.5">
                    Draft Letters for {draftTargetQuote.vendor_name}
                  </h3>
                </div>
                <button
                  onClick={() => setIsDraftDrawerOpen(false)}
                  className="w-8 h-8 rounded-full bg-stone-100 dark:bg-stone-800 hover:bg-stone-200 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 flex items-center justify-center font-bold text-sm transition-colors"
                >
                  ✕
                </button>
              </div>

              {/* Language & Tone Selectors */}
              <div className="mt-4 flex flex-wrap justify-between items-center gap-3">
                {/* Variant Tabs */}
                <div className="flex space-x-1 p-1 bg-stone-100 dark:bg-stone-800 rounded-xl">
                  {(['polite', 'firm', 'bundle_ask'] as const).map((variant) => (
                    <button
                      key={variant}
                      onClick={() => setActiveVariantTab(variant)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${
                        activeVariantTab === variant
                          ? 'bg-white dark:bg-stone-700 text-stone-900 dark:text-stone-100 shadow-sm'
                          : 'text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-200'
                      }`}
                    >
                      {variant.replace('_', ' ')}
                    </button>
                  ))}
                </div>

                {/* Language Toggle */}
                <div className="flex space-x-1 p-1 bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 rounded-xl text-xs font-medium">
                  <button
                    onClick={() => setDraftLanguage('english')}
                    className={`px-3 py-1 rounded-lg transition-colors ${
                      draftLanguage === 'english'
                        ? 'bg-[#8B1E28] text-white dark:bg-[#F4B41A] dark:text-stone-950'
                        : 'text-stone-700 dark:text-stone-300'
                    }`}
                  >
                    English
                  </button>
                  <button
                    onClick={() => setDraftLanguage('hindi')}
                    className={`px-3 py-1 rounded-lg transition-colors ${
                      draftLanguage === 'hindi'
                        ? 'bg-[#8B1E28] text-white dark:bg-[#F4B41A] dark:text-stone-950'
                        : 'text-stone-700 dark:text-stone-300'
                    }`}
                  >
                    हिंदी (Devanagari)
                  </button>
                </div>
              </div>

              {/* Draft Message Content */}
              <div className="mt-6 bg-stone-50 dark:bg-stone-950/70 rounded-2xl p-5 border border-stone-200 dark:border-stone-800 relative">
                {copySuccessMsg && (
                  <div className="absolute top-2 right-2 px-3 py-1 bg-emerald-600 text-white text-xs font-semibold rounded-lg shadow-md animate-fadeIn">
                    {copySuccessMsg}
                  </div>
                )}

                {draftVariants ? (
                  <div>
                    <pre className="whitespace-pre-wrap font-sans text-xs text-stone-800 dark:text-stone-200 leading-relaxed">
                      {draftVariants[activeVariantTab][draftLanguage]}
                    </pre>

                    <div className="mt-4 pt-4 border-t border-stone-200 dark:border-stone-800 flex justify-end">
                      <button
                        onClick={() => handleCopyText(draftVariants[activeVariantTab][draftLanguage])}
                        className="px-4 py-2 rounded-xl bg-stone-900 hover:bg-[#8B1E28] text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 text-xs font-semibold flex items-center space-x-2 transition-all shadow-sm active:scale-95"
                      >
                        <span>📋</span>
                        <span>Copy Draft to Clipboard</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="py-12 text-center text-xs text-stone-400">Generating negotiation variants...</div>
                )}
              </div>

              {/* Human Control Guarantee */}
              <div className="mt-6 p-4 rounded-xl bg-stone-100 dark:bg-stone-800/60 text-[11px] text-stone-600 dark:text-stone-400 leading-normal border border-stone-200 dark:border-stone-700">
                <strong>Human-in-the-loop guarantee:</strong> Utsav never dispatches communication without human review. You can paste this text directly into WhatsApp or email and modify any terms to suit your family’s tone.
              </div>
            </div>

            <div className="pt-4 border-t border-stone-200 dark:border-stone-800">
              <button
                onClick={() => setIsDraftDrawerOpen(false)}
                className="w-full py-2.5 rounded-xl border border-stone-300 dark:border-stone-700 text-stone-700 dark:text-stone-300 text-xs font-medium hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
