"use client";

import React, { useState, useEffect } from "react";
import { getAuthHeaders } from "@/lib/auth";

interface InvitationStudioProps {
  eventId: string;
  eventName: string;
  city: string;
  startDate?: string;
  apiBase: string;
}

interface LayoutOption {
  id: string;
  name: string;
  description: string;
  recommended_for: string;
}

interface WordingVariant {
  id: string;
  title: string;
  body_text: string;
  tone: string;
}

interface CardSummary {
  id: string;
  event_id: string;
  layout_variant: string;
  guest_id?: string;
  guest_name?: string;
  wording_preview: string;
  generated_at: string;
  png_download_url: string;
  pdf_download_url: string;
}

interface FailedGuest {
  guest_id: string;
  name: string;
  reason: string;
}

export function InvitationStudio({
  eventId,
  eventName,
  city,
  startDate,
  apiBase,
}: InvitationStudioProps) {
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Studio Options Data
  const [layoutOptions, setLayoutOptions] = useState<LayoutOption[]>([]);
  const [palette, setPalette] = useState<string[]>([
    "#B45309",
    "#991B1B",
    "#FEF3C7",
    "#1E3A8A",
    "#D97706",
  ]);
  const [themeName, setThemeName] = useState<string | null>(null);
  const [themeProposalId, setThemeProposalId] = useState<string | null>(null);
  const [hostName, setHostName] = useState<string | null>(null);
  const [dateStr, setDateStr] = useState<string>(
    startDate || "Date to be confirmed",
  );
  const [venueStr, setVenueStr] = useState<string>(
    city ? `${city} (Venue to be confirmed)` : "Venue to be confirmed",
  );
  const [muhuratTime, setMuhuratTime] = useState<string | null>(null);
  const [ceremonies, setCeremonies] = useState<string[]>([]);
  const [guestCount, setGuestCount] = useState<number>(0);
  const [wordingOptions, setWordingOptions] = useState<WordingVariant[]>([]);
  const [providerUsed, setProviderUsed] = useState<string>("stub");
  const [fallbackWarning, setFallbackWarning] = useState<string | null>(null);
  const [contentReviewNote, setContentReviewNote] = useState<string>("");

  // User Selection State
  const [selectedLayout, setSelectedLayout] = useState<string>("classic_royal");
  const [selectedWordingIndex, setSelectedWordingIndex] = useState<number>(0);
  const [customWording, setCustomWording] = useState<string>("");

  // Generated Cards
  const [generatedCards, setGeneratedCards] = useState<CardSummary[]>([]);
  const [failedGuests, setFailedGuests] = useState<FailedGuest[]>([]);
  const [activePreviewCard, setActivePreviewCard] =
    useState<CardSummary | null>(null);

  // 1. Fetch Studio Options & Existing Cards on Mount
  useEffect(() => {
    let isMounted = true;

    async function loadStudio() {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        // Fetch options
        const optRes = await fetch(
          `${apiBase}/api/v1/events/${eventId}/invitations/options`,
          {
            headers: getAuthHeaders(eventId),
          },
        );
        if (!optRes.ok)
          throw new Error(
            `Failed to fetch invitation options: HTTP ${optRes.status}`,
          );
        const optData = await optRes.json();

        if (isMounted) {
          setLayoutOptions(optData.layout_options || []);
          setPalette(
            optData.palette && optData.palette.length
              ? optData.palette
              : ["#B45309", "#991B1B", "#FEF3C7"],
          );
          setThemeName(optData.theme_name);
          setThemeProposalId(optData.theme_proposal_id);
          setHostName(optData.host_name);
          setDateStr(optData.date_str || startDate || "Date to be confirmed");
          setVenueStr(optData.venue_str || "Venue to be confirmed");
          setMuhuratTime(optData.muhurat_time);
          setCeremonies(optData.ceremonies || []);
          setGuestCount(optData.guest_count || 0);
          setWordingOptions(optData.wording_options || []);
          setProviderUsed(optData.provider_used || "stub");
          setFallbackWarning(optData.fallback_warning);
          setContentReviewNote(optData.content_review_note);

          if (optData.wording_options && optData.wording_options.length > 0) {
            setCustomWording(optData.wording_options[0].body_text);
          }
        }

        // Fetch existing generated cards
        const cardsRes = await fetch(
          `${apiBase}/api/v1/events/${eventId}/invitations`,
          {
            headers: getAuthHeaders(eventId),
          },
        );
        if (cardsRes.ok) {
          const cardsData: CardSummary[] = await cardsRes.json();
          if (isMounted) {
            setGeneratedCards(cardsData);
            if (cardsData.length > 0) {
              setActivePreviewCard(cardsData[0] ?? null);
            }
          }
        }
      } catch (err: unknown) {
        if (isMounted) {
          setErrorMessage(
            (err instanceof Error ? err.message : String(err)) ||
              "Error initializing Invitation Studio",
          );
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    if (eventId) {
      loadStudio();
    }

    return () => {
      isMounted = false;
    };
  }, [eventId, apiBase, startDate]);

  // Handle Wording Selection
  const handleSelectWording = (index: number) => {
    setSelectedWordingIndex(index);
    if (wordingOptions[index]) {
      setCustomWording(wordingOptions[index].body_text);
    }
  };

  // 2. Generate Cards (Batch or Single)
  const handleGenerateCards = async () => {
    setIsGenerating(true);
    setErrorMessage(null);
    try {
      const payload = {
        theme_proposal_id: themeProposalId,
        layout_variant: selectedLayout,
        wording_text: customWording,
        wording_variant_index: selectedWordingIndex,
      };

      const res = await fetch(
        `${apiBase}/api/v1/events/${eventId}/invitations/generate`,
        {
          method: "POST",
          headers: getAuthHeaders(eventId, {
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(payload),
        },
      );

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(
          errJson.detail || `Generation failed: HTTP ${res.status}`,
        );
      }

      const data = await res.json();
      setGeneratedCards(data.cards || []);
      setFailedGuests(data.failed_guests || []);
      if (data.cards && data.cards.length > 0) {
        setActivePreviewCard(data.cards[0]);
      }
    } catch (err: unknown) {
      setErrorMessage(
        (err instanceof Error ? err.message : String(err)) ||
          "Error generating cards",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="glass-card p-12 rounded-3xl border border-stone-200 dark:border-stone-800 text-center space-y-4">
        <div className="w-12 h-12 rounded-full border-4 border-amber-500 border-t-transparent animate-spin mx-auto" />
        <p className="text-sm font-semibold text-stone-700 dark:text-stone-300">
          Composing your invitation studio...
        </p>
      </div>
    );
  }

  const primaryColor = palette[0] || "#B45309";
  const secondaryColor = palette[1] || "#991B1B";
  const accentColor = palette[2] || "#FEF3C7";

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header & Truthfulness Banners */}
      <div className="glass-card p-6 sm:p-8 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 mb-2">
              <span>🎴</span> Milestone M10 • F16 Invitation Studio
            </div>
            <h2 className="text-2xl sm:text-3xl font-serif font-bold text-stone-900 dark:text-stone-100">
              Personalized Invitation Cards
            </h2>
            <p className="text-sm text-stone-600 dark:text-stone-300 mt-1">
              Deterministic server-side Pillow composition (DEC-028), theme
              palette binding, and individual guest personalization (DEC-029).
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerateCards}
              disabled={isGenerating}
              className="px-6 py-3 rounded-2xl bg-amber-700 hover:bg-amber-800 text-white font-bold text-sm shadow-md transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Rendering Cards...
                </>
              ) : (
                <>
                  <span>✨</span>
                  {guestCount > 0
                    ? `Generate Batch (${guestCount} Guests)`
                    : "Generate Generic Card"}
                </>
              )}
            </button>
          </div>
        </div>

        {/* Mandatory Cultural Truthfulness Disclaimer */}
        <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 p-4 rounded-2xl flex items-start gap-3 text-xs text-amber-900 dark:text-amber-200">
          <span className="text-lg">🕉️</span>
          <div>
            <p className="font-bold">
              Cultural Review Reminder (DEC-027 Safeguard):
            </p>
            <p className="mt-0.5">
              {contentReviewNote ||
                "Auspicious muhurats, ceremony names, and phrasing are starting baselines. Please review with family elders or priests before printing."}
            </p>
          </div>
        </div>

        {errorMessage && (
          <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-300 text-xs text-red-800 dark:text-red-300">
            {errorMessage}
          </div>
        )}
      </div>

      {/* Main Studio Grid */}
      <div className="grid lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Layout & Wording Selection (7 Cols) */}
        <div className="lg:col-span-7 space-y-8">
          {/* Component 1: InvitationLayoutPicker */}
          <section className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                <span>🎨</span> 1. Select Layout Template
              </h3>
              <span className="text-xs text-stone-500">
                Theme: {themeName || "Celebration Gold"}
              </span>
            </div>

            <div className="grid sm:grid-cols-3 gap-4">
              {layoutOptions.map((opt) => {
                const isSelected = selectedLayout === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setSelectedLayout(opt.id)}
                    className={`p-4 rounded-2xl text-left border-2 transition-all flex flex-col justify-between h-44 ${
                      isSelected
                        ? "border-amber-600 bg-amber-50/50 dark:bg-amber-950/30 shadow-md ring-2 ring-amber-400/20"
                        : "border-stone-200 dark:border-stone-800 hover:border-amber-300 bg-white/50 dark:bg-stone-900/40"
                    }`}
                  >
                    <div>
                      {/* Mini Thumbnail Visual */}
                      <div
                        className="w-full h-12 rounded-lg mb-3 flex items-center justify-center p-1"
                        style={{ backgroundColor: accentColor }}
                      >
                        <div
                          className="w-full h-full rounded border border-dashed flex items-center justify-center text-[10px] font-serif font-bold"
                          style={{
                            borderColor: primaryColor,
                            color: primaryColor,
                          }}
                        >
                          {opt.id === "classic_royal" && "|| श्री ||"}
                          {opt.id === "modern_minimal" && "▌ MINIMAL"}
                          {opt.id === "floral_festive" && "✿ FESTIVE"}
                        </div>
                      </div>
                      <h4 className="text-xs font-bold text-stone-900 dark:text-stone-100">
                        {opt.name}
                      </h4>
                      <p className="text-[11px] text-stone-500 dark:text-stone-400 mt-1 line-clamp-2 leading-tight">
                        {opt.description}
                      </p>
                    </div>
                    <span className="text-[10px] font-semibold text-amber-700 dark:text-amber-400">
                      {isSelected ? "✓ Selected" : "Choose"}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Component 2: InvitationWordingSelector */}
          <section className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                <span>✍️</span> 2. Choose Phrasing & Wording
              </h3>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  providerUsed === "gemini"
                    ? "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300"
                    : "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300"
                }`}
              >
                Agent:{" "}
                {providerUsed === "gemini"
                  ? "Gemini AI Composer"
                  : "Deterministic Stub"}
              </span>
            </div>

            {fallbackWarning && (
              <p className="text-xs text-amber-600 dark:text-amber-400 italic">
                Notice: {fallbackWarning}
              </p>
            )}

            <div className="grid sm:grid-cols-3 gap-3">
              {wordingOptions.map((opt, idx) => {
                const isSelected = selectedWordingIndex === idx;
                return (
                  <button
                    key={opt.id}
                    onClick={() => handleSelectWording(idx)}
                    className={`p-3 rounded-2xl text-left border transition-all text-xs ${
                      isSelected
                        ? "border-amber-600 bg-amber-50 dark:bg-amber-950/40 text-amber-950 dark:text-amber-100 font-semibold"
                        : "border-stone-200 dark:border-stone-800 text-stone-600 dark:text-stone-400 hover:border-stone-300"
                    }`}
                  >
                    <div className="font-bold">{opt.title}</div>
                    <div className="text-[10px] opacity-75 mt-0.5">
                      {opt.tone}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Editable Wording Textarea */}
            <div className="space-y-2 pt-2">
              <label className="text-xs font-semibold text-stone-700 dark:text-stone-300">
                Card Wording (Strictly Interpolates Confirmed Event Logistics):
              </label>
              <textarea
                value={customWording}
                onChange={(e) => setCustomWording(e.target.value)}
                rows={4}
                className="w-full text-xs rounded-2xl border border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-stone-900 p-3 leading-relaxed focus:outline-none focus:ring-2 focus:ring-amber-500 text-stone-800 dark:text-stone-200"
                placeholder="Enter custom invitation wording..."
              />
            </div>
          </section>

          {/* Component 4: GuestCardBatchStatus */}
          {generatedCards.length > 0 && (
            <section className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                  <span>👥</span> Guest Card Batch Roster (
                  {generatedCards.length} Ready)
                </h3>
                {failedGuests.length > 0 && (
                  <span className="text-xs font-bold text-red-600 bg-red-100 dark:bg-red-950/60 px-2 py-0.5 rounded-full">
                    {failedGuests.length} Failed
                  </span>
                )}
              </div>

              {failedGuests.length > 0 && (
                <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 text-xs text-red-800 dark:text-red-300 space-y-1">
                  <p className="font-bold">
                    Partial Guest Failures (Other cards rendered successfully):
                  </p>
                  {failedGuests.map((f) => (
                    <p key={f.guest_id}>
                      • <strong>{f.name}</strong>: {f.reason}
                    </p>
                  ))}
                </div>
              )}

              <div className="divide-y divide-stone-100 dark:divide-stone-800 max-h-60 overflow-y-auto">
                {generatedCards.map((c) => {
                  const isActive = activePreviewCard?.id === c.id;
                  return (
                    <div
                      key={c.id}
                      className={`py-3 px-2 flex items-center justify-between rounded-xl transition-all cursor-pointer ${
                        isActive
                          ? "bg-amber-50 dark:bg-amber-950/30"
                          : "hover:bg-stone-50 dark:hover:bg-stone-900/50"
                      }`}
                      onClick={() => setActivePreviewCard(c)}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-lg">💌</span>
                        <div>
                          <p className="text-xs font-bold text-stone-900 dark:text-stone-100">
                            {c.guest_name
                              ? `Invited: ${c.guest_name}`
                              : "Generic Shared Card"}
                          </p>
                          <p className="text-[10px] text-stone-500">
                            {c.layout_variant} •{" "}
                            {new Date(c.generated_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <a
                          href={`${apiBase}${c.png_download_url}`}
                          target="_blank"
                          rel="noreferrer"
                          download
                          className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-stone-100 dark:bg-stone-800 hover:bg-stone-200 text-stone-700 dark:text-stone-300"
                          onClick={(e) => e.stopPropagation()}
                        >
                          PNG ↓
                        </a>
                        <a
                          href={`${apiBase}${c.pdf_download_url}`}
                          target="_blank"
                          rel="noreferrer"
                          download
                          className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 hover:bg-amber-200"
                          onClick={(e) => e.stopPropagation()}
                        >
                          PDF ↓
                        </a>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </div>

        {/* Right Column: Live Card Preview & Export (5 Cols) */}
        <div className="lg:col-span-5 sticky top-6">
          <section className="glass-card p-6 rounded-3xl border border-stone-200/80 dark:border-stone-800/80 space-y-4 shadow-lg">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                <span>👁️</span> Live Card Preview
              </h3>
              {activePreviewCard && (
                <div className="flex items-center gap-2">
                  <a
                    href={`${apiBase}${activePreviewCard.png_download_url}`}
                    target="_blank"
                    rel="noreferrer"
                    download
                    className="px-3 py-1 text-xs font-bold rounded-xl bg-amber-700 hover:bg-amber-800 text-white"
                  >
                    PNG
                  </a>
                  <a
                    href={`${apiBase}${activePreviewCard.pdf_download_url}`}
                    target="_blank"
                    rel="noreferrer"
                    download
                    className="px-3 py-1 text-xs font-bold rounded-xl bg-stone-800 hover:bg-stone-900 text-white dark:bg-stone-200 dark:text-stone-900"
                  >
                    PDF
                  </a>
                </div>
              )}
            </div>

            {/* Server-Rendered PNG or HTML Canvas Mockup */}
            {activePreviewCard ? (
              <div className="space-y-3">
                <div className="rounded-2xl overflow-hidden border-2 border-amber-500/40 shadow-inner bg-stone-100 dark:bg-stone-950 flex items-center justify-center p-2">
                  <img
                    src={`${apiBase}${activePreviewCard.png_download_url}`}
                    alt="Rendered Invitation Card"
                    className="w-full max-h-[580px] object-contain rounded-xl shadow"
                  />
                </div>
                <p className="text-[11px] text-center text-stone-500">
                  Showing server-composed Pillow card for{" "}
                  {activePreviewCard.guest_name || "Generic Host Copy"}
                </p>
              </div>
            ) : (
              /* High-fidelity CSS Preview before user hits generate */
              <div
                className="rounded-2xl p-6 border-4 shadow-md text-center space-y-4 transition-all"
                style={{
                  backgroundColor: "#FFFDF9",
                  borderColor: primaryColor,
                }}
              >
                <div
                  className="text-xs font-serif font-bold tracking-widest uppercase"
                  style={{ color: secondaryColor }}
                >
                  {selectedLayout === "classic_royal"
                    ? "|| श्री गणेशाय नमः ||"
                    : "CORDIAL INVITATION"}
                </div>

                <div className="text-xs text-stone-600">
                  {hostName
                    ? `Together with their families\n${hostName}`
                    : "We warmly request the honor of your presence"}
                </div>

                <h4
                  className="text-xl font-serif font-extrabold"
                  style={{ color: primaryColor }}
                >
                  {eventName}
                </h4>

                <p className="text-xs text-stone-700 leading-relaxed max-w-xs mx-auto">
                  {customWording ||
                    "You are cordially invited to celebrate with us."}
                </p>

                {/* Date / Muhurat Box */}
                <div
                  className="p-3 rounded-xl border border-dashed mx-auto max-w-xs"
                  style={{
                    borderColor: primaryColor,
                    backgroundColor: "#FFF7ED",
                  }}
                >
                  <p
                    className="text-xs font-bold"
                    style={{ color: primaryColor }}
                  >
                    {dateStr}
                  </p>
                  {muhuratTime && (
                    <p className="text-[11px] font-semibold text-amber-700 mt-0.5">
                      Auspicious Muhurat: {muhuratTime}
                    </p>
                  )}
                </div>

                {/* Venue */}
                <div className="text-xs text-stone-600 max-w-xs mx-auto">
                  <span className="font-semibold text-stone-800">Venue:</span>{" "}
                  {venueStr}
                </div>

                {/* Personalization Footer */}
                <div
                  className="pt-4 border-t border-stone-200 text-xs font-bold"
                  style={{ color: secondaryColor }}
                >
                  {guestCount > 0
                    ? `Specially Invited: [Guest Name interpolated per card]`
                    : "Warmest Welcome to You and Your Family"}
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
