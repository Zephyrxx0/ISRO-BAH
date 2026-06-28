'use client';

import { useEffect, useRef, useState } from 'react';
import { AstronomicalSignal } from '../../outputs/integration-schema';
import { Crosshair, Map, Navigation } from 'lucide-react';

interface CelestialRadarProps {
  candidates: AstronomicalSignal[];
  selectedTicId: string;
  onSelectCandidate: (ticId: string) => void;
}

export default function CelestialRadar({
  candidates,
  selectedTicId,
  onSelectCandidate
}: CelestialRadarProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<{ [ticId: string]: any }>({});
  const circlesRef = useRef<{ [ticId: string]: any[] }>({});
  const [leafletLoaded, setLeafletLoaded] = useState(false);
  const LRef = useRef<any>(null);

  // Dynamic import of Leaflet
  useEffect(() => {
    import('leaflet')
      .then((L) => {
        LRef.current = L.default || L;
        setLeafletLoaded(true);
      })
      .catch((err) => console.error('Failed to load Leaflet', err));
  }, []);

  // Initialize Map
  useEffect(() => {
    if (!leafletLoaded || !LRef.current || !mapContainerRef.current || mapInstanceRef.current) return;
    const L = LRef.current;

    // Create Leaflet instance
    // Map centered on average coordinates of candidates
    const map = L.map(mapContainerRef.current, {
      center: [-53.0, -80.0], // Average coordinate region
      zoom: 3,
      minZoom: 2,
      maxZoom: 6,
      zoomControl: true,
      attributionControl: true
    });

    // Add Positron Light map tile layer, which globals.css will invert to dark monochrome grid lines
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; CartoDB Positron Grid Map'
    }).addTo(map);

    mapInstanceRef.current = map;

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [leafletLoaded]);

  // Update Markers & Coordinates
  useEffect(() => {
    if (!leafletLoaded || !LRef.current || !mapInstanceRef.current) return;
    const L = LRef.current;
    const map = mapInstanceRef.current;

    // Clear old markers and circles
    Object.values(markersRef.current).forEach((m) => m.remove());
    Object.values(circlesRef.current).forEach((cList) => cList.forEach((c) => c.remove()));
    markersRef.current = {};
    circlesRef.current = {};

    candidates.forEach((cand) => {
      // Celestial Coordinate Conversion:
      // Dec (-90 to +90) maps directly to Latitude (-90 to 90)
      // RA (0 to 360) maps to Longitude (-180 to 180)
      const lat = cand.dec;
      const lng = cand.ra - 180;

      // Color mapping
      let colorClass = 'bg-signal-green border-signal-green';
      let rawColor = '#22C55E';
      if (cand.disposition === 'BINARY_STAR_ECLIPSE') {
        colorClass = 'bg-warning-amber border-warning-amber';
        rawColor = '#F59E0B';
      } else if (cand.disposition === 'BACKGROUND_STELLAR_CONTAMINATION') {
        colorClass = 'bg-blending-red border-blending-red';
        rawColor = '#EF4444';
      }

      // Check if selected
      const isSelected = cand.ticId === selectedTicId;

      // Custom DivIcon representing a brutalist laser crosshair intercept
      const markerHtml = `
        <div class="relative flex items-center justify-center w-10 h-10 group">
          <!-- Crosshair axes -->
          <div class="absolute w-10 h-[1px] ${isSelected ? 'bg-zinc-950 scale-125' : 'bg-zinc-500'} transition-all duration-200"></div>
          <div class="absolute h-10 w-[1px] ${isSelected ? 'bg-zinc-950 scale-125' : 'bg-zinc-500'} transition-all duration-200"></div>
          <!-- Target center box -->
          <div class="absolute w-2 h-2 ${colorClass} border border-zinc-950 transition-transform ${isSelected ? 'scale-150 animate-ping' : ''}"></div>
          <div class="absolute w-2 h-2 ${colorClass} border border-zinc-950 transition-transform ${isSelected ? 'scale-110' : 'group-hover:scale-125'}"></div>
          <!-- ID Label tooltip -->
          <div class="absolute top-6 left-6 bg-zinc-950 border border-zinc-50 text-[8px] font-mono text-zinc-50 px-1 py-0.5 whitespace-nowrap opacity-75 group-hover:opacity-100 transition-opacity">
            ${cand.name} RA:${cand.ra.toFixed(1)}°
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: markerHtml,
        className: 'celestial-radar-crosshair',
        iconSize: [40, 40],
        iconAnchor: [20, 20]
      });

      // Add marker to map
      const marker = L.marker([lat, lng], { icon: customIcon }).addTo(map);
      markersRef.current[cand.ticId] = marker;

      // Click callback
      marker.on('click', () => {
        onSelectCandidate(cand.ticId);
      });

      // Add radar range rings (concentric dashed circles)
      const circle1 = L.circle([lat, lng], {
        radius: isSelected ? 400000 : 250000,
        color: rawColor,
        weight: isSelected ? 1.5 : 0.8,
        fill: false,
        dashArray: isSelected ? '3,3' : '5,5',
        opacity: isSelected ? 0.9 : 0.4
      }).addTo(map);

      const circle2 = L.circle([lat, lng], {
        radius: isSelected ? 800000 : 500000,
        color: rawColor,
        weight: 0.5,
        fill: false,
        dashArray: '8,8',
        opacity: isSelected ? 0.6 : 0.2
      }).addTo(map);

      circlesRef.current[cand.ticId] = [circle1, circle2];
    });
  }, [leafletLoaded, candidates, selectedTicId, onSelectCandidate]);

  // Pan to selected candidate coordinate
  useEffect(() => {
    if (!leafletLoaded || !mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    const selectedCand = candidates.find((c) => c.ticId === selectedTicId);
    if (selectedCand) {
      const lat = selectedCand.dec;
      const lng = selectedCand.ra - 180;
      map.panTo([lat, lng], { animate: true, duration: 1.0 });
    }
  }, [selectedTicId, candidates, leafletLoaded]);

  return (
    <div className="border border-border-brutal bg-[#FAFAFA] flex flex-col h-full">
      {/* Header telemetry deck */}
      <div className="p-4 border-b border-border-brutal bg-[#FAFAFA] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Crosshair className="w-4 h-4 text-zinc-950" />
          <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-900">
            CELESTIAL COORDINATE SPATIAL INTERCEPT [2D PLOT]
          </span>
        </div>
        <span className="text-[9px] text-raw-zinc uppercase font-mono">
          RA/DEC INTERPOLATION MATRIX
        </span>
      </div>

      {/* Map Content */}
      <div className="relative flex-1 min-h-[350px] w-full celestial-map-container">
        {!leafletLoaded && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center font-mono text-[10px] text-raw-zinc bg-zinc-900">
            <Navigation className="w-6 h-6 animate-spin text-zinc-500 mb-2" />
            SYNCHRONIZING CELESTIAL COORDINATE SYSTEM [J2000.0]...
          </div>
        )}
        <div ref={mapContainerRef} className="w-full h-full z-10" />
      </div>

      {/* Radar Coordinate Telemetry Legend */}
      <div className="p-3 bg-zinc-50 border-t border-border-brutal text-[9px] font-mono grid grid-cols-2 lg:grid-cols-5 gap-2 divide-x divide-zinc-200">
        {candidates.map((cand) => (
          <button
            key={cand.ticId}
            onClick={() => onSelectCandidate(cand.ticId)}
            className={`px-2 py-1 text-left flex flex-col transition-all cursor-pointer ${
              cand.ticId === selectedTicId 
                ? 'bg-zinc-900 text-zinc-50 border border-zinc-950' 
                : 'hover:bg-zinc-150 text-zinc-700'
            }`}
          >
            <span className="font-bold truncate text-[8px]">{cand.name}</span>
            <span className="text-[7px] text-raw-zinc truncate mt-0.5">
              RA: {cand.ra.toFixed(2)}° | DEC: {cand.dec.toFixed(2)}°
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
