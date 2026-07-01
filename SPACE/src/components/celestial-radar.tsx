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
    <div className="h-full flex flex-col p-4 min-w-0 overflow-hidden">
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
        className="block w-full text-center font-mono text-[10px] tracking-widest text-[var(--fg-dim)] hover:text-[var(--fg)] border border-[var(--border-color)] hover:border-[var(--fg-dim)] px-2 py-1 transition-colors no-underline whitespace-nowrap overflow-hidden"
      >
        [ VIEW DIAGNOSTICS ]
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
  const [leafletLoaded, setLeafletLoaded] = useState(false);
  const [currentZoom, setCurrentZoom] = useState(2);
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
      zoom: 3,
      minZoom: 2,
      maxZoom: 6,
      zoomControl: false,
      attributionControl: false,
      maxBounds: BOUNDS,
      maxBoundsViscosity: 1.0,
    });

    map.on('zoom', () => {
      setCurrentZoom(map.getZoom());
    });

    const starMapUrl = '/assets/skymap.svg';
    L.imageOverlay(starMapUrl, BOUNDS, { 
      opacity: 0.6,
      className: 'sepia-[.2] hue-rotate-[180deg] saturate-[1.5]' // Gives it a cool tactical blue-ish tint
    }).addTo(map);

    map.getContainer().style.background = "#050505";

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
    markersRef.current = {};

    candidates.forEach((cand) => {
      let color = "#4af626";
      if (cand.disposition === "BINARY_STAR_ECLIPSE" || cand.disposition === "BACKGROUND_STELLAR_CONTAMINATION") {
        color = "#e61919";
      }

      const safeId = cand.ticId.replace(/\s+/g, '-');
      const isSelected = cand.ticId === selectedTicId;
      const markerHtml = `
        <div class="radar-marker ${isSelected ? 'selected' : ''}" id="marker-${safeId}" style="--active-color: ${color};">
          <div class="radar-backdrop"></div>
          <div class="radar-ring"></div>
          <div class="radar-x"></div>
          <div class="radar-y"></div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: markerHtml,
        className: "",
        iconSize: [48, 48],
        iconAnchor: [24, 24],
      });

      const marker = L.marker([cand.dec, cand.ra], { icon: customIcon }).addTo(map);
      markersRef.current[cand.ticId] = marker;

      marker.on("click", () => {
        onSelectCandidate(cand.ticId);
      });
    });
  }, [leafletLoaded, candidates]); // Removed onSelectCandidate to prevent re-creation loop

  useEffect(() => {
    if (!leafletLoaded || !mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    
    // Toggle active state classes using the DOM directly for smooth CSS transitions
    candidates.forEach((cand) => {
      const safeId = cand.ticId.replace(/\s+/g, '-');
      const el = document.getElementById(`marker-${safeId}`);
      if (el) {
        if (cand.ticId === selectedTicId) {
          el.classList.add("selected");
        } else {
          el.classList.remove("selected");
        }
      }
    });

    const selectedCand = candidates.find((c) => c.ticId === selectedTicId);
    if (selectedCand) {
      map.panTo([selectedCand.dec, selectedCand.ra], { animate: true, duration: 0.5 });
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

          {/* CUSTOM ZOOM CONTROLS */}
          {leafletLoaded && (
            <div className="absolute bottom-4 right-4 z-[400] flex items-center border border-[var(--border-color)] bg-[var(--panel)]">
              <button
                onClick={() => mapInstanceRef.current?.zoomOut()}
                className="px-3 py-1 font-mono text-[var(--fg-dim)] hover:text-[var(--fg)] hover:bg-[var(--surface)] transition-colors border-r border-[var(--border-color)] leading-none text-lg"
              >
                -
              </button>
              <input
                type="range"
                min="2"
                max="6"
                step="0.1"
                value={currentZoom}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setCurrentZoom(val);
                  mapInstanceRef.current?.setZoom(val);
                }}
                className="brutalist-slider w-24 mx-3"
              />
              <button
                onClick={() => mapInstanceRef.current?.zoomIn()}
                className="px-3 py-1 font-mono text-[var(--fg-dim)] hover:text-[var(--fg)] hover:bg-[var(--surface)] transition-colors border-l border-[var(--border-color)] leading-none text-lg"
              >
                +
              </button>
            </div>
          )}
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
                  className={`font-mono text-[9px] tracking-widest px-2 py-1 border transition-colors ${cand.ticId === selectedTicId
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
      <div className="w-64 border-l border-[var(--border-color)] bg-[var(--panel)] flex-shrink-0 hidden xl:flex xl:flex-col">
        <div className="px-4 py-1 border-b border-[var(--border-color)] bg-[var(--panel)]">
          <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
            [ TELEMETRY ]
          </span>
        </div>
        <StarInfoPanel star={selectedStar} />
      </div>
    </div>
  );
}
