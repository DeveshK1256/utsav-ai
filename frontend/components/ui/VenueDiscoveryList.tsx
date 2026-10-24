"use client";

import React, { useState, useEffect } from "react";

export interface CostEstimate {
  is_estimate: boolean;
  limited_data: boolean;
  estimated_cost_display: string;
  min_amount?: number;
  max_amount?: number;
  currency: string;
}

export interface VendorDiscoveryItem {
  id: string;
  business_name: string;
  category: string;
  city: string;
  locality?: string;
  city_tier?: string;
  latitude?: number;
  longitude?: number;
  distance_km?: number;
  rating_tier: string;
  average_rating?: number;
  rating_count: number;
  is_verified_profile: boolean;
  coordinate_precision: string;
  cost_estimate: CostEstimate;
  source_notes?: string;
}

interface VenueDiscoveryListProps {
  initialCity?: string;
  onSelectVenue?: (venue: VendorDiscoveryItem) => void;
  selectedVenueId?: string;
}

export const VenueDiscoveryList: React.FC<VenueDiscoveryListProps> = ({
  initialCity = "Jaipur",
  onSelectVenue,
  selectedVenueId,
}) => {
  const [city, setCity] = useState(initialCity);
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [geoState, setGeoState] = useState<{
    lat?: number;
    lng?: number;
    status: "idle" | "requesting" | "granted" | "denied";
    errorMsg?: string;
  }>({ status: "idle" });

  const [loading, setLoading] = useState(false);
  const [venues, setVenues] = useState<VendorDiscoveryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Request browser geolocation with non-blocking manual fallback
  const requestLocation = () => {
    if (!navigator.geolocation) {
      setGeoState({
        status: "denied",
        errorMsg: "Browser geolocation not supported on this device.",
      });
      return;
    }

    setGeoState({ status: "requesting" });
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGeoState({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          status: "granted",
        });
      },
      (err) => {
        setGeoState({
          status: "denied",
          errorMsg:
            err.code === 1
              ? "Location permission denied. You can select your city manually below."
              : "Unable to retrieve GPS coordinates. Using city fallback.",
        });
      },
      { timeout: 8000 }
    );
  };

  const fetchVenues = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL || "https://utsav-ai-ycg2.onrender.com/api/v1";
      const params = new URLSearchParams();

      if (geoState.status === "granted" && geoState.lat && geoState.lng) {
        params.append("lat", geoState.lat.toString());
        params.append("lng", geoState.lng.toString());
        params.append("radius_km", "30.0");
      } else {
        params.append("city", city);
        params.append("radius_km", "35.0");
      }

      if (categoryFilter !== "all") {
        params.append("category", categoryFilter);
      }

      const res = await fetch(`${apiBase}/discovery/vendors?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Failed to load venues (${res.status})`);
      }
      const data = await res.json();
      setVenues(data.results || []);
    } catch (err: any) {
      setError(err.message || "Failed to fetch venue listings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVenues();
  }, [city, categoryFilter, geoState.lat, geoState.lng]);

  return (
    <div className="bg-white rounded-xl border border-stone-200 shadow-sm p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-stone-100 pb-4">
        <div>
          <h3 className="text-xl font-serif text-stone-900 font-semibold flex items-center gap-2">
            🏛️ Venue Discovery & Logistics
            <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full font-sans font-medium">
              F15-Lite (Honest Directory)
            </span>
          </h3>
          <p className="text-sm text-stone-600 mt-1">
            Real curated venues sorted by proximity. Unreviewed venues are clearly marked as unrated.
          </p>
        </div>

        {/* Location selector / Geolocation */}
        <div className="flex flex-wrap items-center gap-2">
          {geoState.status === "idle" && (
            <button
              onClick={requestLocation}
              className="text-xs px-3 py-1.5 border border-stone-300 rounded-lg text-stone-700 hover:bg-stone-50 transition-colors flex items-center gap-1.5"
            >
              📍 Use My Current Location
            </button>
          )}

          {geoState.status === "requesting" && (
            <span className="text-xs text-stone-500 animate-pulse">
              Requesting GPS...
            </span>
          )}

          {geoState.status === "granted" && (
            <span className="text-xs bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-md border border-emerald-200 flex items-center gap-1">
              ✓ GPS Active ({geoState.lat?.toFixed(3)}, {geoState.lng?.toFixed(3)})
              <button
                onClick={() => setGeoState({ status: "idle" })}
                className="ml-1 text-emerald-900 hover:text-emerald-950 font-bold"
              >
                ×
              </button>
            </span>
          )}

          {/* City Fallback always visible */}
          <div className="flex items-center gap-1.5 text-xs text-stone-600">
            <span>City:</span>
            <select
              value={city}
              onChange={(e) => {
                setCity(e.target.value);
                setGeoState({ status: "idle" });
              }}
              className="px-2.5 py-1 border border-stone-300 rounded-lg bg-stone-50 text-stone-900 text-xs focus:ring-1 focus:ring-amber-500"
            >
              <option value="Jaipur">Jaipur (11 venues)</option>
              <option value="Pune">Pune (8 venues)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Geolocation Notice / Consent Fallback banner */}
      {geoState.errorMsg && (
        <div className="text-xs bg-stone-50 border border-stone-200 text-stone-700 rounded-lg p-2.5 flex items-center justify-between">
          <span>ℹ️ {geoState.errorMsg}</span>
          <button
            onClick={() => setGeoState({ status: "idle" })}
            className="text-stone-500 hover:text-stone-800 font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-stone-500 uppercase tracking-wider mr-1">
          Type:
        </span>
        {[
          { id: "all", label: "All Venues" },
          { id: "palace", label: "Heritage Palaces" },
          { id: "lawn", label: "Lawns & Gardens" },
          { id: "banquet", label: "Banquet Halls" },
          { id: "convention", label: "Convention" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setCategoryFilter(tab.id)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
              categoryFilter === tab.id
                ? "bg-stone-900 border-stone-900 text-white font-medium shadow-sm"
                : "bg-white border-stone-200 text-stone-600 hover:bg-stone-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Honest Transparency Legend (DEC-013 & DEC-014) */}
      <div className="bg-amber-50/60 border border-amber-200/80 rounded-lg p-3 text-xs text-amber-900 space-y-1">
        <div className="font-semibold flex items-center gap-1.5 text-amber-950">
          <span>🔍 Directory Honesty Guarantee:</span>
        </div>
        <p className="text-amber-800">
          • <strong>Ratings:</strong> Every venue starts as <span className="underline">New / Unrated</span>. Utsav never fabricates star ratings or reviews. Ratings only reflect post-event host reviews.
        </p>
        <p className="text-amber-800">
          • <strong>Cost:</strong> Labeled as <em>estimates</em> only with <span className="underline">Limited data</span> until real quote benchmarks accumulate from local vendors.
        </p>
      </div>

      {/* Venues List */}
      {loading ? (
        <div className="py-12 text-center text-stone-500 text-sm animate-pulse space-y-2">
          <div className="text-2xl">⏳</div>
          <p>Scanning nearby venues in {city}...</p>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
          {error}
        </div>
      ) : venues.length === 0 ? (
        <div className="py-10 text-center text-stone-500 text-xs border border-dashed border-stone-200 rounded-lg">
          No venues found matching the selected filter. Try choosing "All Venues".
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {venues.map((venue) => {
            const isSelected = selectedVenueId === venue.id;
            return (
              <div
                key={venue.id}
                onClick={() => onSelectVenue && onSelectVenue(venue)}
                className={`p-4 rounded-xl border text-left transition-all cursor-pointer relative ${
                  isSelected
                    ? "border-amber-600 bg-amber-50/40 shadow-sm"
                    : "border-stone-200 hover:border-amber-300 hover:bg-stone-50/70"
                }`}
              >
                {/* Top line: Name & Proximity */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-medium text-stone-900 text-sm">
                      {venue.business_name}
                    </h4>
                    <p className="text-xs text-stone-500 mt-0.5">
                      📍 {venue.locality ? `${venue.locality}, ` : ""}{venue.city}
                    </p>
                  </div>
                  {venue.distance_km !== null && venue.distance_km !== undefined && (
                    <span className="text-xs font-mono bg-stone-100 text-stone-700 px-2 py-0.5 rounded border border-stone-200 shrink-0">
                      {venue.distance_km} km
                    </span>
                  )}
                </div>

                {/* Badges: Category + Unrated Tier + Limited Data Cost */}
                <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-3 border-t border-stone-100 text-xs">
                  <span className="bg-stone-100 text-stone-700 px-2 py-0.5 rounded text-[11px] capitalize">
                    {venue.category.replace(/_/g, " ")}
                  </span>

                  {/* Rating Tier Badge (Strict DEC-013 honesty) */}
                  <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-[11px] font-medium border border-blue-200 flex items-center gap-1">
                    ⚪ New / Unrated
                  </span>

                  {/* Cost Estimate Badge (Strict DEC-014 honesty) */}
                  <span className="bg-stone-100 text-stone-600 px-2 py-0.5 rounded text-[11px] border border-stone-200">
                    Estimate: {venue.cost_estimate?.estimated_cost_display || "Limited data"}
                  </span>
                </div>

                {/* Sourcing Transparency footnote */}
                {venue.source_notes && (
                  <p className="text-[10px] text-stone-600 mt-2 italic">
                    Source: {venue.source_notes}
                  </p>
                )}

                {isSelected && (
                  <div className="absolute top-3 right-3 text-amber-600 text-sm font-bold">
                    ✓ Selected
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default VenueDiscoveryList;
