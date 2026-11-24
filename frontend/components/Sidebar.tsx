"use client";

import React from "react";
import { SystemStatus } from "../lib/types";
import { Cpu, Database, Settings2, FileText, CheckCircle2 } from "lucide-react";

interface SidebarProps {
  status: SystemStatus | null;
  model: string;
  setModel: (m: string) => void;
  temperature: number;
  setTemperature: (t: number) => void;
  maxHops: number;
  setMaxHops: (h: number) => void;
  threshold: number;
  setThreshold: (t: number) => void;
  tokenBudget: number;
  setTokenBudget: (b: number) => void;
}

export default function Sidebar({
  status,
  model,
  setModel,
  temperature,
  setTemperature,
  maxHops,
  setMaxHops,
  threshold,
  setThreshold,
  tokenBudget,
  setTokenBudget,
}: SidebarProps) {
  return (
    <aside className="w-80 bg-[#0b1120] border-r border-white/10 flex flex-col h-screen sticky top-0 overflow-y-auto shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-white/10 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#00d2ff] to-[#3b82f6] flex items-center justify-center text-xl shadow-[0_0_20px_rgba(0,210,255,0.4)]">
          🧭
        </div>
        <div>
          <div className="text-lg font-black tracking-tight bg-gradient-to-r from-white via-slate-100 to-cyan-300 bg-clip-text text-transparent">
            GraphScout
          </div>
          <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
            Agentic GraphRAG &bull; TigerGraph
          </div>
        </div>
      </div>

      {/* Engine Status */}
      <div className="p-5 border-b border-white/10 space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          <span>Engine Configuration</span>
        </div>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Host</span>
            <span className="font-mono text-slate-200">{status?.tigergraph.host || "127.0.0.1:14240"}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Graph Name</span>
            <span className="font-semibold text-slate-200">{status?.tigergraph.graph_name || "GraphScoutKG"}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Mode</span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-subtle" />
              <span>{status?.tigergraph.mode_label || "Connected"}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Model & Orchestrator Settings */}
      <div className="p-5 border-b border-white/10 space-y-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span>Orchestrator Hyperparameters</span>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs text-slate-300 font-medium">Reasoning Model</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-3 py-2 text-xs bg-slate-900 border border-white/10 rounded-md text-slate-200 focus:outline-none focus:border-cyan-400"
          >
            <option value="gpt-4o">gpt-4o (High Reasoning)</option>
            <option value="gpt-4o-mini">gpt-4o-mini (Fast / Budget)</option>
            <option value="claude-3-5-sonnet-20241022">claude-3-5-sonnet</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-slate-300">Temperature</span>
            <span className="font-mono font-bold text-cyan-400">{temperature.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            className="w-full accent-cyan-400 cursor-pointer"
          />
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-slate-300">Max Reasoning Hops</span>
            <span className="font-mono font-bold text-cyan-400">{maxHops}</span>
          </div>
          <input
            type="range"
            min="2"
            max="10"
            step="1"
            value={maxHops}
            onChange={(e) => setMaxHops(parseInt(e.target.value, 10))}
            className="w-full accent-cyan-400 cursor-pointer"
          />
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-slate-300">Completeness Threshold</span>
            <span className="font-mono font-bold text-cyan-400">{Math.round(threshold * 100)}%</span>
          </div>
          <input
            type="range"
            min="0.5"
            max="1"
            step="0.05"
            value={threshold}
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            className="w-full accent-cyan-400 cursor-pointer"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs text-slate-300 font-medium">Token Budget</label>
          <select
            value={tokenBudget}
            onChange={(e) => setTokenBudget(parseInt(e.target.value, 10))}
            className="w-full px-3 py-2 text-xs bg-slate-900 border border-white/10 rounded-md text-slate-200 focus:outline-none focus:border-cyan-400"
          >
            <option value="8000">8,000 tokens</option>
            <option value="16000">16,000 tokens (Balanced)</option>
            <option value="32000">32,000 tokens (Deep Audit)</option>
          </select>
        </div>
      </div>

      {/* Dataset Indicators */}
      <div className="p-5 space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
          <FileText className="w-3.5 h-3.5 text-cyan-400" />
          <span>Datasets Status</span>
        </div>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Olympic Corpus</span>
            <span className="font-semibold text-slate-200">
              {status?.datasets.corpus_documents ? `${status.datasets.corpus_documents.toLocaleString()} docs` : "2,951 docs"}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Public Eval Suite</span>
            <span className="font-semibold text-slate-200">
              {status?.datasets.eval_public_questions ? `${status.datasets.eval_public_questions} Qs` : "100 Qs"}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Hidden Eval Suite</span>
            <span className="font-semibold text-slate-200">
              {status?.datasets.eval_hidden_questions ? `${status.datasets.eval_hidden_questions} Qs` : "50 Qs"}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Indexed Entities</span>
            <span className="font-semibold text-cyan-400">
              {status?.tigergraph.indexed_entities ? `${status.tigergraph.indexed_entities}+` : "1,000+"}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
