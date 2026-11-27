"use client";

import React from "react";
import { BarChart3, BookOpen, Compass, ExternalLink, Layers, Menu } from "lucide-react";
import { cx } from "./ui";

export const TABS = [
  { id: "studio", label: "Investigate", icon: Compass },
  { id: "benchmark", label: "Benchmark", icon: BarChart3 },
  { id: "corpus", label: "Corpus", icon: BookOpen },
  { id: "schema", label: "Graph Schema", icon: Layers },
] as const;

export type TabId = (typeof TABS)[number]["id"];

interface NavbarProps {
  activeTab: TabId;
  onSelect: (tab: TabId) => void;
  onOpenSidebar: () => void;
}

export default function Navbar({ activeTab, onSelect, onOpenSidebar }: NavbarProps) {
  return (
    <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-white/10 bg-[#0b1120]/85 px-4 py-2.5 backdrop-blur-md sm:px-6 lg:px-8">
      <button
        onClick={onOpenSidebar}
        className="rounded-lg p-2 text-slate-300 hover:bg-white/5 hover:text-white lg:hidden"
        aria-label="Open settings panel"
      >
        <Menu className="h-5 w-5" />
      </button>

      <nav aria-label="Main" className="min-w-0 flex-1 overflow-x-auto">
        <ul className="flex w-max items-center gap-1 rounded-lg border border-white/5 bg-slate-900/60 p-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <li key={tab.id}>
                <a
                  href={`#${tab.id}`}
                  onClick={(e) => {
                    e.preventDefault();
                    onSelect(tab.id);
                  }}
                  aria-current={active ? "page" : undefined}
                  className={cx(
                    "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    active ? "bg-cyan-400/10 text-cyan-300 ring-1 ring-cyan-400/30" : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden />
                  <span className="hidden sm:inline">{tab.label}</span>
                  <span className="sr-only sm:hidden">{tab.label}</span>
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      <a
        href="/docs"
        target="_blank"
        rel="noopener noreferrer"
        className="hidden items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-semibold text-slate-300 transition-colors hover:bg-white/5 hover:text-white md:flex"
      >
        API docs
        <ExternalLink className="h-3.5 w-3.5 opacity-70" aria-hidden />
      </a>
    </header>
  );
}
