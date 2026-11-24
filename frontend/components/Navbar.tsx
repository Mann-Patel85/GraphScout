"use client";

import React from "react";
import { Compass, BarChart2, BookOpen, Layers, ExternalLink } from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export default function Navbar({ activeTab, setActiveTab }: NavbarProps) {
  const tabs = [
    { id: "studio", label: "Investigation Studio", icon: Compass },
    { id: "benchmark", label: "3-Way Benchmark", icon: BarChart2 },
    { id: "corpus", label: "Corpus Explorer", icon: BookOpen },
    { id: "schema", label: "GSQL Schema", icon: Layers },
  ];

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-8 py-3.5 border-b border-white/10 bg-[#0b1120]/80 backdrop-blur-md">
      <div className="flex items-center gap-2 bg-slate-900/60 p-1 rounded-lg border border-white/5">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-all ${
                isActive
                  ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-[#00d2ff] border border-cyan-400/30 shadow-[0_0_15px_rgba(0,210,255,0.2)]"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-3">
        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-semibold text-slate-300 border border-white/10 hover:bg-white/5 hover:text-white transition-all"
        >
          <span>OpenAPI Docs</span>
          <ExternalLink className="w-3.5 h-3.5 opacity-70" />
        </a>
      </div>
    </header>
  );
}
