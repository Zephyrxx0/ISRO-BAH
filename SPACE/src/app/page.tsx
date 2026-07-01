"use client";

import Link from "next/link";
import { ArrowRight, Satellite, Orbit, Stars } from "lucide-react";
import { useEffect, useState } from "react";

export default function Home() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="relative w-full h-[calc(100vh-3rem)] overflow-hidden flex flex-col items-center justify-center bg-[var(--bg)] text-[var(--fg)]">
      {/* Background Effects */}
      <div className="absolute inset-0 z-0 flex items-center justify-center pointer-events-none">
        <div className="absolute w-[800px] h-[800px] bg-[var(--accent)]/5 rounded-full blur-[120px] animate-pulse-slow"></div>
        <div className="absolute w-[400px] h-[400px] bg-[var(--accent)]/10 rounded-full blur-[80px] animate-pulse"></div>
        {/* Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080801a_1px,transparent_1px),linear-gradient(to_bottom,#8080801a_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)]"></div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center text-center space-y-10 p-6">
        
        <div className="flex items-center gap-6 text-[var(--accent)] mb-4 animate-fade-in-up" style={{ animationDelay: '0.1s', opacity: 0, animationFillMode: 'forwards' }}>
          <Orbit className="w-10 h-10 animate-spin-slow opacity-80" />
          <Satellite className="w-10 h-10 animate-pulse opacity-80" />
          <Stars className="w-10 h-10 animate-pulse opacity-80" />
        </div>

        <div className="space-y-6 animate-fade-in-up" style={{ animationDelay: '0.3s', opacity: 0, animationFillMode: 'forwards' }}>
          <h1 className="text-7xl md:text-9xl font-black font-sans tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white via-white/90 to-white/40 filter drop-shadow-[0_0_30px_rgba(255,255,255,0.2)] animate-glow">
            LIGHTSPEED
          </h1>
          <div className="flex items-center justify-center gap-4">
            <div className="h-[1px] w-12 md:w-24 bg-gradient-to-r from-transparent to-[var(--accent)]"></div>
            <p className="text-xl md:text-2xl font-mono tracking-widest text-[var(--fg-dim)] uppercase">
              Exoplanet Detection Pipeline
            </p>
            <div className="h-[1px] w-12 md:w-24 bg-gradient-to-l from-transparent to-[var(--accent)]"></div>
          </div>
        </div>

        <p className="max-w-2xl text-[var(--fg-dim)] font-mono text-sm md:text-base leading-relaxed mt-8 opacity-0 animate-fade-in-up" style={{ animationDelay: '0.5s', animationFillMode: 'forwards' }}>
          Advanced autonomous system for identifying exoplanet candidates from TESS telemetry data. Utilizing dual-view CNN ensembles and automated vetting protocols to process sectors at lightspeed.
        </p>

        <div className="pt-12 opacity-0 animate-fade-in-up" style={{ animationDelay: '0.7s', animationFillMode: 'forwards' }}>
          <Link
            href="/candidates"
            className="group relative inline-flex items-center gap-4 px-10 py-5 bg-[var(--panel)] border border-[var(--border-color)] hover:border-[var(--accent)] transition-all duration-300 overflow-hidden shadow-[0_0_0_0_rgba(230,25,25,0)] hover:shadow-[0_0_20px_0_rgba(230,25,25,0.3)]"
          >
            {/* Hover Glitch Effect Background */}
            <div className="absolute inset-0 w-0 bg-[var(--accent)] transition-all duration-500 ease-out group-hover:w-full opacity-10"></div>
            
            <span className="relative z-10 font-mono font-bold tracking-widest text-[var(--fg)] group-hover:text-white transition-colors">
              INITIALIZE SEQUENCE
            </span>
            <ArrowRight className="relative z-10 w-5 h-5 text-[var(--accent)] group-hover:translate-x-1 group-hover:text-white transition-all" />
            
            {/* Corner Accents */}
            <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-[var(--accent)] opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-[var(--accent)] opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </Link>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{__html: `
        @keyframes fade-in-up {
          0% { opacity: 0; transform: translateY(30px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes glow {
          0%, 100% { filter: drop-shadow(0 0 30px rgba(230, 25, 25, 0.15)); }
          50% { filter: drop-shadow(0 0 60px rgba(230, 25, 25, 0.4)); }
        }
        @keyframes spin-slow {
          100% { transform: rotate(360deg); }
        }
        .animate-fade-in-up {
          animation: fade-in-up 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .animate-glow {
          animation: glow 4s ease-in-out infinite;
        }
        .animate-spin-slow {
          animation: spin-slow 20s linear infinite;
        }
        .animate-pulse-slow {
          animation: pulse 8s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
      `}} />
    </div>
  );
}
