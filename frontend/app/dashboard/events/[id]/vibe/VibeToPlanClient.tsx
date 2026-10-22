'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://utsav-ai-ycg2.onrender.com/api/v1';

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
      .then((themes: ThemeProposal[]) => {
        if (themes.length > 0) {
          setActiveTheme(themes[0]);
        } else {
          setActiveTheme(null);
        }
      })
      .catch(err => console.error("Error loading themes:", err));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).slice(0, 10);
      setSelectedFiles(files);
    }
  };

  const handleUploadAndExtract = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFiles.length === 0 && !textDescription.trim()) {
      setErrorMessage("Please select at least 1 image or provide an aesthetic description.");
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);

    const formData = new FormData();
    selectedFiles.forEach(f => formData.append("files", f));
    if (textDescription.trim()) {
      formData.append("text_description", textDescription.trim());
    }

    try {
      const res = await fetch(`${API_BASE_URL}/events/${eventId}/vibe/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to extract aesthetic vibe.");
      }

      const newProfile: StyleProfile = await res.json();
      setProfiles(prev => [newProfile, ...prev]);
      setActiveProfile(newProfile);
      setActiveTheme(null);
      setSelectedFiles([]);
      setTextDescription('');
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
    <div className="min-h-screen bg-[#FDFBF7] text-[#2C2420] p-6 lg:p-12 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between pb-4 border-b border-[#E8DEC8]">
          <div className="flex items-center space-x-3">
            <Link 
              href={`/dashboard/events`}
              className="text-xs uppercase tracking-wider text-[#A67C52] hover:text-[#7A5734] font-semibold"
            >
              ← Back to Events
            </Link>
            <span className="text-stone-300">/</span>
            <span className="text-xs uppercase tracking-wider text-stone-500 font-medium">Vibe-to-Plan</span>
          </div>
          <span className="text-xs bg-[#EAE2D2] text-[#5C452D] px-2.5 py-1 rounded font-mono">
            Milestone M3: Vision & Theme
          </span>
        </div>

        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-serif font-bold text-[#2C2420]">
            Vibe-to-Plan Engine
          </h1>
          <p className="text-stone-600 mt-1 text-sm max-w-2xl">
            Upload inspiration images or mood notes. Real multimodal AI extracts color palettes, aesthetic tags, and cultural materials, translating visual dreams into concrete itemized decor proposals.
          </p>
        </div>

        {errorMessage && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded">
            <strong>Error:</strong> {errorMessage}
          </div>
        )}

        {/* Upload Form Section */}
        <div className="bg-white p-6 rounded-lg border border-[#E8DEC8] shadow-sm space-y-6">
          <h2 className="text-lg font-semibold text-[#3C3028] flex items-center gap-2">
            <span>✨</span> 1. Upload Inspiration Images (Up to 10)
          </h2>

          <form onSubmit={handleUploadAndExtract} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-2">
                Inspiration Photos / Mood Board Stills
              </label>
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleFileChange}
                className="block w-full text-sm text-stone-600 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-[#8B263E] file:text-white hover:file:bg-[#6D1E31] cursor-pointer"
              />
              <p className="text-xs text-stone-400 mt-1">
                Supported formats: JPG, PNG, WEBP. Batched into a single multimodal Gemini call (DEC-023).
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-2">
                Aesthetic Vision & Atmosphere Notes (Optional)
              </label>
              <textarea
                value={textDescription}
                onChange={e => setTextDescription(e.target.value)}
                placeholder="e.g. Royal Rajasthani heritage palace vibe, vibrant marigold yellow, antique brass diyas, raw silk fabrics..."
                rows={3}
                className="w-full text-sm p-3 border border-stone-300 rounded focus:outline-none focus:ring-1 focus:ring-[#8B263E]"
              />
            </div>

            <button
              type="submit"
              disabled={isUploading}
              className="px-6 py-2.5 bg-[#8B263E] hover:bg-[#6D1E31] text-white text-sm font-semibold rounded shadow-sm disabled:opacity-50 transition-colors"
            >
              {isUploading ? "Analyzing Aesthetic & Extracting Palette..." : "Extract Vibe & Generate Palette"}
            </button>
          </form>
        </div>

        {/* Extracted Style Profile & Mood Board */}
        {activeProfile && (
          <div className="bg-white p-6 rounded-lg border border-[#E8DEC8] shadow-sm space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stone-200">
              <div>
                <h2 className="text-lg font-semibold text-[#3C3028] flex items-center gap-2">
                  <span>🎨</span> 2. Extracted Style Profile
                </h2>
                <p className="text-xs text-stone-500 mt-0.5">
                  Profile ID: <span className="font-mono">{activeProfile.profile_id.slice(0, 8)}...</span> • Analyzed {activeProfile.uploaded_image_count} image(s)
                </p>
              </div>

              <div className="flex items-center gap-3">
                <a
                  href={`${API_BASE_URL}/events/${eventId}/vibe/${activeProfile.profile_id}/moodboard`}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 border border-[#8B263E] text-[#8B263E] hover:bg-[#8B263E] hover:text-white text-xs font-semibold rounded transition-colors"
                >
                  Download Mood Board Collage (JPEG)
                </a>

                <button
                  onClick={handleGenerateTheme}
                  disabled={isGeneratingTheme}
                  className="px-5 py-2 bg-[#2D5A27] hover:bg-[#1E3E1A] text-white text-xs font-semibold rounded shadow-sm disabled:opacity-50 transition-colors"
                >
                  {isGeneratingTheme ? "Designing Concrete Theme..." : "Generate Concrete Theme (10+ Items)"}
                </button>
              </div>
            </div>

            {/* Color Palette Display */}
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-stone-500 block mb-2">
                Dominant Extracted Color Palette
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {activeProfile.extracted_palette.map((hex, idx) => (
                  <div key={idx} className="flex flex-col items-center p-3 rounded border border-stone-200 bg-stone-50">
                    <div 
                      className="w-full h-12 rounded shadow-inner mb-2 border border-black/10"
                      style={{ backgroundColor: hex }}
                    />
                    <span className="text-xs font-mono font-bold text-stone-700">{hex.toUpperCase()}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Aesthetic Tags & Mood Words */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-stone-500 block mb-1.5">
                  Style Descriptors
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activeProfile.style_tags.map((tag, i) => (
                    <span key={i} className="text-xs bg-amber-50 text-amber-900 border border-amber-200 px-2.5 py-1 rounded-full font-medium">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-stone-500 block mb-1.5">
                  Atmosphere & Mood Keywords
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activeProfile.mood_words.map((word, i) => (
                    <span key={i} className="text-xs bg-rose-50 text-rose-900 border border-rose-200 px-2.5 py-1 rounded-full font-medium">
                      {word}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Concrete Theme Proposal Section */}
        {activeTheme && (
          <div className="bg-white p-6 rounded-lg border border-[#E8DEC8] shadow-sm space-y-8">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stone-200">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-serif font-bold text-[#2C2420]">
                    {activeTheme.theme_name}
                  </h2>
                  <span className="text-xs bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded-full font-semibold">
                    {activeTheme.decor_items.length} Decor Items Proposed
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-stone-500 mt-1">
                  <span>Provider: <strong className="font-mono">{activeTheme.provider_used}</strong></span>
                  {activeTheme.fallback_warning && (
                    <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                      ⚠️ {activeTheme.fallback_warning}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Cultural & Creative Direction Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-[#FAF7F0] p-5 rounded-lg border border-[#EDE4D0]">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#7A5734] mb-1">
                  🍽️ Culinary Direction
                </h3>
                <p className="text-xs text-stone-700 leading-relaxed">
                  {activeTheme.menu_direction || "Traditional regional feast with interactive live stations."}
                </p>
              </div>

              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#7A5734] mb-1">
                  🎶 Playlist & Music Genres
                </h3>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {activeTheme.playlist_genres.map((g, idx) => (
                    <span key={idx} className="text-xs bg-white text-stone-700 border border-stone-300 px-2 py-0.5 rounded">
                      {g}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#7A5734] mb-1">
                  👗 Dress Code Recommendation
                </h3>
                <p className="text-xs text-stone-700 leading-relaxed">
                  {activeTheme.dress_code_suggestion || "Royal traditional attire matching the palette."}
                </p>
              </div>

              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#7A5734] mb-1">
                  💌 Invitation Design Brief
                </h3>
                <p className="text-xs text-stone-700 leading-relaxed">
                  {activeTheme.invitation_design_brief || "Handmade paper textures with gold foil accents."}
                </p>
              </div>
            </div>

            {/* Itemized Decor Proposals Table */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-md font-semibold text-[#2C2420]">
                  Itemized Decor Elements (Zero LLM Math • Exact City Tiers)
                </h3>
                <span className="text-xs text-stone-500">
                  Click <strong>Accept</strong> to add individual items directly into budget & task list.
                </span>
              </div>

              <div className="overflow-x-auto border border-stone-200 rounded">
                <table className="w-full text-left text-xs">
                  <thead className="bg-stone-100 text-stone-600 uppercase tracking-wider border-b border-stone-200">
                    <tr>
                      <th className="p-3">Category</th>
                      <th className="p-3">Decor Item</th>
                      <th className="p-3">Formula & Quantity</th>
                      <th className="p-3">Estimated Cost Range</th>
                      <th className="p-3">Sourcing</th>
                      <th className="p-3">Status / Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-200">
                    {activeTheme.decor_items.map((item) => (
                      <tr key={item.id} className={item.status === 'accepted' ? 'bg-emerald-50/50' : item.status === 'rejected' ? 'bg-stone-50 opacity-60' : 'hover:bg-amber-50/20'}>
                        <td className="p-3 font-mono font-medium text-stone-700">
                          <span className="bg-stone-200 px-1.5 py-0.5 rounded text-[11px]">
                            {item.category}
                          </span>
                        </td>
                        <td className="p-3 font-medium text-stone-900 max-w-xs">
                          <div>{item.name}</div>
                          {item.reasoning?.aesthetic && (
                            <div className="text-[11px] text-stone-500 italic mt-0.5">
                              {item.reasoning.aesthetic}
                            </div>
                          )}
                        </td>
                        <td className="p-3">
                          <div className="font-semibold text-stone-800">{item.computed_quantity} units</div>
                          <div className="text-[11px] text-stone-400 font-mono">({item.quantity_formula})</div>
                        </td>
                        <td className="p-3">
                          <div className="font-semibold text-stone-800">
                            ₹{item.cost_range_low.toLocaleString('en-IN')} - ₹{item.cost_range_high.toLocaleString('en-IN')}
                          </div>
                          <div className="text-[11px] uppercase text-stone-500">{item.cost_tier} tier</div>
                        </td>
                        <td className="p-3">
                          <span className="uppercase text-[11px] font-mono px-2 py-0.5 bg-stone-100 rounded text-stone-600">
                            {item.sourcing_type}
                          </span>
                        </td>
                        <td className="p-3">
                          {item.status === 'accepted' ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold bg-emerald-100 px-2 py-0.5 rounded">
                              ✓ Accepted
                            </span>
                          ) : item.status === 'rejected' ? (
                            <span className="text-stone-400 font-medium">Excluded</span>
                          ) : (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => handleAcceptItem(item.id)}
                                disabled={acceptingItemId === item.id}
                                className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-800 text-white rounded font-medium disabled:opacity-50"
                              >
                                {acceptingItemId === item.id ? "Adding..." : "Accept"}
                              </button>
                              <button
                                onClick={() => handleRejectItem(item.id)}
                                className="px-2 py-1 border border-stone-300 hover:bg-stone-100 text-stone-600 rounded"
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
