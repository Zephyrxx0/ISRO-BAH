"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Navbar() {
  const pathname = usePathname();

  const links = [
    { href: "/", label: "CANDIDATES" },
    { href: "/map", label: "STAR MAP" },
    { href: "/about", label: "ABOUT" },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 h-12 bg-[var(--panel)] border-b border-[var(--border-color)] flex items-center justify-between px-6 z-50">
      <div className="flex items-center gap-3">
        <span className="text-[var(--accent)] font-bold font-mono text-sm">
          [
        </span>
        <span className="font-sans font-black text-sm tracking-tighter text-[var(--fg)]">
          EXOPLANET PIPELINE
        </span>
        <span className="text-[var(--fg-dim)] font-mono text-xs">
          REV 2.6 // TESS S1–3
        </span>
        <span className="text-[var(--accent)] font-bold font-mono text-sm">
          ]
        </span>
      </div>

      <div className="flex items-center gap-1">
        {links.map((link, i) => {
          const isActive = pathname === link.href;
          return (
            <span key={link.href} className="flex items-center">
              {i > 0 && (
                <span className="text-[var(--border-color)] mx-1 font-mono text-xs">
                  //
                </span>
              )}
              <Link
                href={link.href}
                className={`font-mono text-xs px-3 py-1 transition-colors ${
                  isActive
                    ? "bg-[var(--accent)] text-[var(--fg)]"
                    : "text-[var(--fg-dim)] hover:text-[var(--fg)] hover:bg-[var(--surface)]"
                }`}
              >
                {link.label}
              </Link>
            </span>
          );
        })}
      </div>
    </nav>
  );
}
