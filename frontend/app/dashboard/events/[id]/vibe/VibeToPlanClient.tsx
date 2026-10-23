'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Navbar } from '@/components/ui/Navbar';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location.hostname.includes('netlify.app')
    ? '/api/v1'
    : 'https://utsav-ai-ycg2.onrender.com/api/v1');

interface StyleProfile {
  profile_id: string;
  event_id: string;
  extracted_palette: string[];
  style_tags: string[];
  mood_words: string[];
  text_description?: string | null;
  uploaded_image_count: number;
  created_at: string;
}

interface DecorItem {
  id: string;
  category: string;
  name: string;
  quantity_formula: string;
  computed_quantity: number;
  cost_tier: 'low' | 'medium' | 'high';
  cost_range_low: number;
  cost_range_high: number;
  sourcing_type: 'rent' | 'diy' | 'buy';
  status: string; // proposed, accepted, rejected
  budget_item_id?: string | null;
  task_id?: string | null;
  reasoning: Record<string, any>;
}

interface ThemeProposal {
  theme_id: string;
  style_profile_id: string;
  theme_name: string;
  palette: string[];
  menu_direction?: string | null;
  playlist_genres: string[];
  dress_code_suggestion?: string | null;
  invitation_design_brief?: string | null;
  status: string;
  decor_items: DecorItem[];
  provider_used: string;
  fallback_warning?: string | null;
  created_at: string;
}

export default function VibeToPlanClient() {
  const params = useParams();
  const eventId = (params?.id as string) || '';

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [textDescription, setTextDescription] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isGeneratingTheme, setIsGeneratingTheme] = useState<boolean>(false);
  const [acceptingItemId, setAcceptingItemId] = useState<string | null>(null);

  const [profiles, setProfiles] = useState<StyleProfile[]>([]);
  const [activeProfile, setActiveProfile] = useState<StyleProfile | null>(null);
  const [activeTheme, setActiveTheme] = useState<ThemeProposal | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch existing profiles on mount
  useEffect(() => {
    if (!eventId || eventId === 'default') return;

    fetch(`${API_BASE_URL}/events/${eventId}/vibe/profiles`)
      .then(res => res.ok ? res.json() : [])
      .then((data: StyleProfile[]) => {
        setProfiles(data);
        if (data.length > 0) {
          setActiveProfile(data[0]);
          loadThemes(data[0].profile_id);
        }
      })
      .catch(err => console.error("Error loading profiles:", err));
  }, [eventId]);

  const loadThemes = (profileId: string) => {
    fetch(`${API_BASE_URL}/events/${eventId}/vibe/${profileId}/themes`)
      .then(res => res.ok ? res.json() : [])
      .then((data: ThemeProposal[]) => {
        if (data && data.length > 0) {
          setActiveTheme(data[0]);
        }
      })
      .catch(err => console.error("Error loading themes:", err));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files).slice(0, 10));
    }
  };

  const handleUploadAndExtract = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFiles.length === 0) {
      setErrorMessage("Please select at least 1 image to extract aesthetic vibe.");
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      formData.append("files", file);
    });
    if (textDescription) {
      formData.append("text_description", textDescription);
    }

    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/vibe/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to upload and extract aesthetic vibe.");
      }

      const newProfile: StyleProfile = await res.json();
      setProfiles(prev => [newProfile, ...prev]);
      setActiveProfile(newProfile);
      setSelectedFiles([]);
      loadThemes(newProfile.profile_id);
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleGenerateTheme = async () => {
    if (!activeProfile) return;
    setIsGeneratingTheme(true);
    setErrorMessage(null);

    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/vibe/${activeProfile.profile_id}/generate-theme`, {
        method: "POST",
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to generate concrete theme.");
      }

      const proposal: ThemeProposal = await res.json();
      setActiveTheme(proposal);
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setIsGeneratingTheme(false);
    }
  };

  const handleAcceptItem = async (itemId: string) => {
    setAcceptingItemId(itemId);
    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/vibe/decor-items/${itemId}/accept`, {
        method: "POST",
      });
      if (res.ok) {
        const updatedItem: DecorItem = await res.json();
        setActiveTheme(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            decor_items: prev.decor_items.map(it => it.id === itemId ? updatedItem : it)
          };
        });
      }
    } catch (err) {
      console.error("Error accepting decor item:", err);
    } finally {
      setAcceptingItemId(null);
    }
  };

  const handleRejectItem = async (itemId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/vibe/decor-items/${itemId}/reject`, {
        method: "POST",
      });
      if (res.ok) {
        const updatedItem: DecorItem = await res.json();
        setActiveTheme(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            decor_items: prev.decor_items.map(it => it.id === itemId ? updatedItem : it)
          };
        });
      }
    } catch (err) {
      console.error("Error rejecting decor item:", err);
    }
  };

  return (
    <div className="min-h-screen pb-20">
      {/* Universal Top Navigation */}
      <Navbar
        badge="Vibe-to-Plan"
        rightAction={
          <Link
            href="/onboarding"
            className="text-xs font-semibold uppercase tracking-wider text-stone-600 dark:text-stone-300 hover:text-stone-900 dark:hover:text-white px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-800 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
          >
            ← Intake Studio
          </Link>
        }
      />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 space-y-8">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-serif font-bold text-stone-900 dark:text-stone-50">
            Vibe-to-Plan Engine
          </h1>
          <p className="text-stone-600 dark:text-stone-300 mt-1 text-sm max-w-2xl leading-relaxed">
            Upload inspiration images or mood notes. Real multimodal AI extracts color palettes, aesthetic tags, and cultural materials, translating visual dreams into concrete itemized decor proposals.
          </p>
        </div>

        {errorMessage && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-sm rounded-2xl shadow-sm flex items-center justify-between">
            <span>⚠️ {errorMessage}</span>
            <button onClick={() => setErrorMessage(null)} className="font-bold ml-2">✕</button>
          </div>
        )}

        {/* Upload Form Section */}
        <div className="glass-card p-6 sm:p-8 rounded-3xl shadow-sm space-y-6">
          <h2 className="text-lg font-serif font-bold text-stone-900 dark:text-stone-50 flex items-center gap-2">
            <span>✨</span> 1. Upload Inspiration Images (Up to 10)
          </h2>

          <form onSubmit={handleUploadAndExtract} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-stone-700 dark:text-stone-300 mb-2">
                Inspiration Photos / Mood Board Stills
              </label>
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleFileChange}
                className="block w-full text-sm text-stone-700 dark:text-stone-300 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-[#8B1E28] file:text-white dark:file:bg-[#F4B41A] dark:file:text-stone-950 hover:file:opacity-90 cursor-pointer border border-stone-200 dark:border-stone-800 rounded-xl p-2 bg-stone-50/50 dark:bg-stone-900/50"
              />
              <p className="text-xs text-stone-500 dark:text-stone-400 mt-1.5">
                Supported formats: JPG, PNG, WEBP. Batched into a single multimodal Gemini call (DEC-023).
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-stone-700 dark:text-stone-300 mb-2">
                Aesthetic Vision & Atmosphere Notes (Optional)
              </label>
              <textarea
                value={textDescription}
                onChange={e => setTextDescription(e.target.value)}
                placeholder="e.g. Royal Rajasthani heritage palace vibe, vibrant marigold yellow, antique brass diyas, raw silk fabrics..."
                rows={3}
                className="w-full text-sm p-3.5 rounded-xl border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-amber-500 transition-colors shadow-sm"
              />
            </div>

            <button
              type="submit"
              disabled={isUploading}
              className="px-6 py-3 bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 text-xs font-bold uppercase tracking-wider rounded-xl shadow-sm disabled:opacity-50 transition-all active:scale-95 flex items-center space-x-2"
            >
              <span>{isUploading ? "Analyzing Aesthetic & Extracting Palette..." : "Extract Vibe & Generate Palette"}</span>
              <span>→</span>
            </button>
          </form>
        </div>

        {/* Extracted Style Profile & Mood Board */}
        {activeProfile && (
          <div className="glass-card p-6 sm:p-8 rounded-3xl shadow-sm space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stone-200 dark:border-stone-800">
              <div>
                <h2 className="text-lg font-serif font-bold text-stone-900 dark:text-stone-50 flex items-center gap-2">
                  <span>🎨</span> 2. Extracted Style Profile
                </h2>
                <p className="text-xs text-stone-500 dark:text-stone-400 mt-0.5">
                  Extracted from {activeProfile.uploaded_image_count} photos via Gemini 2.5 Flash
                </p>
              </div>

              <div className="flex gap-3">
                <a
                  href={`${API_BASE_URL}/events/${eventId}/vibe/${activeProfile.profile_id}/moodboard`}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 border border-stone-300 dark:border-stone-700 rounded-xl text-xs font-semibold hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 transition-colors flex items-center gap-1.5"
                >
                  <span>🖼️</span> Download Collage JPEG
                </a>

                <button
                  onClick={handleGenerateTheme}
                  disabled={isGeneratingTheme}
                  className="px-5 py-2 bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 text-xs font-bold uppercase tracking-wider rounded-xl shadow-sm disabled:opacity-50 transition-all active:scale-95 flex items-center gap-1.5"
                >
                  <span>✨</span>
                  <span>{isGeneratingTheme ? "Composing Theme..." : "Generate Concrete Theme (>=10 items)"}</span>
                </button>
              </div>
            </div>

            {/* Dominant Palette Swatches */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-700 dark:text-stone-300 mb-2.5">
                Harmonized 5-Color Palette
              </h3>
              <div className="grid grid-cols-5 gap-3">
                {activeProfile.extracted_palette.map((hex, idx) => (
                  <div key={idx} className="space-y-1.5 text-center">
                    <div
                      className="h-16 rounded-2xl shadow-sm border border-stone-200 dark:border-stone-700 transition-transform hover:scale-105"
                      style={{ backgroundColor: hex }}
                    />
                    <span className="text-[11px] font-mono font-semibold text-stone-700 dark:text-stone-300 block">{hex}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Aesthetic Tags & Mood Keywords */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div className="p-4 rounded-2xl bg-stone-50 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 block mb-2">
                  Style Descriptors
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activeProfile.style_tags.map((tag, idx) => (
                    <span key={idx} className="text-xs bg-white dark:bg-stone-800 text-stone-800 dark:text-stone-200 px-2.5 py-1 rounded-lg border border-stone-200 dark:border-stone-700 font-medium">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-stone-50 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 block mb-2">
                  Atmospheric Mood Words
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activeProfile.mood_words.map((w, idx) => (
                    <span key={idx} className="text-xs bg-white dark:bg-stone-800 text-stone-800 dark:text-stone-200 px-2.5 py-1 rounded-lg border border-stone-200 dark:border-stone-700 font-medium">
                      ✨ {w}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Concrete Theme Proposal Section */}
        {activeTheme && (
          <div className="glass-card p-6 sm:p-8 rounded-3xl shadow-xl border-2 border-amber-400/60 dark:border-amber-500/60 space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stone-200 dark:border-stone-800">
              <div>
                <div className="flex items-center gap-2.5">
                  <h2 className="text-2xl font-serif font-bold text-stone-900 dark:text-stone-50">
                    {activeTheme.theme_name}
                  </h2>
                  <span className="text-xs bg-emerald-100 dark:bg-emerald-950/80 border border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 px-2.5 py-0.5 rounded-full font-semibold">
                    {activeTheme.decor_items.length} Decor Items Proposed
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-stone-500 dark:text-stone-400 mt-1 font-mono">
                  <span>Provider: <strong>{activeTheme.provider_used}</strong></span>
                  {activeTheme.fallback_warning && (
                    <span className="text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/80 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800 font-sans">
                      ⚠️ {activeTheme.fallback_warning}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Cultural & Creative Direction Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 bg-stone-50/80 dark:bg-stone-950/60 p-5 rounded-2xl border border-stone-200 dark:border-stone-800">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-1">
                  🍽️ Culinary Direction
                </h3>
                <p className="text-xs text-stone-700 dark:text-stone-300 leading-relaxed">
                  {activeTheme.menu_direction || "Traditional regional feast with interactive live stations."}
                </p>
              </div>

              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-1">
                  🎶 Playlist & Music Genres
                </h3>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {activeTheme.playlist_genres.map((g, idx) => (
                    <span key={idx} className="text-xs bg-white dark:bg-stone-800 text-stone-700 dark:text-stone-300 border border-stone-200 dark:border-stone-700 px-2.5 py-0.5 rounded-md font-medium">
                      {g}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-1">
                  👗 Dress Code Recommendation
                </h3>
                <p className="text-xs text-stone-700 dark:text-stone-300 leading-relaxed">
                  {activeTheme.dress_code_suggestion || "Royal traditional attire matching the palette."}
                </p>
              </div>

              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-1">
                  💌 Invitation Design Brief
                </h3>
                <p className="text-xs text-stone-700 dark:text-stone-300 leading-relaxed">
                  {activeTheme.invitation_design_brief || "Handmade paper textures with gold foil accents."}
                </p>
              </div>
            </div>

            {/* Itemized Decor Proposals Table */}
            <div>
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 mb-3">
                <h3 className="text-base font-serif font-bold text-stone-900 dark:text-stone-50">
                  Itemized Decor Elements (Zero LLM Math • Exact City Tiers)
                </h3>
                <span className="text-xs text-stone-500 dark:text-stone-400">
                  Click <strong>Accept</strong> to add individual items into budget & task list.
                </span>
              </div>

              <div className="overflow-x-auto border border-stone-200 dark:border-stone-800 rounded-2xl">
                <table className="w-full text-left text-xs">
                  <thead className="bg-stone-100 dark:bg-stone-800/80 text-stone-600 dark:text-stone-300 uppercase tracking-wider border-b border-stone-200 dark:border-stone-800 font-semibold">
                    <tr>
                      <th className="p-3">Category</th>
                      <th className="p-3">Decor Item</th>
                      <th className="p-3">Formula & Quantity</th>
                      <th className="p-3">Estimated Cost Range</th>
                      <th className="p-3">Sourcing</th>
                      <th className="p-3">Status / Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                    {activeTheme.decor_items.map((item) => (
                      <tr key={item.id} className={item.status === 'accepted' ? 'bg-emerald-50/60 dark:bg-emerald-950/30' : item.status === 'rejected' ? 'bg-stone-50 dark:bg-stone-900/30 opacity-60' : 'hover:bg-amber-50/30 dark:hover:bg-amber-950/20 transition-colors'}>
                        <td className="p-3 font-mono font-medium text-stone-700 dark:text-stone-300">
                          <span className="bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 px-2 py-0.5 rounded text-[11px]">
                            {item.category}
                          </span>
                        </td>
                        <td className="p-3 font-medium text-stone-900 dark:text-stone-100 max-w-xs">
                          <div>{item.name}</div>
                          {item.reasoning?.aesthetic && (
                            <div className="text-[11px] text-stone-500 dark:text-stone-400 italic mt-0.5">
                              {item.reasoning.aesthetic}
                            </div>
                          )}
                        </td>
                        <td className="p-3">
                          <div className="font-semibold text-stone-900 dark:text-stone-100">{item.computed_quantity} units</div>
                          <div className="text-[11px] text-stone-500 dark:text-stone-400 font-mono">({item.quantity_formula})</div>
                        </td>
                        <td className="p-3">
                          <div className="font-bold font-mono text-stone-900 dark:text-stone-100">
                            ₹{item.cost_range_low.toLocaleString('en-IN')} - ₹{item.cost_range_high.toLocaleString('en-IN')}
                          </div>
                          <div className="text-[11px] uppercase font-semibold text-amber-700 dark:text-amber-400">{item.cost_tier} tier</div>
                        </td>
                        <td className="p-3">
                          <span className="uppercase text-[11px] font-mono px-2 py-0.5 bg-stone-100 dark:bg-stone-800 rounded border border-stone-200 dark:border-stone-700 text-stone-700 dark:text-stone-300 font-medium">
                            {item.sourcing_type}
                          </span>
                        </td>
                        <td className="p-3">
                          {item.status === 'accepted' ? (
                            <span className="inline-flex items-center gap-1 text-emerald-800 dark:text-emerald-300 font-bold bg-emerald-100 dark:bg-emerald-950/70 border border-emerald-300 dark:border-emerald-800 px-2.5 py-1 rounded-lg">
                              ✓ Accepted
                            </span>
                          ) : item.status === 'rejected' ? (
                            <span className="text-stone-400 font-medium">Excluded</span>
                          ) : (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleAcceptItem(item.id)}
                                disabled={acceptingItemId === item.id}
                                className="px-3 py-1 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-semibold text-xs shadow-sm disabled:opacity-50 transition-colors active:scale-95"
                              >
                                {acceptingItemId === item.id ? "Adding..." : "Accept"}
                              </button>
                              <button
                                onClick={() => handleRejectItem(item.id)}
                                className="px-2.5 py-1 border border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 rounded-lg text-xs font-medium transition-colors active:scale-95"
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
