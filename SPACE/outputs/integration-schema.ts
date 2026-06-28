/**
 * AI-enabled Detection of Exoplanets from Noisy Astronomical Light Curves
 * Standard Integration Schema - Pipeline Contract (Hour 0 to Hour 18+)
 * Location: /outputs/integration-schema.ts
 */

export type ConfidenceTier = 'GOLD' | 'SILVER' | 'BRONZE' | 'FALSE_POSITIVE';

export type PipelineDisposition = 
  | 'CONFIRMED_PLANET' 
  | 'BINARY_STAR_ECLIPSE' 
  | 'BACKGROUND_STELLAR_CONTAMINATION' 
  | 'FALSE_ALARM';

export interface AstronomicalSignal {
  ticId: string;
  name: string;
  ra: number;  // Right Ascension (degrees, 0.0 to 360.0)
  dec: number; // Declination (degrees, -90.0 to +90.0)
  period: number; // Orbital Period (days)
  depth: number;  // Transit depth (parts per thousand, ppt)
  sde: number;    // Signal Detection Efficiency
  snr: number;    // Signal to Noise Ratio
  t0: number;     // Transit Epoch (BJD - 2457000)
  duration: number; // Transit duration (hours)
  confidenceTier: ConfidenceTier;
  disposition: PipelineDisposition;
}

export interface LightCurvePoint {
  phase: number; // Phase-folded time (-0.5 to 0.5 or relative days)
  flux: number;  // Normalized flux (approx 1.0)
}

export interface LightCurveData {
  // Raw high-frequency noisy light curve (Layer 1)
  rawPhase: number[];
  rawFlux: number[];
  
  // Cleaned, phase-folded transit model curve (Layer 2)
  modelPhase: number[];
  modelFlux: number[];
}

export interface TriceratopsValidation {
  fpp: number;  // False Positive Probability (0.0 to 1.0)
  nfpp: number; // Non-Transiting False Positive Probability (0.0 to 1.0)
  modes: {
    tp: number;   // True Planet Probability
    eb: number;   // Eclipsing Binary Probability
    heb: number;  // Hierarchical Eclipsing Binary Probability
    bgob: number; // Background Eclipsing Binary Probability
  };
}

export interface SectorValidation {
  sector: number;
  periodMatch: boolean;
  depthConsistency: boolean;
  snr: number;
  status: 'PASS' | 'FAIL';
}

export interface SherlockValidation {
  sectors: number[];
  snrPerSector: number[];
  passFailMatrix: SectorValidation[];
  overallRecoveryStatus: 'RECOVERED' | 'NOT_RECOVERED' | 'INSUFFICIENT_DATA';
}

export interface CandidateEntry {
  signal: AstronomicalSignal;
  lightCurve: LightCurveData;
  validation: {
    triceratops: TriceratopsValidation;
    sherlock: SherlockValidation;
  };
}

export interface PipelinePayload {
  timestamp: string;
  pipelineVersion: string;
  hourElapsed: number; // Hour 0 (static placeholder) vs Hour 18 (live streaming backend outputs)
  candidates: {
    [ticId: string]: CandidateEntry;
  };
}
