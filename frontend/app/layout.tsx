import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "GraphScout | Agentic GraphRAG",
  description:
    "An autonomous multi-agent GraphRAG system: an LLM orchestrator that plans graph traversals and vector searches, evaluates its evidence, and answers multi-hop questions with citations.",
  icons: {
    icon: "data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22><rect width=%2232%22 height=%2232%22 rx=%228%22 fill=%22%230e7490%22/><circle cx=%2210%22 cy=%2211%22 r=%223.5%22 fill=%22white%22/><circle cx=%2222%22 cy=%229%22 r=%223%22 fill=%22white%22/><circle cx=%2217%22 cy=%2222%22 r=%224%22 fill=%22white%22/><path d=%22M10 11 L22 9 L17 22 Z%22 stroke=%22white%22 stroke-width=%221.5%22 fill=%22none%22/></svg>",
  },
};

export const viewport: Viewport = {
  themeColor: "#070b14",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${mono.variable}`}>
      <body className="min-h-screen bg-[#070b14] font-sans text-slate-200 antialiased">{children}</body>
    </html>
  );
}
