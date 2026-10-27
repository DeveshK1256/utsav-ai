"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { Search, MapPin, Navigation, ListFilter, AlertCircle, Sparkles } from "lucide-react";
import { WakingUpNotice } from "./WakingUpNotice";

// Dynamically import Leaflet map to guarantee zero SSR 'window is not defined' crashes
const LeafletVenueMap = dynamic(
  () => import("./LeafletVenueMap").then((mod) => mod.LeafletVenueMap),
  {
    ssr: false,
    loading: () => (
      <div className="h-[400px] w-full rounded-2xl bg-stone-100 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 flex items-center justify-center text-xs text-stone-500 animate-pulse">
        <span>🗺️ Loading OpenStreetMap canvas...</span>
      </div>
    ),
  }
);

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
  const [searchInput, setSearchInput] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [geoState, setGeoState] = useState<{
    lat?: number;
    lng?: number;
    displayName?: string;
    status: "idle" | "requesting" | "granted" | "denied";
    errorMsg?: string;
  }>({
    status: "idle",
    lat: 26.9124,
    lng: 75.7873,
    displayName: "Jaipur, Rajasthan",
  });

  const [loading, setLoading] = useState(false);
  const [geocoding, setGeocoding] = useState(false);
  const [venues, setVenues] = useState<VendorDiscoveryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const apiBase =
    process.env.NEXT_PUBLIC_API_URL ||
    (typeof window !== "undefined" && window.location.hostname.includes("netlify.app")
      ? "/api/v1"
      : "https://utsav-ai-ycg2.onrender.com/api/v1");

  // 1. Built-in Browser Geolocation (Zero-Cost, No Key)
  const requestLocation = () => {
    if (!navigator.geolocation) {
      setGeoState((prev) => ({
        ...prev,
        status: "denied",
        errorMsg: "Browser geolocation is not supported on this device. Please enter city or pincode below.",
      }));
      return;
    }

    setGeoState((prev) => ({ ...prev, status: "requesting", errorMsg: undefined }));
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setGeoState({
          lat,
          lng,
          status: "granted",
          displayName: `GPS: ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
        });
      },
      (err) => {
        setGeoState((prev) => ({
          ...prev,
          status: "denied",
          errorMsg:
            err.code === 1
              ? "Location permission was denied. Enter your city or 6-digit pincode below."
              : "Unable to retrieve GPS coordinates. Using fallback search.",
        }));
      },
      { timeout: 8000 }
    );
  };

  // 2. Manual City/Pincode Geocoding via OpenStreetMap Nominatim (Free, No Key)
  const handleManualSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = searchInput.trim();
    if (!query) return;

    setGeocoding(true);
    setError(null);

    try {
      // First try backend Nominatim proxy (which caches & honors 1 req/sec policy)
      const res = await fetch(`${apiBase}/discovery/geocode?q=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        setGeoState({
          lat: data.lat,
          lng: data.lng,
          displayName: data.display_name.split(",")[0],
          status: "granted",
        });
        setCity(data.display_name.split(",")[0]);
      } else {
        // Direct Nominatim fallback with compliant User-Agent
        const directRes = await fetch(
          `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
            query
          )}&format=json&countrycodes=in&limit=1`,
          {
            headers: {
              "User-Agent": "UtsavCelebrationApp/1.0 (utsav.celebrations@gmail.com)",
            },
          }
        );
        const directData = await directRes.json();
        if (directData && directData.length > 0) {
          const lat = parseFloat(directData[0].lat);
          const lng = parseFloat(directData[0].lon);
          setGeoState({
            lat,
            lng,
            displayName: directData[0].display_name.split(",")[0],
            status: "granted",
          });
          setCity(directData[0].display_name.split(",")[0]);
        } else {
          setError(`No location found in OpenStreetMap for "${query}". Try another city name or pincode.`);
        }
      }
    } catch (err: any) {
      setError(`Geocoding error: ${err.message || "Failed to resolve coordinates"}`);
    } finally {
      setGeocoding(false);
    }
  };

  // 3. Fetch Real Nearby Venues (Curated Baseline + OpenStreetMap Nationwide)
  const fetchVenues = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();

      if (geoState.lat && geoState.lng) {
        params.append("lat", geoState.lat.toString());
        params.append("lng", geoState.lng.toString());
        params.append("radius_km", "25.0");
      }
      if (city) {
        params.append("city", city);
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

  const centerLat = geoState.lat || 26.9124;
  const centerLng = geoState.lng || 75.7873;

  return (
    <div className="bg-white dark:bg-stone-900 rounded-3xl border border-stone-200 dark:border-stone-800 shadow-xl p-6 sm:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-stone-100 dark:border-stone-800 pb-5">
        <div>
          <h3 className="text-xl sm:text-2xl font-serif text-stone-900 dark:text-stone-50 font-bold flex items-center gap-2">
            🏛️ Nationwide Venue Discovery
            <span className="text-[11px] bg-amber-500/15 border border-amber-500/30 text-amber-900 dark:text-amber-200 px-2.5 py-0.5 rounded-full font-sans font-semibold">
              Free OpenStreetMap
            </span>
          </h3>
          <p className="text-xs sm:text-sm text-stone-600 dark:text-stone-400 mt-1">
            Real venues nationwide powered by OpenStreetMap & Curated Seeds. Zero synthetic entries, zero paid APIs.
          </p>
        </div>

        {/* Quick GPS button */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={requestLocation}
            disabled={geoState.status === "requesting"}
            className="text-xs px-3.5 py-2 border border-stone-300 dark:border-stone-700 rounded-xl text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 font-semibold transition-all flex items-center gap-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
          >
            <Navigation className={`w-3.5 h-3.5 text-blue-600 dark:text-blue-400 ${geoState.status === "requesting" ? "animate-spin" : ""}`} />
            <span>{geoState.status === "requesting" ? "Locating..." : "Use Current Location"}</span>
          </button>
        </div>
      </div>

      {/* Manual City / Pincode Fallback Input Bar */}
      <form onSubmit={handleManualSearch} className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <MapPin className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Enter city or 6-digit pincode (e.g. 560001, Bengaluru, Indore, Jaipur)..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-stone-300 dark:border-stone-700 bg-stone-50 dark:bg-stone-950 text-stone-900 dark:text-stone-100 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-[#8B1E28] dark:focus:ring-amber-400"
          />
        </div>
        <button
          type="submit"
          disabled={geocoding || !searchInput.trim()}
          className="px-5 py-2.5 rounded-xl bg-[#8B1E28] hover:bg-stone-900 text-white dark:bg-[#F4B41A] dark:hover:bg-amber-300 dark:text-stone-950 font-semibold text-xs sm:text-sm transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
        >
          <Search className="w-4 h-4" />
          <span>{geocoding ? "Locating..." : "Search Area"}</span>
        </button>
      </form>

      {/* Active Location Indicator */}
      <div className="flex flex-wrap items-center justify-between text-xs text-stone-600 dark:text-stone-400 bg-stone-100/70 dark:bg-stone-950/70 p-3 rounded-xl border border-stone-200 dark:border-stone-800">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>
            Search Centroid: <strong>{geoState.displayName || city}</strong> ({centerLat.toFixed(3)}, {centerLng.toFixed(3)}) • 25 km radius
          </span>
        </div>
        <span className="text-[11px] text-stone-500 font-mono">
          Found {venues.length} venue{venues.length === 1 ? "" : "s"}
        </span>
      </div>

      {geoState.errorMsg && (
        <div className="text-xs bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300 rounded-xl p-3 flex items-center justify-between">
          <span>ℹ️ {geoState.errorMsg}</span>
          <button
            onClick={() => setGeoState((prev) => ({ ...prev, errorMsg: undefined }))}
            className="text-amber-900 dark:text-amber-100 hover:opacity-75 font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}

      {/* FREE INTERACTIVE LEAFLET MAP (OpenStreetMap Tiles) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-stone-700 dark:text-stone-300">
          <span>Interactive Map (Click pins to inspect & select)</span>
          <span className="text-[11px] text-stone-500">Leaflet.js • OpenStreetMap ODbL</span>
        </div>
        
        <LeafletVenueMap
          venues={venues}
          centerLat={centerLat}
          centerLng={centerLng}
          userLat={geoState.lat}
          userLng={geoState.lng}
          selectedVenueId={selectedVenueId}
          onSelectVenue={onSelectVenue}
        />
      </div>

      {/* Category Filter Pills */}
      <div className="flex flex-wrap items-center gap-2 pt-2">
        <span className="text-xs font-semibold text-stone-500 uppercase tracking-wider mr-1 flex items-center gap-1">
          <ListFilter className="w-3.5 h-3.5" />
          <span>Filter:</span>
        </span>
        {[
          { id: "all", label: "All Real Places" },
          { id: "banquet", label: "Banquet Halls" },
          { id: "garden", label: "Marriage Gardens" },
          { id: "palace", label: "Heritage Palaces" },
          { id: "venue", label: "Convention & Centres" },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setCategoryFilter(tab.id)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
              categoryFilter === tab.id
                ? "bg-[#8B1E28] border-[#8B1E28] text-white dark:bg-[#F4B41A] dark:border-[#F4B41A] dark:text-stone-950 font-semibold shadow-xs"
                : "bg-white dark:bg-stone-900 border-stone-200 dark:border-stone-800 text-stone-700 dark:text-stone-300 hover:bg-stone-50 dark:hover:bg-stone-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Venues Grid / Honest Empty State */}
      {loading ? (
        <div className="py-12 text-center text-stone-900 dark:text-stone-100 font-medium text-xs sm:text-sm space-y-3">
          <div className="text-2xl animate-spin inline-block">⏳</div>
          <p>Scanning OpenStreetMap and curated directory within 25 km of {city}...</p>
          <div className="max-w-md mx-auto">
            <WakingUpNotice isLoading={loading} timeoutMs={3500} />
          </div>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 text-xs rounded-xl border border-red-200 dark:border-red-800">
          {error}
        </div>
      ) : venues.length === 0 ? (
        /* 4. HONEST EMPTY STATE (No Fabrication) */
        <div className="py-12 px-6 text-center border-2 border-dashed border-stone-300 dark:border-stone-800 rounded-2xl bg-stone-50/50 dark:bg-stone-950/50 space-y-3">
          <div className="text-3xl">🏛️</div>
          <h4 className="font-serif text-base font-bold text-stone-900 dark:text-stone-100">
            No places found yet near you
          </h4>
          <p className="text-xs text-stone-600 dark:text-stone-400 max-w-md mx-auto leading-relaxed">
            OpenStreetMap currently has zero banquet halls, marriage gardens, or event venues mapped within 25 km of this location. This is a real data gap in OpenStreetMap for smaller towns, not a system error.
          </p>
          <p className="text-xs text-amber-800 dark:text-amber-300 font-medium">
            Utsav never fabricates synthetic places. You can search another nearby city or skip this step to proceed with &quot;Venue to be confirmed&quot;.
          </p>
        </div>
      ) : (
        <div id="venue-cards-list" className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {venues.map((venue) => {
            const isSelected = selectedVenueId === venue.id;
            const isCuratedSeed = (venue.source_notes || "").includes("pickyourtrail") || (venue.source_notes || "").includes("venuelook");

            return (
              <div
                key={venue.id}
                className={`p-4 rounded-2xl border text-left transition-all relative ${
                  isSelected
                    ? "border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/20 shadow-md ring-2 ring-emerald-500/30"
                    : "border-stone-200 dark:border-stone-800 hover:border-amber-400 dark:hover:border-amber-600 bg-stone-50/40 dark:bg-stone-950/40"
                }`}
              >
                {/* Top line: Name & Proximity */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-medium text-stone-900 dark:text-stone-100 text-sm flex items-center gap-1.5">
                      <span>{venue.business_name}</span>
                      {isCuratedSeed && (
                        <span className="text-[10px] bg-amber-500/20 text-amber-900 dark:text-amber-200 px-1.5 py-0.2 rounded font-mono font-semibold" title="High-confidence curated baseline">
                          Curated
                        </span>
                      )}
                    </h4>
                    <p className="text-xs text-stone-500 dark:text-stone-400 mt-0.5">
                      📍 {venue.locality ? `${venue.locality}, ` : ""}{venue.city}
                    </p>
                  </div>
                  {venue.distance_km !== null && venue.distance_km !== undefined && (
                    <div className="flex flex-col items-end shrink-0">
                      <span className="text-xs font-mono font-bold bg-white dark:bg-stone-900 text-stone-800 dark:text-stone-200 px-2 py-0.5 rounded border border-stone-200 dark:border-stone-800 shadow-2xs">
                        {venue.distance_km.toFixed(1)} km
                      </span>
                      <span className="text-[10px] text-stone-500 mt-0.5">
                        {venue.coordinate_precision === "exact_osm_node" ? "exact OSM pin" : "approx. centroid"}
                      </span>
                    </div>
                  )}
                </div>

                {/* Badges: Category + Unrated Tier + Limited Data Cost */}
                <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-3 border-t border-stone-200/60 dark:border-stone-800/60 text-xs">
                  <span className="bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 px-2 py-0.5 rounded text-[11px] capitalize">
                    {venue.category.replace(/_/g, " ")}
                  </span>

                  <span className="bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded text-[11px] font-medium border border-blue-200 dark:border-blue-800 flex items-center gap-1">
                    ⚪ New / Unrated
                  </span>

                  <span className="bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 px-2 py-0.5 rounded text-[11px]">
                    Estimate: {venue.cost_estimate?.estimated_cost_display || "Limited data"}
                  </span>
                </div>

                {/* Sourcing Footnote */}
                {venue.source_notes && (
                  <p className="text-[10px] text-stone-500 dark:text-stone-400 mt-2 italic line-clamp-1" title={venue.source_notes}>
                    Source: {venue.source_notes}
                  </p>
                )}

                {/* Action button */}
                <div className="mt-3 pt-2 flex items-center justify-between border-t border-stone-100 dark:border-stone-800/40">
                  <span className="text-[11px] text-stone-500">
                    {isSelected ? "Selected for this celebration" : "Click card or map pin to pick"}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onSelectVenue) onSelectVenue(venue);
                    }}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                      isSelected
                        ? "bg-emerald-600 text-white shadow-xs"
                        : "bg-stone-200 dark:bg-stone-800 hover:bg-stone-300 text-stone-800 dark:text-stone-200"
                    }`}
                  >
                    {isSelected ? "✓ Selected" : "Select this"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default VenueDiscoveryList;
