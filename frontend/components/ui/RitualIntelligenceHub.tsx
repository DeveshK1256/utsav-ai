'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { getAuthHeaders } from '@/lib/auth';

interface RitualHubProps {
  eventId: string;
  eventName: string;
  city: string;
  startDate?: string;
  initialTraditionCode?: string;
  initialSecondaryTraditionCode?: string;
  apiBase: string;
  onTasksGenerated?: () => void;
}

interface TraditionOption {
  code: string;
  regional_name: string;
  description: string;
  is_verified: boolean;
  verification_source?: string;
  item_count: number;
}

interface CeremonyItem {
  name: string;
  origin_tradition: string;
  day_offset: number;
  start_time: string;
  duration_hours: number;
  venue_type: string;
  is_outdoor: boolean;
  is_muhurat_locked: boolean;
  cultural_significance: string;
  family_guidance?: string;
}

interface AlignmentPoint {
  issue: string;
  description: string;
  recommendation: string;
}

interface MuhuratCandidate {
  id: string;
  name: string;
  window: string;
  suitability: string;
  planetary_rationale: string;
  is_recommended: boolean;
}

interface PanchangData {
  sunrise: string;
  sunset: string;
  rahu_kaal: {
    start: string;
    end: string;
    octile_index: number;
    is_inauspicious: boolean;
  };
  abhijit_muhurat: {
    start: string;
    end: string;
    is_auspicious: boolean;
    caution?: string | null;
  };
  tithi: {
    name: string;
    paksha: string;
    percent_elapsed: number;
  };
  nakshatra: {
    name: string;
    percent_elapsed: number;
  };
  priest_disclaimer: string;
}

export const RitualIntelligenceHub: React.FC<RitualHubProps> = ({
  eventId,
  eventName,
  city,
  startDate,
  initialTraditionCode = 'maharashtrian_vedic',
  initialSecondaryTraditionCode,
  apiBase,
  onTasksGenerated
}) => {
  const [traditions, setTraditions] = useState<TraditionOption[]>([]);
  const [primaryTradition, setPrimaryTradition] = useState<string>(initialTraditionCode);
  const [secondaryTradition, setSecondaryTradition] = useState<string>(initialSecondaryTraditionCode || 'punjabi_traditional');
  const [isDualTradition, setIsDualTradition] = useState<boolean>(Boolean(initialSecondaryTraditionCode) || true);

  // Panchang and Muhurats
  const [panchang, setPanchang] = useState<PanchangData | null>(null);
  const [muhuratCandidates, setMuhuratCandidates] = useState<MuhuratCandidate[]>([]);
  const [isLoadingPanchang, setIsLoadingPanchang] = useState<boolean>(true);

  // Run of Show & Merge Data
  const [mergedTitle, setMergedTitle] = useState<string>('');
  const [ceremonies, setCeremonies] = useState<CeremonyItem[]>([]);
  const [alignmentPoints, setAlignmentPoints] = useState<AlignmentPoint[]>([]);
  const [samagriItems, setSamagriItems] = useState<any[]>([]);
  const [isMerging, setIsMerging] = useState<boolean>(false);
  const [mergeSuccessMsg, setMergeSuccessMsg] = useState<string | null>(null);

  // Task generation state
  const [isGeneratingTasks, setIsGeneratingTasks] = useState<boolean>(false);
  const [taskSuccessMsg, setTaskSuccessMsg] = useState<string | null>(null);

  const eventDate = useMemo(() => {
    return startDate ? startDate.split('T')[0] : new Date().toISOString().split('T')[0];
  }, [startDate]);

  // Load traditions and initial panchang
  useEffect(() => {
    async function loadInitialData() {
      try {
        // 1. Fetch available traditions
        const tradRes = await fetch(`${apiBase}/api/v1/rituals/traditions`);
        if (tradRes.ok) {
          const tradData = await tradRes.json();
          setTraditions(tradData);
        }

        // 2. Fetch live panchang & candidates for event location
        const pRes = await fetch(`${apiBase}/api/v1/rituals/panchang?event_date=${eventDate}`);
        if (pRes.ok) {
          const pData = await pRes.json();
          setPanchang(pData);
        }

        const candRes = await fetch(`${apiBase}/api/v1/rituals/muhurat-candidates?event_date=${eventDate}`);
        if (candRes.ok) {
          const candData = await candRes.json();
          setMuhuratCandidates(candData.candidates || []);
        }
      } catch (err) {
        console.error('Failed to load ritual metadata:', err);
      } finally {
        setIsLoadingPanchang(false);
      }
    }
    loadInitialData();
  }, [apiBase, eventDate]);

  // Trigger merge on mount or when requested
  const handleMergeTraditions = async () => {
    setIsMerging(true);
    setMergeSuccessMsg(null);
    try {
      const res = await fetch(`${apiBase}/api/v1/rituals/merge-traditions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          primary_tradition_code: primaryTradition,
          secondary_tradition_code: isDualTradition ? secondaryTradition : primaryTradition,
          start_date: eventDate,
          event_id: eventId
        })
      });

      if (res.ok) {
        const data = await res.json();
        setMergedTitle(data.fusion_title);
        setCeremonies(data.run_of_show || []);
        setAlignmentPoints(data.family_alignment_points || []);
        setSamagriItems(data.samagri_items || []);
        setMergeSuccessMsg('✨ Cultural traditions harmonized into unified run-of-show.');
      }
    } catch (err) {
      console.error('Merge traditions error:', err);
    } finally {
      setIsMerging(false);
    }
  };

  useEffect(() => {
    handleMergeTraditions();
  }, [primaryTradition, secondaryTradition, isDualTradition]);

  // Generate ritual tasks into DAG
  const handleGenerateTasks = async () => {
    setIsGeneratingTasks(true);
    setTaskSuccessMsg(null);
    try {
      const res = await fetch(`${apiBase}/api/v1/rituals/events/${eventId}/generate-tasks`, {
        method: 'POST',
        headers: getAuthHeaders(eventId)
      });
      if (res.ok) {
        const data = await res.json();
        setTaskSuccessMsg(`✅ Created ${data.tasks_created_count} ritual procurement tasks into your timeline.`);
        if (onTasksGenerated) onTasksGenerated();
      }
    } catch (err) {
      console.error('Task generation error:', err);
    } finally {
      setIsGeneratingTasks(false);
    }
  };

  const getOriginBadge = (origin: string) => {
    if (origin.includes('Shared') || origin.includes('Combined')) {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
          🕉️ Shared / Combined
        </span>
      );
    }
    if (origin.toLowerCase().includes('maharashtrian')) {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
          🚩 {origin}
        </span>
      );
    }
    if (origin.toLowerCase().includes('punjabi')) {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
          ✨ {origin}
        </span>
      );
    }
    if (origin.toLowerCase().includes('tamil') || origin.toLowerCase().includes('iyer')) {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
          🌸 {origin}
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
        🪔 {origin}
      </span>
    );
  };

  return (
    <div className="space-y-8">
      {/* 0. MANDATORY CEREMONY CONTENT ACCURACY & UNREVIEWED STATUS BANNER */}
      <div className="rounded-2xl bg-rose-500/10 dark:bg-rose-500/5 border-2 border-rose-500/50 dark:border-rose-500/40 p-6 shadow-md relative overflow-hidden">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-rose-500/20 text-rose-700 dark:text-rose-300 rounded-xl text-2xl flex-shrink-0">
            ⚠️
          </div>
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-bold text-rose-950 dark:text-rose-100 uppercase tracking-wide">
                Mandatory Priest & Elder Review Required — AI-Drafted Baseline
              </h3>
              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-rose-200/80 dark:bg-rose-900/60 text-rose-900 dark:text-rose-200">
                Unreviewed Content
              </span>
            </div>
            <p className="text-sm text-rose-900 dark:text-rose-200 leading-relaxed font-serif">
              This ceremonial sequence and ritual item list was <strong>AI-drafted as a starting point</strong> based on general knowledge of cultural customs. It has <strong>NOT been reviewed by a priest, pandit, community elder, or religious authority</strong> and may contain errors, omissions, or regionally inappropriate details.
            </p>
            <div className="p-3 bg-rose-100/70 dark:bg-rose-900/30 rounded-xl border border-rose-300/60 dark:border-rose-700/60 text-xs text-rose-950 dark:text-rose-200 font-medium flex items-center gap-2">
              <span>
                <strong>Action Required:</strong> Please review this timeline, ritual order, and samagri list carefully with your family elders and officiating priest before finalizing dates, booking venues, or printing invitation cards.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 1. ELEVATED AUSTERE MUHURAT & PANCHANG MANDATE BANNER */}
      <div className="rounded-2xl bg-amber-500/10 dark:bg-amber-500/5 border-2 border-amber-500/40 dark:border-amber-500/30 p-6 shadow-md relative overflow-hidden">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-amber-500/20 text-amber-700 dark:text-amber-300 rounded-xl text-2xl flex-shrink-0">
            🕉️
          </div>
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-amber-950 dark:text-amber-100 uppercase tracking-wide">
                Astronomical Muhurat & Panchang Guidance (Drik Standard)
              </h3>
              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-200/60 dark:bg-amber-900/50 text-amber-900 dark:text-amber-200">
                Lahiri Ayanamsha
              </span>
            </div>
            <p className="text-sm text-amber-900 dark:text-amber-200 leading-relaxed font-serif">
              Calculated using astronomical ephemeris formulas for <strong>{city}</strong> on <strong>{eventDate}</strong>.
              Regional almanacs (Kalnirnay, Vakya, Surya Siddhanta, or KP Ayanamsha) often vary by 10–20 minutes due to differing horizon and refraction models.
            </p>
            <div className="p-3 bg-amber-100/70 dark:bg-amber-900/30 rounded-xl border border-amber-300/50 dark:border-amber-700/50 text-xs text-amber-950 dark:text-amber-200 font-medium flex items-center gap-2">
              <span className="text-base">⚠️</span>
              <span>
                <strong>Mandatory for Hosts:</strong> Always verify your final auspicious pheras and vidhi muhurat with your family priest (Panditji / Guruji) before printing cards.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. SOLAR-LUNAR TELEMETRY & CANDIDATE MUHURATS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Solar & Lunar Card */}
        <div className="rounded-2xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-100 dark:border-neutral-800 pb-3">
            <h4 className="font-semibold text-sm text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
              <span>☀️</span> Solar-Lunar Telemetry
            </h4>
            <span className="text-xs text-neutral-500">{city}</span>
          </div>
          {isLoadingPanchang || !panchang ? (
            <div className="text-xs text-neutral-400 py-4 text-center">Calculating planetary coordinates...</div>
          ) : (
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center py-1 border-b border-neutral-50 dark:border-neutral-800/50">
                <span className="text-neutral-500">Apparent Sunrise</span>
                <span className="font-mono font-medium text-neutral-900 dark:text-neutral-100">{panchang.sunrise} IST</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-neutral-50 dark:border-neutral-800/50">
                <span className="text-neutral-500">Apparent Sunset</span>
                <span className="font-mono font-medium text-neutral-900 dark:text-neutral-100">{panchang.sunset} IST</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-neutral-50 dark:border-neutral-800/50">
                <span className="text-neutral-500">Prevailing Tithi</span>
                <span className="font-medium text-neutral-900 dark:text-neutral-100">{panchang.tithi.name} ({panchang.tithi.paksha} Paksha)</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-neutral-50 dark:border-neutral-800/50">
                <span className="text-neutral-500">Ruling Nakshatra</span>
                <span className="font-medium text-neutral-900 dark:text-neutral-100">{panchang.nakshatra.name}</span>
              </div>
              <div className="flex justify-between items-center py-1.5 px-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/20 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900/40">
                <span>🚫 Prohibited Rahu Kaal</span>
                <span className="font-mono font-bold">{panchang.rahu_kaal.start.slice(0, 5)} - {panchang.rahu_kaal.end.slice(0, 5)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Auspicious Muhurat Windows */}
        <div className="md:col-span-2 rounded-2xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-100 dark:border-neutral-800 pb-3">
            <h4 className="font-semibold text-sm text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
              <span>⭐</span> Auspicious Candidate Windows (Ephemeris)
            </h4>
            <span className="text-xs text-neutral-500">Ranked by Astrological Suitability</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {muhuratCandidates.map((c) => (
              <div
                key={c.id}
                className={`p-3.5 rounded-xl border transition-all ${
                  c.is_recommended
                    ? 'bg-amber-50/60 dark:bg-amber-950/20 border-amber-300 dark:border-amber-700/60'
                    : 'bg-neutral-50/70 dark:bg-neutral-800/40 border-neutral-200 dark:border-neutral-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-neutral-900 dark:text-neutral-100">{c.name}</span>
                  {c.is_recommended && (
                    <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-amber-500 text-white uppercase">
                      Top Pick
                    </span>
                  )}
                </div>
                <div className="text-base font-bold font-mono text-neutral-950 dark:text-white mb-1">
                  {c.window}
                </div>
                <p className="text-[11px] text-neutral-600 dark:text-neutral-400 line-clamp-2">
                  {c.planetary_rationale}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 3. MULTI-TRADITION FUSION STUDIO */}
      <div className="rounded-2xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-neutral-100 dark:border-neutral-800 pb-4">
          <div>
            <h3 className="font-bold text-lg text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
              <span>🎭</span> Cultural Traditions & Cross-Lineage Fusion
            </h3>
            <p className="text-xs text-neutral-500 mt-1">
              Combine two cultural traditions into a reconciled, respectful run-of-show with origin attribution.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleMergeTraditions}
              disabled={isMerging}
              className="px-4 py-2 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white dark:bg-neutral-100 dark:hover:bg-white dark:text-neutral-900 text-xs font-semibold shadow transition disabled:opacity-50"
            >
              {isMerging ? 'Reconciling...' : '⚡ Re-Synthesize Fusion'}
            </button>
          </div>
        </div>

        {/* Tradition Selectors */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1.5">
              Primary Cultural Tradition
            </label>
            <select
              value={primaryTradition}
              onChange={(e) => setPrimaryTradition(e.target.value)}
              className="w-full text-xs rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2.5 text-neutral-900 dark:text-neutral-100 focus:ring-2 focus:ring-amber-500"
            >
              {traditions.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.regional_name} (AI-Drafted Baseline — Unreviewed)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300 mb-1.5 flex items-center justify-between">
              <span>Secondary Tradition (Cross-Cultural Fusion)</span>
              <span className="text-[11px] text-amber-600 dark:text-amber-400 font-normal">Dual Heritage</span>
            </label>
            <select
              value={secondaryTradition}
              onChange={(e) => setSecondaryTradition(e.target.value)}
              className="w-full text-xs rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2.5 text-neutral-900 dark:text-neutral-100 focus:ring-2 focus:ring-amber-500"
            >
              {traditions.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.regional_name} (AI-Drafted Baseline — Unreviewed)
                </option>
              ))}
            </select>
          </div>
        </div>

        {mergeSuccessMsg && (
          <div className="p-3 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs rounded-xl flex items-center justify-between">
            <span>{mergeSuccessMsg}</span>
            <span className="font-bold">{mergedTitle}</span>
          </div>
        )}

        {/* 4. MERGED RUN-OF-SHOW CEREMONIES */}
        <div className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <h4 className="font-bold text-sm text-neutral-900 dark:text-neutral-100 uppercase tracking-wide">
              Unified Chronological Run-of-Show
            </h4>
            <span className="text-xs text-neutral-500">{ceremonies.length} Ceremonies Planned</span>
          </div>

          <div className="space-y-3">
            {ceremonies.map((c, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50/40 dark:bg-neutral-850 hover:border-amber-400/50 transition-all space-y-2.5"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-neutral-200 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300">
                      Day {c.day_offset + 1} • {c.start_time}
                    </span>
                    <h5 className="font-semibold text-sm text-neutral-900 dark:text-neutral-100">
                      {c.name}
                    </h5>
                    {getOriginBadge(c.origin_tradition)}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-neutral-500">
                    <span>⏳ {c.duration_hours} hrs</span>
                    <span>•</span>
                    <span>{c.is_outdoor ? '🌿 Outdoor' : '🏛️ Indoor'}</span>
                    {c.is_muhurat_locked && (
                      <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                        🔒 Muhurat Locked
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed font-serif">
                  {c.cultural_significance}
                </p>

                {c.family_guidance && (
                  <div className="p-2.5 rounded-lg bg-amber-50/70 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-800/40 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2">
                    <span className="flex-shrink-0">💡</span>
                    <span><strong>Family Alignment Note:</strong> {c.family_guidance}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 5. FAMILY ALIGNMENT POINTS & DISCREPANCIES */}
        {alignmentPoints.length > 0 && (
          <div className="space-y-3 pt-4 border-t border-neutral-100 dark:border-neutral-800">
            <h4 className="font-bold text-sm text-neutral-900 dark:text-neutral-100 uppercase tracking-wide flex items-center gap-2">
              <span>🤝</span> Elder & Family Alignment Checkpoints
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {alignmentPoints.map((p, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-800 space-y-2 text-xs"
                >
                  <h5 className="font-bold text-neutral-900 dark:text-neutral-100 text-xs">
                    ⚠️ {p.issue}
                  </h5>
                  <p className="text-neutral-600 dark:text-neutral-400">
                    {p.description}
                  </p>
                  <div className="pt-1.5 text-amber-800 dark:text-amber-300 font-medium">
                    👉 <strong>Recommendation:</strong> {p.recommendation}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 6. DAG TASK GENERATION & PRIEST EXPORT ACTIONS */}
        <div className="pt-4 border-t border-neutral-100 dark:border-neutral-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h5 className="font-semibold text-xs text-neutral-900 dark:text-neutral-100">
              Integrate into Master DAG Execution Graph
            </h5>
            <p className="text-xs text-neutral-500">
              Converts AI-drafted samagri checklists into scheduled procurement tasks assigned to elders for review.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={`${apiBase}/api/v1/rituals/events/${eventId}/pandit-guide`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-xl border border-neutral-300 dark:border-neutral-700 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-800 text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <span>📄</span> Export Pandit Guide (JSON/Print)
            </a>
            <button
              onClick={handleGenerateTasks}
              disabled={isGeneratingTasks}
              className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold shadow transition disabled:opacity-50"
            >
              {isGeneratingTasks ? 'Generating Tasks...' : '📌 Attach Tasks to Timeline'}
            </button>
          </div>
        </div>

        {taskSuccessMsg && (
          <div className="p-3 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs rounded-xl">
            {taskSuccessMsg}
          </div>
        )}
      </div>
    </div>
  );
};
