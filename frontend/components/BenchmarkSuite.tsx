"use client";

import React, { useState } from "react";
import { BenchmarkResult } from "../lib/types";
import { runBenchmark } from "../lib/api";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Play, Download, BarChart3, Clock, CheckCircle2 } from "lucide-react";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface BenchmarkSuiteProps {
  model: string;
}

export default function BenchmarkSuite({ model }: BenchmarkSuiteProps) {
  const [dataset, setDataset] = useState<string>("public");
  const [limit, setLimit] = useState<number>(3);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<BenchmarkResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunBenchmark = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await runBenchmark({
        dataset,
        limit,
        model,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Benchmark failed");
    } finally {
      setIsLoading(false);
    }
  };

  const exportJSON = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "benchmark_report.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  // Chart data configs
  const completenessChartData = result
    ? {
        labels: ["Standard RAG", "GraphRAG (1-Hop)", "Agentic GraphRAG (GraphScout)"],
        datasets: [
          {
            label: "Average Completeness Score",
            data: [
              result.summary.standard_rag.avg_completeness,
              result.summary.graph_rag.avg_completeness,
              result.summary.agentic_rag.avg_completeness,
            ],
            backgroundColor: ["#64748b", "#3b82f6", "#00d2ff"],
            borderRadius: 8,
          },
        ],
      }
    : null;

  const tokensChartData = result
    ? {
        labels: ["Standard RAG", "GraphRAG (1-Hop)", "Agentic GraphRAG (GraphScout)"],
        datasets: [
          {
            label: "Average Total Tokens",
            data: [
              result.summary.standard_rag.avg_tokens,
              result.summary.graph_rag.avg_tokens,
              result.summary.agentic_rag.avg_tokens,
            ],
            backgroundColor: ["#94a3b8", "#a855f7", "#10b981"],
            borderRadius: 8,
          },
        ],
      }
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
          3-Way Multi-Hop Evaluation Harness <BarChart3 className="w-5 h-5 text-cyan-400" />
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Direct head-to-head comparison evaluating <strong>Standard RAG</strong> vs <strong>GraphRAG (1-Hop)</strong> vs <strong>Agentic GraphRAG (GraphScout)</strong> across Accuracy, Completeness, and Token Efficiency.
        </p>
      </div>

      {/* Benchmark Controls */}
      <div className="bg-[#0f172a]/80 border border-white/10 rounded-2xl p-5 shadow-xl backdrop-blur-md">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Evaluation Dataset</label>
            <select
              value={dataset}
              onChange={(e) => setDataset(e.target.value)}
              className="w-full px-3 py-2.5 text-xs bg-slate-900 border border-white/10 rounded-xl text-slate-200 focus:outline-none focus:border-cyan-400"
            >
              <option value="public">data/eval_public.jsonl (100 Verified Questions)</option>
              <option value="hidden">data/eval_hidden.jsonl (50 Competition Questions)</option>
              <option value="sample">data/benchmark_questions.json (Sample Scenarios)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Question Evaluation Count</label>
            <select
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value, 10))}
              className="w-full px-3 py-2.5 text-xs bg-slate-900 border border-white/10 rounded-xl text-slate-200 focus:outline-none focus:border-cyan-400"
            >
              <option value={2}>2 Questions (Rapid Verification)</option>
              <option value={3}>3 Questions (Standard)</option>
              <option value={5}>5 Questions (Deep)</option>
              <option value={10}>10 Questions (Benchmark)</option>
            </select>
          </div>

          <div>
            <button
              onClick={handleRunBenchmark}
              disabled={isLoading}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs shadow-[0_0_20px_rgba(0,210,255,0.3)] transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Benchmarking Pipelines...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  <span>Run 3-Way Benchmark</span>
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
            {error}
          </div>
        )}
      </div>

      {/* Visual Analytics */}
      {result && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Charts Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="bg-[#0f172a]/70 border border-white/10 rounded-2xl p-5">
              <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
                <span>🎯</span> Completeness Score by Pipeline (Higher is Better)
              </h3>
              {completenessChartData && (
                <Bar
                  data={completenessChartData}
                  options={{
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                      y: { beginAtZero: true, max: 1.0, ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.05)" } },
                      x: { ticks: { color: "#cbd5e1", font: { weight: "bold" } }, grid: { display: false } },
                    },
                  }}
                />
              )}
            </div>

            <div className="bg-[#0f172a]/70 border border-white/10 rounded-2xl p-5">
              <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
                <span>⚡</span> Token Consumption by Pipeline (Efficiency)
              </h3>
              {tokensChartData && (
                <Bar
                  data={tokensChartData}
                  options={{
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                      y: { beginAtZero: true, ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.05)" } },
                      x: { ticks: { color: "#cbd5e1", font: { weight: "bold" } }, grid: { display: false } },
                    },
                  }}
                />
              )}
            </div>
          </div>

          {/* Results Table */}
          <div className="bg-[#0f172a]/70 border border-white/10 rounded-2xl p-5 overflow-hidden">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-white/10">
              <h3 className="text-sm font-bold text-slate-200">
                Detailed Evaluation Breakdown ({result.rows.length} runs across {result.questions_evaluated} questions in {result.total_duration_seconds}s)
              </h3>
              <button
                onClick={exportJSON}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white transition-all border border-white/10"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export JSON Report</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/10 bg-slate-900/60 text-slate-400">
                    <th className="py-3 px-3">Question</th>
                    <th className="py-3 px-3">Pipeline</th>
                    <th className="py-3 px-3 text-right">Accuracy</th>
                    <th className="py-3 px-3 text-right">Completeness</th>
                    <th className="py-3 px-3 text-right">Tokens</th>
                    <th className="py-3 px-3 text-right">Latency</th>
                    <th className="py-3 px-3 text-right">Entities</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {result.rows.map((r, i) => {
                    const isAgentic = r.pipeline === "agentic_rag";
                    return (
                      <tr key={i} className="hover:bg-white/[0.02]">
                        <td className="py-3 px-3 max-w-xs truncate text-slate-200" title={r.question}>
                          {r.question}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`font-semibold ${
                              isAgentic ? "text-cyan-400" : "text-slate-300"
                            }`}
                          >
                            {r.pipeline_label}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right font-mono font-bold text-emerald-400">
                          {r.accuracy.toFixed(2)}
                        </td>
                        <td className="py-3 px-3 text-right font-mono font-bold text-cyan-400">
                          {Math.round(r.completeness * 100)}%
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-300">
                          {r.total_tokens.toLocaleString()}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-400">
                          {r.latency_seconds.toFixed(3)}s
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-400">
                          {r.entities_count}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
