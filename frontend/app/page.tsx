"use client";

import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";
import InvestigationStudio from "../components/InvestigationStudio";
import BenchmarkSuite from "../components/BenchmarkSuite";
import CorpusExplorer from "../components/CorpusExplorer";
import GsqlSchemaView from "../components/GsqlSchemaView";
import { SystemStatus, PresetQuery } from "../lib/types";
import { getSystemStatus, getPresetQueries } from "../lib/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState<string>("studio");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [presets, setPresets] = useState<PresetQuery[]>([]);

  // Orchestrator Hyperparameters
  const [model, setModel] = useState<string>("gpt-4o");
  const [temperature, setTemperature] = useState<number>(0.1);
  const [maxHops, setMaxHops] = useState<number>(6);
  const [threshold, setThreshold] = useState<number>(0.85);
  const [tokenBudget, setTokenBudget] = useState<number>(16000);

  useEffect(() => {
    getSystemStatus().then(setStatus).catch(console.error);
    getPresetQueries().then(setPresets).catch(console.error);
  }, []);

  return (
    <div className="flex w-screen min-h-screen bg-[#070b14] text-slate-100">
      {/* Fixed Left Sidebar */}
      <Sidebar
        status={status}
        model={model}
        setModel={setModel}
        temperature={temperature}
        setTemperature={setTemperature}
        maxHops={maxHops}
        setMaxHops={setMaxHops}
        threshold={threshold}
        setThreshold={setThreshold}
        tokenBudget={tokenBudget}
        setTokenBudget={setTokenBudget}
      />

      {/* Main Content Pane */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="p-8 flex-1">
          {activeTab === "studio" && (
            <InvestigationStudio
              presets={presets}
              model={model}
              temperature={temperature}
              maxHops={maxHops}
              threshold={threshold}
              tokenBudget={tokenBudget}
            />
          )}

          {activeTab === "benchmark" && <BenchmarkSuite model={model} />}

          {activeTab === "corpus" && <CorpusExplorer />}

          {activeTab === "schema" && <GsqlSchemaView />}
        </main>
      </div>
    </div>
  );
}
