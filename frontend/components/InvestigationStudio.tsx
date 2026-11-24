"use client";

import React, { useState } from "react";
import { InvestigationResult, PresetQuery } from "../lib/types";
import { runInvestigation } from "../lib/api";
import KnowledgeGraph from "./KnowledgeGraph";
import StepTraces from "./StepTraces";
import DocumentChunks from "./DocumentChunks";
import {
  Search,
  Sparkles,
  Zap,
  Layers,
  Copy,
  Check,
  Share2,
  Clock,
  Database,
  CheckCircle,
} from "lucide-react";

interface InvestigationStudioProps {
  presets: PresetQuery[];
  model: string;
  temperature: number;
  maxHops: number;
  threshold: number;
  tokenBudget: number;
}

export default function InvestigationStudio({
  presets,
  model,
  temperature,
  maxHops,
  threshold,
  tokenBudget,
}: InvestigationStudioProps) {
  const [query, setQuery] = useState(
    "Who won the gold medal in the event held at Eton Dorney on 6 to 8 August at the 2012 Summer Olympics?"
  );
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeEvidenceTab, setActiveEvidenceTab] = useState<"graph" | "traces" | "chunks">("graph");
  const [copied, setCopied] = useState(false);

  const handleInvestigate = async () => {
    if (!query.trim()) return;
    setIsLoading(true);
    setError(null);

    try {
      const data = await runInvestigation({
        query: query.trim(),
        model,
        temperature,
        max_hops: maxHops,
        completeness_threshold: threshold,
        token_budget: tokenBudget,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to complete investigation");
    } finally {
      setIsLoading(false);
    }
  };

  const copyAnswer = () => {
    if (!result?.final_answer) return;
    navigator.clipboard.writeText(result.final_answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Hero Header */}
      <div>
        <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
          Autonomous Agentic Investigation <Sparkles className="w-5 h-5 text-cyan-400" />
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Dynamically decomposes complex questions, explores TigerGraph GSQL relations, retrieves vector chunks, and synthesizes grounded answers with citations.
        </p>
      </div>

      {/* Preset Chips */}
      {presets.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs uppercase font-bold tracking-wider text-slate-400">
            ⚡ Curated Benchmark Scenarios
          </div>
          <div className="flex flex-wrap gap-2">
            {presets.map((p) => (
              <button
                key={p.id}
                onClick={() => setQuery(p.query)}
                className="px-3 py-1.5 rounded-full text-xs bg-slate-800/80 hover:bg-cyan-500/10 hover:text-cyan-400 border border-white/5 hover:border-cyan-500/30 text-slate-300 transition-all truncate max-w-sm text-left"
                title={p.query}
              >
                <strong className="text-cyan-400 font-semibold">{p.category}:</strong> {p.query}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search Input Card */}
      <div className="bg-[#0f172a]/80 border border-white/10 rounded-2xl p-4 shadow-xl backdrop-blur-md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-5 h-5 text-slate-400 absolute left-4 top-3.5" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleInvestigate()}
              placeholder="Ask a multi-hop or uncertain question..."
              className="w-full pl-11 pr-4 py-3 bg-slate-900 border border-white/10 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all"
            />
          </div>
          <button
            onClick={handleInvestigate}
            disabled={isLoading || !query.trim()}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-sm shadow-[0_0_20px_rgba(0,210,255,0.3)] transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            {isLoading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Investigating Graph...</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 fill-white" />
                <span>Run Investigation</span>
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
            {error}
          </div>
        )}
      </div>

      {/* Results View */}
      {result && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* KPI Metrics Banner */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="bg-[#0f172a]/70 border border-white/10 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold">
                #
              </div>
              <div>
                <div className="text-xl font-black text-slate-100 font-mono">
                  {result.metrics.total_tokens.toLocaleString()}
                </div>
                <div className="text-[11px] uppercase font-bold tracking-wider text-slate-400">Total Tokens</div>
              </div>
            </div>

            <div className="bg-[#0f172a]/70 border border-white/10 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold">
                🕸️
              </div>
              <div>
                <div className="text-xl font-black text-slate-100 font-mono">
                  {result.metrics.entities_discovered}
                </div>
                <div className="text-[11px] uppercase font-bold tracking-wider text-slate-400">Entities Linked</div>
              </div>
            </div>

            <div className="bg-[#0f172a]/70 border border-white/10 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 font-bold">
                👣
              </div>
              <div>
                <div className="text-xl font-black text-slate-100 font-mono">
                  {result.metrics.reasoning_steps}
                </div>
                <div className="text-[11px] uppercase font-bold tracking-wider text-slate-400">Reasoning Steps</div>
              </div>
            </div>

            <div className="bg-[#0f172a]/70 border border-white/10 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400 font-bold">
                🎯
              </div>
              <div>
                <div className="text-xl font-black text-slate-100 font-mono">
                  {result.metrics.completeness_pct}%
                </div>
                <div className="text-[11px] uppercase font-bold tracking-wider text-slate-400">Completeness</div>
              </div>
            </div>

            <div className="bg-[#0f172a]/70 border border-white/10 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold">
                ⏱️
              </div>
              <div>
                <div className="text-xl font-black text-slate-100 font-mono">
                  {result.latency_seconds}s
                </div>
                <div className="text-[11px] uppercase font-bold tracking-wider text-slate-400">Latency</div>
              </div>
            </div>
          </div>

          {/* Grounded Answer Card */}
          <div className="bg-gradient-to-b from-[#0f172a] to-[#0b1120] border border-cyan-400/30 rounded-2xl p-6 shadow-[0_0_30px_rgba(0,210,255,0.1)] space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <span className="text-base font-bold text-cyan-400 flex items-center gap-2">
                <span>🧭</span> Grounded Multi-Hop Answer
              </span>
              <button
                onClick={copyAnswer}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-300 bg-slate-800/80 hover:bg-slate-700 hover:text-white transition-all border border-white/10"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "Copied" : "Copy Answer"}</span>
              </button>
            </div>

            <div className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
              {result.final_answer}
            </div>

            {/* Citations */}
            <div className="pt-3 border-t border-white/10 flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Evidence Citations:</span>
              {(result.citation_references && result.citation_references.length > 0
                ? result.citation_references
                : ["Olympic Corpus Gold Documents"]
              ).map((c, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-0.5 rounded text-xs font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                >
                  📌 {c}
                </span>
              ))}
            </div>
          </div>

          {/* Evidence Exploration Container */}
          <div className="bg-[#0f172a]/70 border border-white/10 rounded-2xl overflow-hidden shadow-xl">
            {/* Sub-nav */}
            <div className="flex items-center gap-2 px-6 pt-3 border-b border-white/10 bg-[#0b1120]/60">
              <button
                onClick={() => setActiveEvidenceTab("graph")}
                className={`pb-3 px-2 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 border-b-2 transition-all ${
                  activeEvidenceTab === "graph"
                    ? "border-cyan-400 text-cyan-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <span>🕸️</span> Interactive Knowledge Graph
              </button>
              <button
                onClick={() => setActiveEvidenceTab("traces")}
                className={`pb-3 px-2 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 border-b-2 transition-all ${
                  activeEvidenceTab === "traces"
                    ? "border-cyan-400 text-cyan-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <span>👣</span> Agent Step Traces ({result.steps.length})
              </button>
              <button
                onClick={() => setActiveEvidenceTab("chunks")}
                className={`pb-3 px-2 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 border-b-2 transition-all ${
                  activeEvidenceTab === "chunks"
                    ? "border-cyan-400 text-cyan-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <span>📄</span> Supporting Vector Chunks ({result.chunks.length})
              </button>
            </div>

            {/* Sub-tab Body */}
            <div className="p-6">
              {activeEvidenceTab === "graph" && <KnowledgeGraph subgraph={result.subgraph} />}
              {activeEvidenceTab === "traces" && <StepTraces steps={result.steps} />}
              {activeEvidenceTab === "chunks" && <DocumentChunks chunks={result.chunks} />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
