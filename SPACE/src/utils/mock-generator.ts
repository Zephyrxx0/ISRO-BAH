import { PipelinePayload, CandidateEntry, ConfidenceTier, PipelineDisposition } from '../../outputs/integration-schema';

// Helper to generate Gaussian random noise
function randomNormal(mean = 0, std = 1) {
  const u = 1 - Math.random();
  const v = Math.random();
  const z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
  return mean + z * std;
}

// Generate light curve points
function generateLightCurve(
  periodDays: number,
  depthPpt: number,
  durationHours: number,
  noiseSigma: number
): { rawPhase: number[]; rawFlux: number[]; modelPhase: number[]; modelFlux: number[] } {
  const rawPhase: number[] = [];
  const rawFlux: number[] = [];
  const modelPhase: number[] = [];
  const modelFlux: number[] = [];

  const transitDurationPhase = durationHours / (periodDays * 24);
  const ingressEgressPhase = transitDurationPhase * 0.15; // 15% duration for ingress/egress slope

  // Generate 600 raw points centered on transit (from phase -0.06 to +0.06)
  const steps = 600;
  for (let i = 0; i < steps; i++) {
    const phase = -0.06 + (i / steps) * 0.12;
    
    // Calculate model flux (trapezoidal transit model)
    const absPhase = Math.abs(phase);
    let modelValue = 1.0;
    
    const halfWidth = transitDurationPhase / 2;
    const flatHalfWidth = halfWidth - ingressEgressPhase;

    if (absPhase <= flatHalfWidth) {
      modelValue = 1.0 - (depthPpt / 1000);
    } else if (absPhase > flatHalfWidth && absPhase <= halfWidth) {
      // Ingress / Egress linear interpolation
      const fraction = (halfWidth - absPhase) / ingressEgressPhase;
      modelValue = 1.0 - (fraction * (depthPpt / 1000));
    } else {
      modelValue = 1.0;
    }

    rawPhase.push(phase);
    // Raw flux is model value + random Gaussian noise
    rawFlux.push(modelValue + randomNormal(0, noiseSigma));
  }

  // Generate 200 model points for a super smooth overlay curve
  const modelSteps = 200;
  for (let i = 0; i < modelSteps; i++) {
    const phase = -0.06 + (i / modelSteps) * 0.12;
    const absPhase = Math.abs(phase);
    let modelValue = 1.0;
    
    const halfWidth = transitDurationPhase / 2;
    const flatHalfWidth = halfWidth - ingressEgressPhase;

    if (absPhase <= flatHalfWidth) {
      modelValue = 1.0 - (depthPpt / 1000);
    } else if (absPhase > flatHalfWidth && absPhase <= halfWidth) {
      const fraction = (halfWidth - absPhase) / ingressEgressPhase;
      modelValue = 1.0 - (fraction * (depthPpt / 1000));
    } else {
      modelValue = 1.0;
    }

    modelPhase.push(phase);
    modelFlux.push(modelValue);
  }

  return { rawPhase, rawFlux, modelPhase, modelFlux };
}

export function generateMockPayload(hour: number): PipelinePayload {
  const isH18 = hour >= 18;

  const candidates: { [ticId: string]: CandidateEntry } = {
    "TIC 22522502": {
      signal: {
        ticId: "TIC 22522502",
        name: "WASP-121b",
        ra: 106.6,
        dec: -39.1,
        period: 1.274925,
        depth: 15.6, // ppt
        sde: isH18 ? 34.2 : 28.1,
        snr: isH18 ? 45.1 : 39.8,
        t0: 1354.2312,
        duration: 2.9, // hours
        confidenceTier: "GOLD" as ConfidenceTier,
        disposition: "CONFIRMED_PLANET" as PipelineDisposition
      },
      lightCurve: generateLightCurve(1.274925, 15.6, 2.9, isH18 ? 0.0012 : 0.0035),
      validation: {
        triceratops: {
          fpp: isH18 ? 0.00012 : 0.045,
          nfpp: isH18 ? 0.00002 : 0.012,
          modes: {
            tp: isH18 ? 0.99988 : 0.943,
            eb: isH18 ? 0.00008 : 0.035,
            heb: isH18 ? 0.00003 : 0.015,
            bgob: isH18 ? 0.00001 : 0.007
          }
        },
        sherlock: {
          sectors: [1, 2, 6, 7],
          snrPerSector: isH18 ? [22.1, 24.5, 23.9, 25.1] : [20.1, 19.5, 0.0, 0.0],
          passFailMatrix: [
            { sector: 1, periodMatch: true, depthConsistency: true, snr: 22.1, status: 'PASS' },
            { sector: 2, periodMatch: true, depthConsistency: true, snr: 24.5, status: 'PASS' },
            { sector: 6, periodMatch: true, depthConsistency: true, snr: 23.9, status: isH18 ? 'PASS' : 'FAIL' },
            { sector: 7, periodMatch: true, depthConsistency: true, snr: 25.1, status: isH18 ? 'PASS' : 'FAIL' }
          ],
          overallRecoveryStatus: isH18 ? 'RECOVERED' : 'INSUFFICIENT_DATA'
        }
      }
    },
    "TIC 259377017": {
      signal: {
        ticId: "TIC 259377017",
        name: "TOI-270b",
        ra: 66.1,
        dec: -51.8,
        period: 3.36008,
        depth: 2.1,
        sde: isH18 ? 18.7 : 14.2,
        snr: isH18 ? 22.4 : 17.6,
        t0: 1412.5567,
        duration: 1.8,
        confidenceTier: "GOLD" as ConfidenceTier,
        disposition: "CONFIRMED_PLANET" as PipelineDisposition
      },
      lightCurve: generateLightCurve(3.36008, 2.1, 1.8, isH18 ? 0.00035 : 0.00095),
      validation: {
        triceratops: {
          fpp: isH18 ? 0.0024 : 0.125,
          nfpp: isH18 ? 0.0008 : 0.045,
          modes: {
            tp: isH18 ? 0.9968 : 0.830,
            eb: isH18 ? 0.0018 : 0.095,
            heb: isH18 ? 0.0010 : 0.052,
            bgob: isH18 ? 0.0004 : 0.023
          }
        },
        sherlock: {
          sectors: [3, 4, 5],
          snrPerSector: isH18 ? [12.4, 13.8, 14.2] : [11.2, 0.0, 0.0],
          passFailMatrix: [
            { sector: 3, periodMatch: true, depthConsistency: true, snr: 12.4, status: 'PASS' },
            { sector: 4, periodMatch: true, depthConsistency: true, snr: 13.8, status: isH18 ? 'PASS' : 'FAIL' },
            { sector: 5, periodMatch: true, depthConsistency: true, snr: 14.2, status: isH18 ? 'PASS' : 'FAIL' }
          ],
          overallRecoveryStatus: isH18 ? 'RECOVERED' : 'INSUFFICIENT_DATA'
        }
      }
    },
    "TIC 307210830": {
      signal: {
        ticId: "TIC 307210830",
        name: "L98-59b",
        ra: 120.3,
        dec: -68.3,
        period: 2.2532,
        depth: 0.75, // ultra shallow transit
        sde: isH18 ? 15.1 : 10.4,
        snr: isH18 ? 14.8 : 9.5,
        t0: 1321.4112,
        duration: 1.2,
        confidenceTier: isH18 ? "GOLD" : ("BRONZE" as ConfidenceTier),
        disposition: "CONFIRMED_PLANET" as PipelineDisposition
      },
      lightCurve: generateLightCurve(2.2532, 0.75, 1.2, isH18 ? 0.00015 : 0.00045),
      validation: {
        triceratops: {
          fpp: isH18 ? 0.0085 : 0.285,
          nfpp: isH18 ? 0.0022 : 0.089,
          modes: {
            tp: isH18 ? 0.9893 : 0.626,
            eb: isH18 ? 0.0062 : 0.185,
            heb: isH18 ? 0.0031 : 0.112,
            bgob: isH18 ? 0.0014 : 0.077
          }
        },
        sherlock: {
          sectors: [11, 12, 13],
          snrPerSector: isH18 ? [8.5, 9.2, 9.8] : [7.2, 0.0, 0.0],
          passFailMatrix: [
            { sector: 11, periodMatch: true, depthConsistency: true, snr: 8.5, status: 'PASS' },
            { sector: 12, periodMatch: true, depthConsistency: true, snr: 9.2, status: isH18 ? 'PASS' : 'FAIL' },
            { sector: 13, periodMatch: true, depthConsistency: true, snr: 9.8, status: isH18 ? 'PASS' : 'FAIL' }
          ],
          overallRecoveryStatus: isH18 ? 'RECOVERED' : 'INSUFFICIENT_DATA'
        }
      }
    },
    "TIC 35516889": {
      signal: {
        ticId: "TIC 35516889",
        name: "WASP-19b (Blend)",
        ra: 148.4,
        dec: -45.6,
        period: 0.78884,
        depth: 20.3, // Deep but suspicious V-shape
        sde: isH18 ? 28.5 : 22.4,
        snr: isH18 ? 32.1 : 27.8,
        t0: 1289.4452,
        duration: 1.5,
        confidenceTier: "FALSE_POSITIVE" as ConfidenceTier,
        disposition: "BINARY_STAR_ECLIPSE" as PipelineDisposition // Warning Amber!
      },
      lightCurve: generateLightCurve(0.78884, 20.3, 1.5, isH18 ? 0.0022 : 0.0055),
      validation: {
        triceratops: {
          fpp: isH18 ? 0.985 : 0.840,
          nfpp: isH18 ? 0.005 : 0.015,
          modes: {
            tp: isH18 ? 0.010 : 0.145,
            eb: isH18 ? 0.925 : 0.720,
            heb: isH18 ? 0.055 : 0.105,
            bgob: isH18 ? 0.010 : 0.030
          }
        },
        sherlock: {
          sectors: [9, 10],
          snrPerSector: [18.2, 19.5],
          passFailMatrix: [
            { sector: 9, periodMatch: true, depthConsistency: false, snr: 18.2, status: 'FAIL' }, // V-shape depth mismatch
            { sector: 10, periodMatch: true, depthConsistency: false, snr: 19.5, status: 'FAIL' }
          ],
          overallRecoveryStatus: 'NOT_RECOVERED'
        }
      }
    },
    "TIC 150428135": {
      signal: {
        ticId: "TIC 150428135",
        name: "TOI-700d (Contam.)",
        ra: 98.4,
        dec: -63.0,
        period: 37.426,
        depth: 0.55, // Earth-sized but background blend
        sde: isH18 ? 12.3 : 9.8,
        snr: isH18 ? 9.8 : 8.1,
        t0: 1654.1234,
        duration: 3.5,
        confidenceTier: isH18 ? "FALSE_POSITIVE" : ("BRONZE" as ConfidenceTier),
        disposition: "BACKGROUND_STELLAR_CONTAMINATION" as PipelineDisposition // Blending Red!
      },
      lightCurve: generateLightCurve(37.426, 0.55, 3.5, isH18 ? 0.00018 : 0.00052),
      validation: {
        triceratops: {
          fpp: isH18 ? 0.765 : 0.420,
          nfpp: isH18 ? 0.720 : 0.380, // High non-transiting false positive (background star)
          modes: {
            tp: isH18 ? 0.180 : 0.490,
            eb: isH18 ? 0.055 : 0.090,
            heb: isH18 ? 0.045 : 0.080,
            bgob: isH18 ? 0.720 : 0.340 // Blended background eclipsing binary mode dominates
          }
        },
        sherlock: {
          sectors: [14, 15, 26],
          snrPerSector: isH18 ? [6.2, 5.8, 6.8] : [5.1, 0.0, 0.0],
          passFailMatrix: [
            { sector: 14, periodMatch: true, depthConsistency: true, snr: 6.2, status: 'PASS' },
            { sector: 15, periodMatch: false, depthConsistency: false, snr: 5.8, status: 'FAIL' },
            { sector: 26, periodMatch: false, depthConsistency: false, snr: 6.8, status: 'FAIL' }
          ],
          overallRecoveryStatus: isH18 ? 'NOT_RECOVERED' : 'INSUFFICIENT_DATA'
        }
      }
    }
  };

  return {
    timestamp: "2026-06-28T12:00:00.000Z",
    pipelineVersion: "v4.2.1-alpha",
    hourElapsed: hour,
    candidates
  };
}
