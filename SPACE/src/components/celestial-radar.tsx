'use client';

import { useEffect, useRef, useState } from 'react';
import { AstronomicalSignal } from '../../outputs/integration-schema';
import { Crosshair, Navigation } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

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

  useEffect(() => {
    import('leaflet')
      .then((L) => {
        LRef.current = L.default || L;
        setLeafletLoaded(true);
      })
      .catch((err) => console.error('Failed to load Leaflet', err));
  }, []);

  useEffect(() => {
    if (!leafletLoaded || !LRef.current || !mapContainerRef.current || mapInstanceRef.current) return;
    const L = LRef.current;

    const map = L.map(mapContainerRef.current, {
      center: [-53.0, -80.0],
      zoom: 3,
      minZoom: 2,
      maxZoom: 6,
      zoomControl: true,
      attributionControl: true
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; CartoDB Dark Matter Map'
    }).addTo(map);

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
    Object.values(circlesRef.current).forEach((cList) => cList.forEach((c) => c.remove()));
    markersRef.current = {};
    circlesRef.current = {};

    candidates.forEach((cand) => {
      const lat = cand.dec;
      const lng = cand.ra - 180;

      let colorClass = 'bg-green-500 border-green-500';
      let rawColor = '#10b981';
      if (cand.disposition === 'BINARY_STAR_ECLIPSE') {
        colorClass = 'bg-yellow-500 border-yellow-500';
        rawColor = '#f59e0b';
      } else if (cand.disposition === 'BACKGROUND_STELLAR_CONTAMINATION') {
        colorClass = 'bg-red-500 border-red-500';
        rawColor = '#ef4444';
      }

      const isSelected = cand.ticId === selectedTicId;

      const markerHtml = `
        <div class="relative flex items-center justify-center w-8 h-8 group cursor-pointer">
          <div class="absolute w-8 h-[1px] ${isSelected ? 'bg-primary scale-125' : 'bg-muted-foreground'} transition-all"></div>
          <div class="absolute h-8 w-[1px] ${isSelected ? 'bg-primary scale-125' : 'bg-muted-foreground'} transition-all"></div>
          <div class="absolute w-2.5 h-2.5 rounded-full ${colorClass} transition-transform ${isSelected ? 'scale-150 animate-ping' : ''}"></div>
          <div class="absolute w-2.5 h-2.5 rounded-full ${colorClass} transition-transform ${isSelected ? 'scale-110' : 'group-hover:scale-125'}"></div>
          <div class="absolute top-5 left-5 bg-background/90 border border-border text-[10px] font-sans text-foreground px-2 py-1 rounded-sm whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
            <span class="font-bold">${cand.name}</span><br/>RA: ${cand.ra.toFixed(1)}°
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: markerHtml,
        className: 'celestial-radar-crosshair',
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      const marker = L.marker([lat, lng], { icon: customIcon }).addTo(map);
      markersRef.current[cand.ticId] = marker;

      marker.on('click', () => {
        onSelectCandidate(cand.ticId);
      });

      const circle1 = L.circle([lat, lng], {
        radius: isSelected ? 400000 : 250000,
        color: rawColor,
        weight: isSelected ? 1.5 : 0.8,
        fill: false,
        dashArray: isSelected ? '4,4' : '6,6',
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
    <Card className="h-full flex flex-col border-border bg-card">
      <CardHeader className="border-b border-border bg-muted/20 pb-4">
        <CardTitle className="text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Crosshair className="w-4 h-4" />
            CELESTIAL COORDINATE MAP
          </div>
          <span className="text-xs font-normal text-muted-foreground uppercase">J2000.0</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="p-0 flex-1 relative flex flex-col min-h-[400px]">
        <div className="relative flex-1 w-full celestial-map-container z-10">
          {!leafletLoaded && (
            <div className="absolute inset-0 z-50 flex flex-col items-center justify-center font-mono text-xs text-muted-foreground bg-background">
              <Navigation className="w-6 h-6 animate-spin text-muted-foreground mb-3" />
              Initializing map tiles...
            </div>
          )}
          <div ref={mapContainerRef} className="w-full h-full" style={{ minHeight: '350px' }} />
        </div>
        
        <ScrollArea className="h-28 border-t border-border bg-muted/10 p-2">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 pr-4">
            {candidates.map((cand) => (
              <button
                key={cand.ticId}
                onClick={() => onSelectCandidate(cand.ticId)}
                className={`p-2 text-left rounded-md border transition-all text-xs ${
                  cand.ticId === selectedTicId 
                    ? 'bg-primary text-primary-foreground border-primary' 
                    : 'bg-card hover:bg-muted border-border text-foreground'
                }`}
              >
                <div className="font-semibold truncate">{cand.name}</div>
                <div className={`text-[10px] mt-1 ${cand.ticId === selectedTicId ? 'text-primary-foreground/80' : 'text-muted-foreground'}`}>
                  RA: {cand.ra.toFixed(1)}°
                </div>
              </button>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
