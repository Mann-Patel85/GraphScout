"use client";

import React, { useCallback, useEffect, useState } from "react";
import Sidebar, { DEFAULT_SETTINGS, type OrchestratorSettings } from "../components/Sidebar";
import Navbar, { TABS, type TabId } from "../components/Navbar";
import InvestigationStudio from "../components/InvestigationStudio";
import BenchmarkSuite from "../components/BenchmarkSuite";
import CorpusExplorer from "../components/CorpusExplorer";
import SchemaView from "../components/SchemaView";
import { Button, Callout } from "../components/ui";
import { SystemStatus, PresetQuery } from "../lib/types";
import { getSystemStatus, getPresetQueries } from "../lib/api";
import { RotateCw } from "lucide-react";

function tabFromHash(): TabId {
  if (typeof window === "undefined") return "studio";
  const id = window.location.hash.replace("#", "");
  return (TABS.some((t) => t.id === id) ? id : "studio") as TabId;
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>("studio");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [presets, setPresets] = useState<PresetQuery[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settings, setSettings] = useState<OrchestratorSettings>(DEFAULT_SETTINGS);

  // Keep the active tab in the URL hash so refresh / shared links land on the same view.
  useEffect(() => {
    setActiveTab(tabFromHash());
    const onHash = () => setActiveTab(tabFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const selectTab = (tab: TabId) => {
    setActiveTab(tab);
    window.history.replaceState(null, "", `#${tab}`);
  };

  const loadStatus = useCallback(async () => {
    setStatusError(null);
    try {
      const s = await getSystemStatus();
      setStatus(s);
      // Default to the configured provider's model unless the user already picked one.
      const models = s.llm?.models ?? [];
      setSettings((cur) => (cur.model && models.includes(cur.model) ? cur : { ...cur, model: s.llm?.default_model ?? "" }));
      getPresetQueries().then(setPresets).catch(() => setPresets([]));
    } catch (err) {
      setStatus(null);
      setStatusError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  return (
    <div className="flex min-h-screen w-full">
      <Sidebar
        status={status}
        statusError={statusError}
        settings={settings}
        onChange={setSettings}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex h-screen min-w-0 flex-1 flex-col overflow-y-auto">
        <Navbar activeTab={activeTab} onSelect={selectTab} onOpenSidebar={() => setSidebarOpen(true)} />

        <main className="mx-auto w-full max-w-[1400px] flex-1 space-y-4 p-4 sm:p-6 lg:p-8">
          {statusError && (
            <Callout tone="red" title="Backend not reachable">
              <div className="flex flex-wrap items-center gap-3">
                <span>{statusError}</span>
                <Button size="sm" icon={RotateCw} onClick={loadStatus}>
                  Retry
                </Button>
              </div>
            </Callout>
          )}

          {/* Tabs stay mounted so results survive switching views. */}
          <div hidden={activeTab !== "studio"}>
            <InvestigationStudio presets={presets} settings={settings} llm={status?.llm} />
          </div>
          <div hidden={activeTab !== "benchmark"}>
            <BenchmarkSuite model={settings.model} temperature={settings.temperature} llm={status?.llm} status={status} />
          </div>
          {activeTab === "corpus" && <CorpusExplorer totalDocs={status?.datasets.corpus_documents} />}
          {activeTab === "schema" && <SchemaView />}
        </main>

        <footer className="border-t border-white/5 px-4 py-4 text-center text-xs text-slate-600 sm:px-8">
          GraphScout · Agentic GraphRAG · FastAPI + Next.js
        </footer>
      </div>
    </div>
  );
}
