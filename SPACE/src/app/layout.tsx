import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { Navbar } from "@/components/navbar";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "ISRO Exoplanet Detection Pipeline",
  description: "AI-enabled transit detection dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased dark`}>
      <body className="min-h-full flex flex-col pt-16 bg-background text-foreground font-sans">
        <Navbar />
        <main className="flex-1 w-full max-w-[1600px] mx-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
