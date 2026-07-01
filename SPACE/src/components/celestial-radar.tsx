"use client";

import { useEffect, useRef, useState } from "react";
import { AstronomicalSignal } from "../../outputs/integration-schema";

interface CelestialRadarProps {
  candidates: AstronomicalSignal[];
  selectedTicId: string;
  onSelectCandidate: (ticId: string) => void;
}

export default function CelestialRadar({
  candidates,
  selectedTicId,
  onSelectCandidate,
}: CelestialRadarProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<{ [ticId: string]: any }>({});
  const circlesRef = useRef<{ [ticId: string]: any[] }>({});
  const [leafletLoaded, setLeafletLoaded] = useState(false);
  const LRef = useRef<any>(null);

  useEffect(() => {
    import("leaflet")
      .then((L) => {
        LRef.current = L.default || L;
        setLeafletLoaded(true);
      })
      .catch((err) => console.error("Failed to load Leaflet", err));
  }, []);

  useEffect(() => {
    if (
      !leafletLoaded ||
      !LRef.current ||
      !mapContainerRef.current ||
      mapInstanceRef.current
    )
      return;
    const L = LRef.current;

    const BOUNDS = L.latLngBounds([[-90, 0], [90, 360]]);

    const map = L.map(mapContainerRef.current, {
      crs: L.CRS.Simple,
      center: [0, 180],
      zoom: 0,
      minZoom: -1,
      maxZoom: 3,
      zoomControl: false,
      attributionControl: false,
      maxBounds: BOUNDS,
      maxBoundsViscosity: 1.0,
    });

    // Dark background — no tile server, pure #0A0A0A canvas
    map.getContainer().style.background = "#0A0A0A";

    // Coordinate grid overlay (RA 0-360, Dec -90 to +90)
    const gridPane = map.createPane("grid");
    gridPane.style.pointerEvents = "none";
    gridPane.style.zIndex = "1";

    // RA grid lines every 60°
    for (let ra = 0; ra <= 360; ra += 60) {
      L.polyline(
        [
          [-90, ra],
          [90, ra],
        ],
        { color: "rgba(234,234,234,0.04)", weight: 1, pane: "grid" }
      ).addTo(map);
    }
    // Dec grid lines every 30°
    for (let dec = -90; dec <= 90; dec += 30) {
      L.polyline(
        [
          [dec, 0],
          [dec, 360],
        ],
        { color: "rgba(234,234,234,0.04)", weight: 1, pane: "grid" }
      ).addTo(map);
    }

    // Crosshair center
    const crosshairIcon = L.divIcon({
      html: '<div style="position:absolute;top:50%;left:50%;width:20px;height:20px;transform:translate(-50%,-50%)"><div style="position:absolute;top:50%;left:0;width:100%;height:1px;background:rgba(234,234,234,0.08)"></div><div style="position:absolute;left:50%;top:0;height:100%;width:1px;background:rgba(234,234,234,0.08)"></div></div>',
      className: "",
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });

    L.marker([0, 180], { icon: crosshairIcon, interactive: false }).addTo(map);

    mapInstanceRef.current = map;

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [leafletLoaded]);

  useEffect(() => {
    if (!leafletLoaded || !LRef.current || !mapInstanceRef.current) return;
    const L = LRef.current;
    const map = mapInstanceRef.current;

    Object.values(markersRef.current).forEach((m) => m.remove());
    Object.values(circlesRef.current).forEach((cList) =>
      cList.forEach((c) => c.remove())
    );
    markersRef.current = {};
    circlesRef.current = {};

    candidates.forEach((cand) => {
      const y = cand.dec;
      const x = cand.ra;

      let color = "#4af626";
      if (cand.disposition === "BINARY_STAR_ECLIPSE") {
        color = "#e61919";
      } else if (cand.disposition === "BACKGROUND_STELLAR_CONTAMINATION") {
        color = "#e61919";
      }

      const isSelected = cand.ticId === selectedTicId;

      const markerHtml = `
        <div style="position:relative;width:24px;height:24px;display:flex;align-items:center;justify-content:center;cursor:crosshair">
          <div style="position:absolute;width:16px;height:1px;background:${isSelected ? color : "rgba(234,234,234,0.3)"};${isSelected ? "transform:scale(1.3)" : ""}"></div>
          <div style="position:absolute;height:16px;width:1px;background:${isSelected ? color : "rgba(234,234,234,0.3)"};${isSelected ? "transform:scale(1.3)" : ""}"></div>
          ${
            isSelected
              ? `<div style="position:absolute;width:6px;height:6px;border:1px solid ${color};background:transparent"></div>`
              : ""
          }
        </div>
      `;

      const customIcon = L.divIcon({
        html: markerHtml,
        className: "",
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const marker = L.marker([y, x], { icon: customIcon }).addTo(map);
      markersRef.current[cand.ticId] = marker;

      marker.on("click", () => {
        onSelectCandidate(cand.ticId);
      });

      const circle1 = L.circle([y, x], {
        radius: isSelected ? 6 : 3,
        color: color,
        weight: isSelected ? 1 : 0.5,
        fill: false,
        dashArray: "4 4",
        opacity: isSelected ? 0.8 : 0.25,
      }).addTo(map);

      circlesRef.current[cand.ticId] = [circle1];
    });
  }, [leafletLoaded, candidates, selectedTicId, onSelectCandidate]);

  useEffect(() => {
    if (!leafletLoaded || !mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    const selectedCand = candidates.find((c) => c.ticId === selectedTicId);
    if (selectedCand) {
      const y = selectedCand.dec;
      const x = selectedCand.ra;
      map.panTo([y, x], { animate: false });
    }
  }, [selectedTicId, candidates, leafletLoaded]);

  return (
    <div className="h-full flex flex-col border border-[var(--border-color)] bg-[var(--surface)]">
      {/* HEADER */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
        <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
          [ CELESTIAL COORDINATE MAP ]
        </span>
        <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
          J2000.0 // TESS S1–3
        </span>
      </div>

      {/* MAP */}
      <div className="relative flex-1 min-h-[400px]">
        {!leafletLoaded && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-[var(--bg)]">
            <span className="font-mono text-xs text-[var(--fg-dim)]">
              INITIALIZING TILE ENGINE...
            </span>
          </div>
        )}
        <div
          ref={mapContainerRef}
          className="w-full h-full"
          style={{ minHeight: "350px" }}
        />
      </div>

      {/* CANDIDATE LIST */}
      <div className="border-t border-[var(--border-color)] bg-[var(--panel)] p-2">
        <div className="flex flex-wrap gap-1">
          {candidates.map((cand) => {
            let color = "var(--terminal-green)";
            if (cand.disposition === "BINARY_STAR_ECLIPSE")
              color = "var(--accent)";
            else if (
              cand.disposition === "BACKGROUND_STELLAR_CONTAMINATION"
            )
              color = "var(--accent)";

            return (
              <button
                key={cand.ticId}
                onClick={() => onSelectCandidate(cand.ticId)}
                className={`font-mono text-[9px] tracking-widest px-2 py-1 border transition-colors ${
                  cand.ticId === selectedTicId
                    ? "border-[var(--fg)] text-[var(--fg)] bg-[var(--surface)]"
                    : "border-[var(--border-color)] text-[var(--fg-dim)] hover:text-[var(--fg)] hover:border-[var(--fg-dim)]"
                }`}
              >
                <span style={{ color }}>+</span> {cand.name}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
