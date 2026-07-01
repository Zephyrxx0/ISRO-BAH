import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { Navbar } from "@/components/navbar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "700", "900"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "LIGHTSPEED",
  description: "TESS Transit Detection — Raw Telemetry Terminal",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full dark`}
    >
      <body className="min-h-full flex flex-col pt-12 bg-[var(--bg)] text-[var(--fg)] font-mono antialiased">
        <Navbar />
        <main className="flex-1 w-full max-w-[1800px] mx-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
