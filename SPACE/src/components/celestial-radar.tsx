"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import Link from "next/link";
import { AstronomicalSignal } from "../../outputs/integration-schema";

interface CelestialRadarProps {
  candidates: AstronomicalSignal[];
  selectedTicId: string;
  onSelectCandidate: (ticId: string) => void;
}

function StarInfoPanel({
  star,
}: {
  star: AstronomicalSignal | null;
}) {
  if (!star) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <span className="font-mono text-[10px] text-[var(--fg-dim)] tracking-widest text-center leading-relaxed">
          SELECT A STAR ON THE MAP
          <br />
          TO VIEW TELEMETRY
        </span>
      </div>
    );
  }

  const dispColor =
    star.disposition === "CONFIRMED_PLANET"
      ? "var(--terminal-green)"
      : star.disposition === "BINARY_STAR_ECLIPSE"
        ? "var(--accent)"
        : star.disposition === "BACKGROUND_STELLAR_CONTAMINATION"
          ? "var(--accent)"
          : "var(--fg-dim)";

  const tierColor =
    star.confidenceTier === "GOLD"
      ? "var(--accent)"
      : star.confidenceTier === "SILVER"
        ? "var(--fg-dim)"
        : "#b45309";

  const dispLabels: Record<string, string> = {
    CONFIRMED_PLANET: "CONFIRMED PLANET",
    BINARY_STAR_ECLIPSE: "ECLIPSING BINARY",
    BACKGROUND_STELLAR_CONTAMINATION: "BACKGROUND BLEND",
    FALSE_ALARM: "FALSE ALARM",
  };

  const ticIdUrl = star.ticId.replace(/\s/g, "");

  return (
    <div className="h-full flex flex-col p-4">
      {/* Header */}
      <div className="border-b border-[var(--border-color)] pb-3 mb-3">
        <h2 className="font-sans font-black text-sm text-[var(--fg)] tracking-tighter">
          {star.name}
        </h2>
        <span className="font-mono text-[9px] text-[var(--fg-dim)] tracking-widest">
          {star.ticId}
        </span>
      </div>

      {/* Disposition + Tier */}
      <div className="flex items-center gap-2 mb-4">
        <span
          className="font-mono text-[9px] tracking-widest font-bold"
          style={{ color: dispColor }}
        >
          {dispLabels[star.disposition] || star.disposition}
        </span>
        <span
          className="font-mono text-[8px] tracking-widest border px-1.5 py-0.5"
          style={{ borderColor: tierColor, color: tierColor }}
        >
          {star.confidenceTier}
        </span>
      </div>

      {/* Params */}
      <div className="space-y-2 flex-1">
        {[
          ["RA", `${star.ra.toFixed(1)}°`],
          ["DEC", `${star.dec.toFixed(1)}°`],
          ["PERIOD", `${star.period.toFixed(4)} d`],
          ["DEPTH", `${star.depth.toFixed(2)} ppt`],
          ["SDE", star.sde.toFixed(2)],
          ["SNR", star.snr.toFixed(2)],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between items-baseline">
            <span className="font-mono text-[8px] text-[var(--fg-dim)] tracking-widest">
              {label}
            </span>
            <span className="font-mono text-[10px] text-[var(--fg)] tabular-nums">
              {value}
            </span>
          </div>
        ))}
      </div>

      {/* Action */}
      <Link
        href={`/star/${ticIdUrl}`}
        className="block w-full text-center font-mono text-[10px] tracking-widest text-[var(--fg-dim)] hover:text-[var(--fg)] border border-[var(--border-color)] hover:border-[var(--fg-dim)] py-2 mt-3 transition-colors no-underline"
      >
        [ VIEW FULL DIAGNOSTICS ]
      </Link>
    </div>
  );
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
  const labelsRef = useRef<{ [ticId: string]: any }>({});
  const [leafletLoaded, setLeafletLoaded] = useState(false);
  const LRef = useRef<any>(null);

  const selectedStar = useMemo(
    () => candidates.find((c) => c.ticId === selectedTicId) || null,
    [candidates, selectedTicId]
  );

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

    map.getContainer().style.background = "#0A0A0A";

    const gridPane = map.createPane("grid");
    gridPane.style.pointerEvents = "none";
    gridPane.style.zIndex = "1";

    for (let ra = 0; ra <= 360; ra += 60) {
      L.polyline(
        [
          [-90, ra],
          [90, ra],
        ],
        { color: "rgba(234,234,234,0.04)", weight: 1, pane: "grid" }
      ).addTo(map);
    }
    for (let dec = -90; dec <= 90; dec += 30) {
      L.polyline(
        [
          [dec, 0],
          [dec, 360],
        ],
        { color: "rgba(234,234,234,0.04)", weight: 1, pane: "grid" }
      ).addTo(map);
    }

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
    Object.values(labelsRef.current).forEach((l) => l.remove());
    markersRef.current = {};
    circlesRef.current = {};
    labelsRef.current = {};

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

      // Outer pulse ring — only visible when selected
      const pulseRing = L.circle([y, x], {
        radius: isSelected ? 18 : 0,
        color: color,
        weight: 1,
        fill: true,
        fillColor: color,
        fillOpacity: isSelected ? 0.12 : 0,
        opacity: isSelected ? 0.6 : 0,
        dashArray: null,
        className: isSelected ? "celestial-pulse" : "",
      }).addTo(map);

      // Selection ring
      const selRing = L.circle([y, x], {
        radius: isSelected ? 8 : 4,
        color: color,
        weight: isSelected ? 1.5 : 0.5,
        fill: false,
        dashArray: isSelected ? null : "4 4",
        opacity: isSelected ? 0.9 : 0.35,
      }).addTo(map);

      // Crosshair marker
      const markerHtml = `
        <div style="position:relative;width:20px;height:20px;display:flex;align-items:center;justify-content:center;cursor:crosshair">
          <div style="position:absolute;width:${isSelected ? 14 : 10}px;height:1px;background:${isSelected ? color : "rgba(234,234,234,0.4)"};transition:all 150ms"></div>
          <div style="position:absolute;height:${isSelected ? 14 : 10}px;width:1px;background:${isSelected ? color : "rgba(234,234,234,0.4)"};transition:all 150ms"></div>
          ${
            isSelected
              ? `<div style="position:absolute;width:5px;height:5px;background:${color};opacity:0.8;transition:all 150ms"></div>`
              : ""
          }
        </div>
      `;

      const customIcon = L.divIcon({
        html: markerHtml,
        className: "",
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      });

      const marker = L.marker([y, x], { icon: customIcon }).addTo(map);
      markersRef.current[cand.ticId] = marker;

      // Selected label (only for selected star)
      let label: any = null;
      if (isSelected) {
        const labelIcon = L.divIcon({
          html: `<div style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:${color};white-space:nowrap;text-shadow:0 0 6px ${color}40;letter-spacing:0.1em;transform:translate(-50%,-140%)">${cand.name}</div>`,
          className: "",
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        });
        label = L.marker([y, x], {
          icon: labelIcon,
          interactive: false,
        }).addTo(map);
        labelsRef.current[cand.ticId] = label;
      }

      marker.on("click", () => {
        onSelectCandidate(cand.ticId);
      });

      circlesRef.current[cand.ticId] = [pulseRing, selRing];
    });
  }, [leafletLoaded, candidates, selectedTicId, onSelectCandidate]);

  useEffect(() => {
    if (!leafletLoaded || !mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    const selectedCand = candidates.find((c) => c.ticId === selectedTicId);
    if (selectedCand) {
      map.panTo([selectedCand.dec, selectedCand.ra], { animate: false });
    }
  }, [selectedTicId, candidates, leafletLoaded]);

  return (
    <div className="h-full flex border border-[var(--border-color)] bg-[var(--surface)]">
      {/* MAP + HEADER column */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
          <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
            [ CELESTIAL COORDINATE MAP ]
          </span>
          <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
            J2000.0 // RA 0–360 / DEC –90–90
          </span>
        </div>

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

        {/* Candidate strip */}
        <div className="border-t border-[var(--border-color)] bg-[var(--panel)] p-2">
          <div className="flex flex-wrap gap-1">
            {candidates.map((cand) => {
              let color = "var(--terminal-green)";
              if (cand.disposition === "BINARY_STAR_ECLIPSE")
                color = "var(--accent)";
              else if (cand.disposition === "BACKGROUND_STELLAR_CONTAMINATION")
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

      {/* INFO PANEL — right side */}
      <div className="w-64 border-l border-[var(--border-color)] bg-[var(--panel)] flex-shrink-0 hidden xl:block">
        <div className="px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
          <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
            [ TELEMETRY ]
          </span>
        </div>
        <StarInfoPanel star={selectedStar} />
      </div>
    </div>
  );
}
