"use client";

import React, { useEffect, useRef } from "react";
import { VendorDiscoveryItem } from "./VenueDiscoveryList";

interface LeafletVenueMapProps {
  venues: VendorDiscoveryItem[];
  centerLat: number;
  centerLng: number;
  userLat?: number;
  userLng?: number;
  selectedVenueId?: string;
  onSelectVenue?: (venue: VendorDiscoveryItem) => void;
  className?: string;
}

export function LeafletVenueMap({
  venues,
  centerLat,
  centerLng,
  userLat,
  userLng,
  selectedVenueId,
  onSelectVenue,
  className = "h-[420px] w-full rounded-2xl overflow-hidden border border-stone-200 dark:border-stone-800 shadow-md relative",
}: LeafletVenueMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<{ remove: () => void } | null>(null);
  const markersLayerRef = useRef<{ clearLayers: () => void } | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !mapContainerRef.current) return;

    let isMounted = true;

    // Dynamically import Leaflet to protect Next.js SSR
    import("leaflet").then((L) => {
      if (!isMounted || !mapContainerRef.current) return;

      // Clean up previous instance if any
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }

      // Initialize map with OpenStreetMap tiles (100% Free, No Key, Zero Billing)
      const map = L.map(mapContainerRef.current, {
        center: [centerLat, centerLng],
        zoom: 12,
        scrollWheelZoom: false,
        attributionControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map);

      const markersLayer = L.layerGroup().addTo(map);
      markersLayerRef.current = markersLayer;
      mapInstanceRef.current = map;

      // Render User GPS/Query location pin if provided
      if (userLat && userLng) {
        const userIcon = L.divIcon({
          className: "user-pin-marker",
          html: `
            <div class="relative flex items-center justify-center w-8 h-8">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-5 w-5 bg-blue-600 border-2 border-white shadow-md text-white text-[10px] items-center justify-center font-bold">📍</span>
            </div>
          `,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        });

        L.marker([userLat, userLng], { icon: userIcon })
          .addTo(markersLayer)
          .bindPopup(
            '<strong>Your Search Location</strong><br/><span style="font-size:11px;color:#666;">Distances calculated from here</span>',
          );
      }

      // Render venue pins
      venues.forEach((v) => {
        if (!v.latitude || !v.longitude) return;

        const isSelected = v.id === selectedVenueId;
        const isCuratedSeed =
          (v.source_notes || "").includes("pickyourtrail") ||
          (v.source_notes || "").includes("venuelook");

        const pinBg = isSelected
          ? "#10B981" // Emerald for selected
          : isCuratedSeed
            ? "#D97706" // Warm Amber for Curated Seed
            : "#8B1E28"; // Kumkum Crimson for OSM record

        const iconHtml = `
          <div style="
            background-color: ${pinBg};
            color: white;
            width: ${isSelected ? "36px" : "30px"};
            height: ${isSelected ? "36px" : "30px"};
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg);
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: all 0.2s ease;
          ">
            <span style="transform: rotate(45deg); font-size: ${isSelected ? "14px" : "12px"};">
              ${isCuratedSeed ? "🪔" : "🏛️"}
            </span>
          </div>
        `;

        const markerIcon = L.divIcon({
          className: `venue-marker-${v.id}`,
          html: iconHtml,
          iconSize: [isSelected ? 36 : 30, isSelected ? 36 : 30],
          iconAnchor: [isSelected ? 18 : 15, isSelected ? 36 : 30],
        });

        const marker = L.marker([v.latitude, v.longitude], {
          icon: markerIcon,
          keyboard: true,
          title: `${v.business_name} (${v.locality || v.city}) - Press Enter to select`,
          alt: `${v.business_name} marker`,
        }).addTo(markersLayer);

        // Interactive Popup
        const distBadge =
          v.distance_km !== undefined
            ? `<strong>${v.distance_km.toFixed(1)} km</strong> away`
            : "Distance approximate";
        const sourceBadge = isCuratedSeed
          ? "🌟 Curated Seed Directory"
          : "🗺️ OpenStreetMap Record";

        const popupContent = document.createElement("div");
        popupContent.className = "venue-popup p-1 text-xs space-y-1.5";
        popupContent.innerHTML = `
          <div style="font-family: serif; font-size: 14px; font-weight: bold; color: #1C1917; line-height: 1.2;">
            ${v.business_name}
          </div>
          <div style="font-size: 11px; color: #57534E;">
            📍 ${v.locality || v.city} • <span style="color: #8B1E28; font-weight: 600;">${distBadge}</span>
          </div>
          <div style="font-size: 11px; color: #78716C; margin-top: 2px;">
            💰 Cost: <span style="font-weight: 600; color: #44403C;">Estimate (${v.cost_estimate?.estimated_cost_display || "Limited data"})</span>
          </div>
          <div style="display: inline-block; font-size: 10px; background: #F5F5F4; padding: 2px 6px; border-radius: 4px; color: #78716C; margin-top: 3px;">
            ${sourceBadge}
          </div>
          <div style="margin-top: 6px;">
            <button id="select-pin-btn-${v.id}" style="
              width: 100%;
              padding: 5px 10px;
              background-color: #8B1E28;
              color: white;
              font-weight: 600;
              border-radius: 6px;
              border: none;
              cursor: pointer;
              font-size: 11px;
            ">
              ${isSelected ? "✓ Selected Venue" : "Select This Venue"}
            </button>
          </div>
        `;

        marker.bindPopup(popupContent);

        // Keyboard activation on Enter / Space
        marker.on("keypress", (e: { originalEvent?: KeyboardEvent }) => {
          if (
            e.originalEvent &&
            (e.originalEvent.key === "Enter" || e.originalEvent.key === " ")
          ) {
            if (onSelectVenue) {
              onSelectVenue(v);
            }
            marker.openPopup();
          }
        });

        // Bind button click inside popup
        marker.on("popupopen", () => {
          const btn = document.getElementById(`select-pin-btn-${v.id}`);
          if (btn && onSelectVenue) {
            btn.onclick = () => {
              onSelectVenue(v);
              marker.closePopup();
            };
          }
        });

        // Also trigger on marker click
        marker.on("click", () => {
          if (onSelectVenue && !isSelected) {
            onSelectVenue(v);
          }
        });
      });

      // Fit bounds if venues exist
      if (venues.length > 0) {
        const boundsCoords: [number, number][] = venues
          .filter((v) => v.latitude && v.longitude)
          .map((v) => [v.latitude!, v.longitude!]);

        if (userLat && userLng) {
          boundsCoords.push([userLat, userLng]);
        }

        if (boundsCoords.length > 1) {
          map.fitBounds(boundsCoords, { padding: [40, 40], maxZoom: 14 });
        }
      }

      // Ensure controls and container have accessible labels and non-trapping tab navigation
      const container = mapContainerRef.current;
      if (container) {
        container.setAttribute("role", "region");
        container.setAttribute(
          "aria-label",
          "Celebration Venues Interactive Map",
        );

        // Ensure zoom controls have accessible aria-labels
        setTimeout(() => {
          const zoomIn = container.querySelector(
            ".leaflet-control-zoom-in",
          ) as HTMLElement | null;
          const zoomOut = container.querySelector(
            ".leaflet-control-zoom-out",
          ) as HTMLElement | null;
          if (zoomIn) {
            zoomIn.setAttribute("aria-label", "Zoom map in");
            zoomIn.setAttribute("title", "Zoom map in");
          }
          if (zoomOut) {
            zoomOut.setAttribute("aria-label", "Zoom map out");
            zoomOut.setAttribute("title", "Zoom map out");
          }
        }, 100);
      }
    });

    return () => {
      isMounted = false;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [
    venues,
    centerLat,
    centerLng,
    userLat,
    userLng,
    selectedVenueId,
    onSelectVenue,
  ]);

  return (
    <div className={className}>
      {/* Skip map controls accessible bypass link to prevent keyboard focus trap */}
      <a
        href="#venue-cards-list"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[1000] focus:px-3 focus:py-1.5 focus:bg-amber-800 focus:text-white focus:text-xs focus:font-semibold focus:rounded-lg focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-amber-400"
      >
        Skip map controls to venue list
      </a>

      <div
        ref={mapContainerRef}
        className="w-full h-full min-h-[400px]"
        tabIndex={0}
        role="region"
        aria-label="Interactive venue map. Use Tab to navigate venue markers or skip to venue list."
      />

      {/* Map Legend Overlay */}
      <div className="absolute bottom-3 left-3 z-[400] bg-white/90 dark:bg-stone-900/90 backdrop-blur-xs p-2 rounded-xl border border-stone-200 dark:border-stone-800 text-[10px] space-y-1 shadow-md pointer-events-none">
        <div className="flex items-center gap-1.5 font-semibold text-stone-800 dark:text-stone-200">
          <span className="w-2.5 h-2.5 rounded-full bg-[#D97706] inline-block"></span>
          <span>Curated Seed (Jaipur/Pune)</span>
        </div>
        <div className="flex items-center gap-1.5 font-semibold text-stone-800 dark:text-stone-200">
          <span className="w-2.5 h-2.5 rounded-full bg-[#8B1E28] inline-block"></span>
          <span>OpenStreetMap (Real Venue)</span>
        </div>
        <div className="flex items-center gap-1.5 text-stone-500 dark:text-stone-400">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
          <span>Selected Pick</span>
        </div>
      </div>
    </div>
  );
}
