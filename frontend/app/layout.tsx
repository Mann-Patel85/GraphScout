import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GraphScout | Agentic GraphRAG on TigerGraph",
  description: "Autonomous Multi-Agent GraphRAG System powered by TigerGraph, Multi-Hop Hybrid Search, and Dynamic Knowledge Gap Resolution.",
  icons: {
    icon: "data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220%22><text y=%2226%22 font-size=%2226%22>🧭</text></svg>",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-[#070b14] text-slate-100 min-h-screen flex flex-col font-sans">
        {children}
      </body>
    </html>
  );
}
