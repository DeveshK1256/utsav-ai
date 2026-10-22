'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://utsav-ai-ycg2.onrender.com/api/v1';

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

  // Negotiation Drawer state
  const [isDraftDrawerOpen, setIsDraftDrawerOpen] = useState<boolean>(false);
  const [draftTargetQuote, setDraftTargetQuote] = useState<QuoteDocument | null>(null);
  const [draftVariants, setDraftVariants] = useState<NegotiationDrafts | null>(null);
  const [draftLanguage, setDraftLanguage] = useState<'english' | 'hindi'>('english');
  const [activeVariantTab, setActiveVariantTab] = useState<'polite' | 'firm' | 'bundle_ask'>('polite');
  const [copySuccessMsg, setCopySuccessMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-load or create test event on mount if not specified
  useEffect(() => {
    async function initOrFetchEvent() {
      setIsLoading(true);
      try {
        const storedId = localStorage.getItem('utsav_last_event_id');
        let currentEventId = storedId;
        if (!currentEventId) {
          // Create default event for dashboard demo
          const res = await fetch(`${API_BASE_URL}/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: 'Ananya & Rohan Wedding',
              event_type: 'wedding',
              guest_count: 350,
              total_budget: 3500000.0,
              city: 'Pune',
              pincode: '411001',
              host_phone: '+919822012345',
              host_name: 'Rohan Joshi'
            })
          });
          if (res.ok) {
            const ev = await res.json();
            currentEventId = ev.id;
            localStorage.setItem('utsav_last_event_id', ev.id);
          }
        }
        if (currentEventId) {
          setEventId(currentEventId);
          await loadQuotes(currentEventId);
        }
      } catch (err: any) {
        console.error('Initialization error', err);
      } finally {
        setIsLoading(false);
      }
    }
    initOrFetchEvent();
  }, []);

  async function loadQuotes(targetEventId: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/quotes/event/${targetEventId}`);
      if (res.ok) {
        const list = await res.json();
        setQuotes(list);
        if (list.length > 0 && !activeQuote) {
          setActiveQuote(list[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load quotes', err);
    }
  }

  // File Upload Handler
  async function handleFileUpload(files: FileList | null) {
    if (!files || files.length === 0 || !eventId) return;
    const file = files[0];
    setIsUploading(true);
    setErrorMsg(null);

    const formData = new FormData();
    formData.append('event_id', eventId);
    formData.append('category', uploadCategory);
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE_URL}/quotes/upload`, {
        method: 'POST',
        body: formData
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }
      const newQuote: QuoteDocument = await res.json();
      setQuotes((prev) => [newQuote, ...prev]);
      setActiveQuote(newQuote);
    } catch (err: any) {
      setErrorMsg(err.message || 'An error occurred during upload.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  // Toggle selection for comparison
  function toggleQuoteSelection(id: string) {
    setSelectedQuoteIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }

  // Run Side-by-Side Comparison
  async function handleCompareQuotes() {
    if (selectedQuoteIds.length < 2) {
      setErrorMsg('Please select at least 2 quotes of the same category to compare.');
      return;
    }
    setIsComparing(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE_URL}/quotes/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quote_ids: selectedQuoteIds })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Comparison failed');
      }
      const data: ComparisonResult = await res.json();
      setComparisonResult(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to compare quotes.');
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
    <div className="min-h-screen bg-[#FDFBF7] text-stone-900 pb-20">
      {/* Top Navigation */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-stone-200">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link href="/" className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#8B1E28] via-[#E67E22] to-[#F4B41A] flex items-center justify-center text-white font-serif text-lg shadow-sm">
              उ
            </Link>
            <div>
              <span className="font-serif font-bold tracking-wide">UTSAV</span>
              <span className="text-xs ml-2 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-medium">F5 Quote Auditor</span>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <Link
              href="/onboarding"
              className="text-xs font-semibold uppercase tracking-wider text-stone-600 hover:text-stone-900"
            >
              ← Intake Studio
            </Link>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-6 pt-8">
        {/* Banner: Zero Autonomous Send */}
        <div className="mb-6 p-4 rounded-xl border border-amber-200 bg-amber-50/80 flex items-start space-x-3">
          <span className="text-xl">🛡️</span>
          <div>
            <h4 className="text-sm font-semibold text-amber-950">Deterministic Negotiation & Document Privacy</h4>
            <p className="text-xs text-amber-900/90 mt-0.5">
              Utsav never contacts vendors on your behalf. All extracted prices are grounded strictly in your uploaded contracts. Draft letters are provided for you to review, personalize, and send directly.
            </p>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-6 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs flex justify-between items-center">
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="font-bold ml-2">✕</button>
          </div>
        )}

        {/* Top Actions: Upload Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Upload Dropzone */}
          <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-stone-200/80 shadow-sm">
            <h2 className="text-lg font-serif font-semibold text-stone-900 mb-1">Upload Vendor Quotation</h2>
            <p className="text-xs text-stone-500 mb-4">Upload PDF invoice or quotation image. Line items, taxes, and hidden clauses will be extracted deterministically.</p>

            <div className="flex flex-wrap items-center gap-4 mb-4">
              <label className="text-xs font-medium text-stone-700">Category:</label>
              {(['caterer', 'venue', 'decorator', 'photographer'] as const).map((cat) => (
                <button
                  key={cat}
                  onClick={() => setUploadCategory(cat)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium capitalize transition-all ${
                    uploadCategory === cat
                      ? 'bg-[#8B1E28] text-white shadow-sm'
                      : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
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
              className="border-2 border-dashed border-stone-300 hover:border-amber-500 rounded-xl p-8 text-center cursor-pointer transition-colors bg-stone-50/50"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,image/*"
                className="hidden"
                onChange={(e) => handleFileUpload(e.target.files)}
              />
              <div className="text-3xl mb-2">📄</div>
              <p className="text-sm font-medium text-stone-700">
                {isUploading ? 'Extracting & Auditing Quote...' : 'Drag & drop quote PDF/image or click to browse'}
              </p>
              <p className="text-xs text-stone-400 mt-1">Supports PDF, PNG, JPG up to 10MB</p>
            </div>
          </div>

          {/* Side Overview / Comparison Trigger */}
          <div className="bg-white rounded-2xl p-6 border border-stone-200/80 shadow-sm flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-semibold text-stone-900 mb-2">Compare Quotes Side-by-Side</h3>
              <p className="text-xs text-stone-500 mb-4">
                Select 2 or more quotes of the same category to normalize costs against your guest count and benchmark medians.
              </p>
              <div className="space-y-1">
                <span className="text-xs text-stone-600 font-medium">Selected for comparison: </span>
                <span className="text-xs font-bold text-[#8B1E28]">{selectedQuoteIds.length} quote(s)</span>
              </div>
            </div>

            <button
              onClick={handleCompareQuotes}
              disabled={selectedQuoteIds.length < 2 || isComparing}
              className={`w-full py-3 rounded-xl font-medium text-xs tracking-wider uppercase transition-all shadow-sm ${
                selectedQuoteIds.length >= 2
                  ? 'bg-[#8B1E28] hover:bg-stone-900 text-white'
                  : 'bg-stone-200 text-stone-400 cursor-not-allowed'
              }`}
            >
              {isComparing ? 'Analyzing Differences...' : 'Launch Side-by-Side Comparison'}
            </button>
          </div>
        </div>

        {/* Comparison Modal / Result Card */}
        {comparisonResult && (
          <div className="mb-8 bg-white rounded-2xl p-6 border-2 border-amber-400/80 shadow-md">
            <div className="flex justify-between items-center mb-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-amber-700">Comparison Output</span>
                <h3 className="text-lg font-serif font-semibold text-stone-900 capitalize">
                  {comparisonResult.category} Quotes Normalized to {comparisonResult.guest_count} Guests
                </h3>
              </div>
              <button
                onClick={() => setComparisonResult(null)}
                className="text-xs font-semibold px-3 py-1 rounded bg-stone-100 hover:bg-stone-200 text-stone-700"
              >
                Close Comparison
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {comparisonResult.compared_quotes.map((cq) => (
                <div key={cq.quote_id} className="p-4 rounded-xl border border-stone-200 bg-stone-50/60 flex flex-col justify-between">
                  <div>
                    <h4 className="font-serif font-bold text-base text-stone-900">{cq.vendor_name}</h4>
                    <div className="mt-2 space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-stone-500">Quoted Total:</span>
                        <span className="font-medium">₹{cq.raw_total.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-stone-500">Effective (w/ Risk Buffer):</span>
                        <span className="font-bold text-[#8B1E28]">₹{cq.effective_total_with_hidden_buffer.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-stone-500">Effective Cost / Guest:</span>
                        <span className="font-semibold text-stone-800">₹{cq.normalized_cost_per_guest.toLocaleString('en-IN')}</span>
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-stone-200">
                      <span className="text-xs font-semibold text-stone-700">Missing Provisions ({cq.hidden_cost_risk_count}):</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {cq.hidden_cost_risks.slice(0, 3).map((risk, idx) => (
                          <span key={idx} className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-800">
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
                    className="mt-4 w-full py-2 rounded-lg bg-stone-900 hover:bg-[#8B1E28] text-white text-xs font-semibold transition-all"
                  >
                    Draft Negotiation
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
            <h3 className="text-sm font-semibold text-stone-900 flex justify-between items-center">
              <span>Saved Quotations</span>
              <span className="text-xs text-stone-500 font-normal">{quotes.length} total</span>
            </h3>

            {quotes.length === 0 ? (
              <div className="bg-white p-6 rounded-xl border border-stone-200 text-center text-xs text-stone-400">
                No quotations uploaded yet. Use the upload box above.
              </div>
            ) : (
              quotes.map((q) => (
                <div
                  key={q.id}
                  onClick={() => setActiveQuote(q)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    activeQuote?.id === q.id
                      ? 'bg-amber-50/70 border-amber-400 shadow-sm'
                      : 'bg-white border-stone-200 hover:border-stone-300'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-stone-100 text-stone-700">
                        {q.category}
                      </span>
                      <h4 className="font-serif font-bold text-stone-900 text-sm mt-1">{q.vendor_name}</h4>
                    </div>
                    <input
                      type="checkbox"
                      checked={selectedQuoteIds.includes(q.id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleQuoteSelection(q.id);
                      }}
                      className="w-4 h-4 text-[#8B1E28] rounded border-stone-300 focus:ring-amber-400"
                    />
                  </div>

                  <div className="mt-3 flex justify-between items-baseline text-xs">
                    <span className="text-stone-500">Quoted Total</span>
                    <span className="font-bold text-stone-900">
                      ₹{(q.total_quoted_amount || 0).toLocaleString('en-IN')}
                    </span>
                  </div>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-stone-400">
                    <span>{q.line_items.length} line items</span>
                    <span className="text-red-700 font-medium">
                      {q.hidden_cost_alerts.filter((a) => a.status === 'missing_from_quote').length} potential flags
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
                <div className="bg-white rounded-2xl p-6 border border-stone-200 shadow-sm">
                  <div className="flex flex-wrap justify-between items-start gap-4">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-100 text-amber-900">
                          {activeQuote.category}
                        </span>
                        <span className="text-xs text-stone-400">Status: {activeQuote.extraction_status}</span>
                      </div>
                      <h2 className="text-xl font-serif font-bold text-stone-900 mt-1">{activeQuote.vendor_name}</h2>
                      <p className="text-xs text-stone-500">Source: {activeQuote.file_name}</p>
                    </div>

                    <div className="text-right">
                      <div className="text-2xl font-bold font-serif text-[#8B1E28]">
                        ₹{(activeQuote.total_quoted_amount || 0).toLocaleString('en-IN')}
                      </div>
                      {activeQuote.tax_amount ? (
                        <p className="text-xs text-stone-500">Includes ₹{activeQuote.tax_amount.toLocaleString('en-IN')} GST</p>
                      ) : null}
                      <button
                        onClick={() => openNegotiationDrawer(activeQuote)}
                        className="mt-3 px-4 py-2 rounded-xl bg-[#8B1E28] hover:bg-stone-900 text-white text-xs font-semibold transition-all shadow-sm"
                      >
                        Generate Negotiation Letters →
                      </button>
                    </div>
                  </div>

                  {/* Benchmark pill */}
                  {activeQuote.benchmark_comparison && (
                    <div className="mt-4 pt-4 border-t border-stone-100 flex items-center justify-between text-xs">
                      <span className="text-stone-500">Regional Median Benchmark:</span>
                      {activeQuote.benchmark_comparison.is_limited_data ? (
                        <span className="px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 font-medium">
                          Limited data (n &lt; 5)
                        </span>
                      ) : (
                        <span
                          className={`px-2 py-0.5 rounded-full font-medium ${
                            activeQuote.benchmark_comparison.cost_status === 'above_median'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {activeQuote.benchmark_comparison.percentage_diff_vs_median}% vs {activeQuote.benchmark_comparison.city_tier} median (₹{activeQuote.benchmark_comparison.median_unit_cost?.toLocaleString('en-IN')})
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Hidden-Cost Alerts Checklist */}
                <div className="bg-white rounded-2xl p-6 border border-stone-200 shadow-sm">
                  <h3 className="text-sm font-semibold text-stone-900 mb-3">Deterministic Hidden-Cost Analysis</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {activeQuote.hidden_cost_alerts.map((alert) => (
                      <div
                        key={alert.code}
                        className={`p-3 rounded-xl border flex flex-col justify-between text-xs ${
                          alert.status === 'missing_from_quote'
                            ? 'bg-red-50/60 border-red-200'
                            : alert.status === 'explicitly_covered'
                            ? 'bg-emerald-50/60 border-emerald-200'
                            : 'bg-amber-50/60 border-amber-200'
                        }`}
                      >
                        <div>
                          <div className="flex justify-between items-center mb-1">
                            <span className="font-semibold text-stone-900">{alert.name}</span>
                            <span
                              className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                alert.status === 'missing_from_quote'
                                  ? 'bg-red-200 text-red-900'
                                  : 'bg-emerald-200 text-emerald-900'
                              }`}
                            >
                              {alert.status === 'missing_from_quote' ? 'Missing' : 'Covered'}
                            </span>
                          </div>
                          <p className="text-stone-600 text-[11px] leading-relaxed">{alert.description}</p>
                        </div>
                        <div className="mt-2 pt-2 border-t border-stone-200/50 text-[10px] text-stone-500 italic">
                          Ask: "{alert.suggested_question}"
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Line Items Table */}
                <div className="bg-white rounded-2xl p-6 border border-stone-200 shadow-sm overflow-hidden">
                  <h3 className="text-sm font-semibold text-stone-900 mb-3">Extracted Line Items</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-stone-200 text-stone-400 font-medium">
                          <th className="py-2">Item Description</th>
                          <th className="py-2 text-right">Qty</th>
                          <th className="py-2 text-right">Rate</th>
                          <th className="py-2 text-right">Total (₹)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-stone-100">
                        {activeQuote.line_items.map((li, idx) => (
                          <tr key={idx} className="hover:bg-stone-50/50">
                            <td className="py-3 font-medium text-stone-900">
                              <div>{li.name}</div>
                              {li.notes && <div className="text-[11px] text-stone-400">{li.notes}</div>}
                            </td>
                            <td className="py-3 text-right text-stone-600">
                              {li.qty} {li.unit}
                            </td>
                            <td className="py-3 text-right text-stone-600">₹{li.unit_price.toLocaleString('en-IN')}</td>
                            <td className="py-3 text-right font-semibold text-stone-900">
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
              <div className="bg-white rounded-2xl p-12 text-center border border-stone-200 text-stone-400 text-sm">
                Select a quote on the left or upload a new one to view line items and hidden-cost audit.
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Negotiation Drafts Drawer / Modal */}
      {isDraftDrawerOpen && draftTargetQuote && (
        <div className="fixed inset-0 z-50 bg-stone-900/60 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-2xl bg-white h-full shadow-2xl p-6 overflow-y-auto flex flex-col justify-between">
            <div>
              {/* Drawer Header */}
              <div className="flex justify-between items-start pb-4 border-b border-stone-200">
                <div>
                  <span className="text-xs uppercase font-bold text-[#8B1E28]">Negotiation Assistant</span>
                  <h3 className="text-lg font-serif font-bold text-stone-900">
                    Draft Letters for {draftTargetQuote.vendor_name}
                  </h3>
                </div>
                <button
                  onClick={() => setIsDraftDrawerOpen(false)}
                  className="w-8 h-8 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-600 flex items-center justify-center font-bold"
                >
                  ✕
                </button>
              </div>

              {/* Language & Tone Selectors */}
              <div className="mt-4 flex flex-wrap justify-between items-center gap-3">
                {/* Variant Tabs */}
                <div className="flex space-x-1 p-1 bg-stone-100 rounded-xl">
                  {(['polite', 'firm', 'bundle_ask'] as const).map((variant) => (
                    <button
                      key={variant}
                      onClick={() => setActiveVariantTab(variant)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${
                        activeVariantTab === variant ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500'
                      }`}
                    >
                      {variant.replace('_', ' ')}
                    </button>
                  ))}
                </div>

                {/* Language Toggle */}
                <div className="flex space-x-1 p-1 bg-amber-50 border border-amber-200 rounded-xl text-xs font-medium">
                  <button
                    onClick={() => setDraftLanguage('english')}
                    className={`px-3 py-1 rounded-lg ${
                      draftLanguage === 'english' ? 'bg-[#8B1E28] text-white' : 'text-stone-700'
                    }`}
                  >
                    English
                  </button>
                  <button
                    onClick={() => setDraftLanguage('hindi')}
                    className={`px-3 py-1 rounded-lg ${
                      draftLanguage === 'hindi' ? 'bg-[#8B1E28] text-white' : 'text-stone-700'
                    }`}
                  >
                    हिंदी (Devanagari)
                  </button>
                </div>
              </div>

              {/* Draft Message Content */}
              <div className="mt-6 bg-stone-50 rounded-2xl p-5 border border-stone-200 relative">
                {copySuccessMsg && (
                  <div className="absolute top-2 right-2 px-3 py-1 bg-emerald-600 text-white text-xs font-semibold rounded-lg shadow-md animate-fade-in">
                    {copySuccessMsg}
                  </div>
                )}

                {draftVariants ? (
                  <div>
                    <pre className="whitespace-pre-wrap font-sans text-xs text-stone-800 leading-relaxed">
                      {draftVariants[activeVariantTab][draftLanguage]}
                    </pre>

                    <div className="mt-4 pt-4 border-t border-stone-200 flex justify-end">
                      <button
                        onClick={() => handleCopyText(draftVariants[activeVariantTab][draftLanguage])}
                        className="px-4 py-2 rounded-xl bg-stone-900 hover:bg-[#8B1E28] text-white text-xs font-semibold flex items-center space-x-2 transition-all shadow-sm"
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
              <div className="mt-6 p-4 rounded-xl bg-stone-100 text-[11px] text-stone-600 leading-normal">
                <strong>Human-in-the-loop guarantee:</strong> Utsav never dispatches communication without human review. You can paste this text directly into WhatsApp or email and modify any terms to suit your family’s tone.
              </div>
            </div>

            <div className="pt-4 border-t border-stone-200">
              <button
                onClick={() => setIsDraftDrawerOpen(false)}
                className="w-full py-2.5 rounded-xl border border-stone-300 text-stone-700 text-xs font-medium hover:bg-stone-100"
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
