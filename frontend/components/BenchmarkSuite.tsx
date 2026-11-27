"use client";

import React, { useMemo, useRef, useState } from "react";
import { BenchmarkResult, BenchmarkRow, LlmInfo, PipelineId, SystemStatus } from "../lib/types";
import { runBenchmark } from "../lib/api";
import { downloadFile, formatSeconds, useElapsed } from "../lib/hooks";
import { Bar } from "react-chartjs-2";
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip, type ChartOptions } from "chart.js";
import { BarChart3, ChevronDown, Download, FileJson, Play, Square, Trophy } from "lucide-react";
import { Badge, Button, Callout, Card, EmptyState, PageHeader, ScoreBar, SectionTitle, cx } from "./ui";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const PIPELINES: Array<{ id: PipelineId; label: string; short: string; color: string; description: string }> = [
  { id: "standard_rag", label: "Standard RAG", short: "Standard", color: "#64748b", description: "Vector search over passages, then one LLM call." },
  { id: "graph_rag", label: "GraphRAG", short: "GraphRAG", color: "#3b82f6", description: "Entity linking + 1-hop graph + passages, one LLM call." },
  { id: "agentic_rag", label: "Agentic GraphRAG", short: "Agentic", color: "#22d3ee", description: "Multi-step orchestrator loop with evaluation." },
];

const DATASETS = [
  { value: "public", label: "Public eval", detail: "Verified answers, scored", scored: true },
  { value: "sample", label: "Sample scenarios", detail: "Small demo set with answers", scored: true },
  { value: "hidden", label: "Hidden eval", detail: "No answers, so scores show n/a", scored: false },
];

const gridColor = "rgba(148,163,184,0.08)";
const tickColor = "#94a3b8";

function baseOptions(yMax?: number, yFormat?: (v: number) => string): ChartOptions<"bar"> {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: "#cbd5e1", boxWidth: 10, boxHeight: 10, font: { size: 11 } } },
      tooltip: { backgroundColor: "#0f172a", borderColor: "rgba(255,255,255,0.1)", borderWidth: 1 },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: yMax,
        ticks: { color: tickColor, callback: (v) => (yFormat ? yFormat(Number(v)) : String(v)) },
        grid: { color: gridColor },
      },
      x: { ticks: { color: "#cbd5e1", font: { weight: 600 } }, grid: { display: false } },
    },
  };
}

function toCsv(rows: BenchmarkRow[]): string {
  const header = ["question", "ground_truth", "pipeline", "answer", "accuracy", "completeness", "total_tokens", "latency_seconds", "entities", "chunks"];
  const esc = (v: unknown) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [
    header.join(","),
    ...rows.map((r) =>
      [r.question, r.ground_truth, r.pipeline, r.answer, r.accuracy, r.completeness, r.total_tokens, r.latency_seconds, r.entities_count, r.chunks_count]
        .map(esc)
        .join(",")
    ),
  ].join("\n");
}

function QuestionResult({ question, rows, defaultOpen }: { question: string; rows: BenchmarkRow[]; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const gt = rows[0]?.ground_truth;
  const best = Math.max(...rows.map((r) => r.accuracy ?? -1));

  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-900/40">
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-white/[0.02]">
        <ChevronDown className={cx("mt-0.5 h-4 w-4 shrink-0 text-slate-500 transition-transform", open && "rotate-180")} aria-hidden />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium leading-snug text-slate-100">{question}</div>
          <div className="mt-1 text-xs text-slate-500">
            Ground truth: <span className={gt ? "text-emerald-300" : "italic"}>{gt || "not available"}</span>
          </div>
        </div>
        <div className="hidden shrink-0 gap-3 md:flex">
          {rows.map((r) => (
            <div key={r.pipeline} className="text-right">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">{PIPELINES.find((p) => p.id === r.pipeline)?.short}</div>
              <div className={cx("font-mono text-xs", r.accuracy != null && r.accuracy === best && best > 0 ? "text-emerald-300" : "text-slate-300")}>
                {r.accuracy == null ? "n/a" : `${Math.round(r.accuracy * 100)}%`}
              </div>
            </div>
          ))}
        </div>
      </button>

      {open && (
        <div className="grid gap-px border-t border-white/10 bg-white/5 lg:grid-cols-3 animate-fade-in">
          {rows.map((r) => {
            const meta = PIPELINES.find((p) => p.id === r.pipeline)!;
            return (
              <div key={r.pipeline} className="space-y-3 bg-[#0c1324] p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: meta.color }} aria-hidden />
                    {meta.label}
                  </span>
                  {r.accuracy != null && r.accuracy === best && best > 0 && (
                    <Badge tone="green">
                      <Trophy className="h-3 w-3" aria-hidden /> best
                    </Badge>
                  )}
                </div>
                <p className="line-clamp-6 whitespace-pre-line text-[13px] leading-relaxed text-slate-300" title={r.answer}>
                  {r.answer || <span className="italic text-slate-500">empty answer</span>}
                </p>
                <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-white/5 pt-3 text-[11px]">
                  <dt className="text-slate-500">Accuracy</dt>
                  <dd className="text-right"><ScoreBar value={r.accuracy} /></dd>
                  <dt className="text-slate-500">Context recall</dt>
                  <dd className="text-right"><ScoreBar value={r.completeness} /></dd>
                  <dt className="text-slate-500">Tokens</dt>
                  <dd className="text-right font-mono text-slate-300">{r.total_tokens.toLocaleString()}</dd>
                  <dt className="text-slate-500">Latency</dt>
                  <dd className="text-right font-mono text-slate-300">{formatSeconds(r.latency_seconds)}</dd>
                  <dt className="text-slate-500">Entities / passages</dt>
                  <dd className="text-right font-mono text-slate-300">
                    {r.entities_count} / {r.chunks_count}
                  </dd>
                </dl>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function BenchmarkSuite({
  model,
  temperature,
  llm,
  status,
}: {
  model: string;
  temperature: number;
  llm?: LlmInfo;
  status: SystemStatus | null;
}) {
  const [dataset, setDataset] = useState("public");
  const [limit, setLimit] = useState(2);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<BenchmarkResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const elapsed = useElapsed(isLoading);

  const datasetMeta = DATASETS.find((d) => d.value === dataset)!;
  const datasetCount =
    dataset === "public" ? status?.datasets.eval_public_questions : dataset === "hidden" ? status?.datasets.eval_hidden_questions : undefined;

  const handleRun = async () => {
    const controller = new AbortController();
    abortRef.current = controller;
    setIsLoading(true);
    setError(null);
    try {
      setResult(await runBenchmark({ dataset, limit, model, temperature }, controller.signal));
    } catch (err) {
      if ((err as Error).name !== "AbortError") setError((err as Error).message);
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  };

  const byQuestion = useMemo(() => {
    const groups = new Map<string, BenchmarkRow[]>();
    result?.rows.forEach((r) => groups.set(r.question, [...(groups.get(r.question) ?? []), r]));
    return Array.from(groups.entries());
  }, [result]);

  const hasScores = !!result && PIPELINES.some((p) => result.summary[p.id].avg_accuracy != null);

  const qualityChart = result && {
    labels: PIPELINES.map((p) => p.label),
    datasets: [
      { label: "Answer accuracy", data: PIPELINES.map((p) => result.summary[p.id].avg_accuracy), backgroundColor: "#22d3ee", borderRadius: 6, maxBarThickness: 36 },
      { label: "Context recall", data: PIPELINES.map((p) => result.summary[p.id].avg_completeness), backgroundColor: "#a855f7", borderRadius: 6, maxBarThickness: 36 },
    ],
  };
  const costChart = result && {
    labels: PIPELINES.map((p) => p.label),
    datasets: [
      { label: "Avg tokens", data: PIPELINES.map((p) => result.summary[p.id].avg_tokens), backgroundColor: PIPELINES.map((p) => p.color), borderRadius: 6, maxBarThickness: 48 },
    ],
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={BarChart3}
        title="Pipeline Benchmark"
        description="Runs the same questions through three retrieval strategies and scores each answer against ground truth: accuracy (is the answer correct?) and context recall (did retrieval surface the answer?)."
      />

      {/* Pipelines explainer */}
      <div className="grid gap-3 md:grid-cols-3">
        {PIPELINES.map((p) => (
          <div key={p.id} className="flex gap-3 rounded-xl border border-white/10 bg-surface/50 p-4">
            <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: p.color }} aria-hidden />
            <div>
              <div className="text-sm font-semibold text-slate-100">{p.label}</div>
              <div className="mt-0.5 text-xs leading-relaxed text-slate-400">{p.description}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Controls */}
      <Card className="space-y-4">
        <div className="grid gap-4 md:grid-cols-[1fr_auto_auto] md:items-end">
          <fieldset>
            <legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Dataset</legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {DATASETS.map((d) => (
                <label
                  key={d.value}
                  className={cx(
                    "cursor-pointer rounded-lg border px-3 py-2 transition-colors",
                    dataset === d.value ? "border-cyan-400/50 bg-cyan-400/[0.06]" : "border-white/10 hover:border-white/20"
                  )}
                >
                  <input type="radio" name="dataset" value={d.value} checked={dataset === d.value} onChange={() => setDataset(d.value)} className="sr-only" />
                  <div className="text-sm font-medium text-slate-100">{d.label}</div>
                  <div className="text-[11px] text-slate-500">{d.detail}</div>
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <label htmlFor="limit" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
              Questions
            </label>
            <select id="limit" value={limit} onChange={(e) => setLimit(parseInt(e.target.value, 10))} className="field md:w-28">
              {[1, 2, 3, 5, 10].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-2">
            {isLoading && (
              <Button icon={Square} onClick={() => abortRef.current?.abort()}>
                Cancel
              </Button>
            )}
            <Button variant="primary" size="lg" icon={Play} loading={isLoading} onClick={handleRun}>
              {isLoading ? `Running… ${formatSeconds(elapsed)}` : "Run benchmark"}
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          {datasetCount != null && <p className="text-xs text-slate-500">Uses the first {limit} of {datasetCount} questions.</p>}
          {!datasetMeta.scored && <Callout tone="cyan">This dataset has no answers, so accuracy and recall will show n/a. Tokens and latency still compare.</Callout>}
          {llm && !llm.live && <Callout tone="amber">No LLM key configured: answers are simulated and scores won&apos;t mean anything.</Callout>}
          {llm?.provider === "groq" && limit >= 3 && (
            <Callout tone="amber">
              On Groq&apos;s free tier each question takes 1–2 minutes (three pipelines, rate-limited). {limit} questions may take {limit * 2}+ minutes.
            </Callout>
          )}
          {error && <Callout tone="red">{error}</Callout>}
        </div>
      </Card>

      {!result && !isLoading && (
        <Card padded={false}>
          <EmptyState icon={BarChart3} title="No benchmark run yet">
            Pick a dataset and run it. Start with 1–2 questions; each runs through all three pipelines.
          </EmptyState>
        </Card>
      )}

      {result && (
        <div className={cx("space-y-6 animate-slide-up", isLoading && "opacity-50 transition-opacity")}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-400">
              <span className="font-semibold text-slate-200">{result.questions_evaluated}</span> questions from{" "}
              <span className="font-mono text-slate-300">{result.dataset_name}</span> in {formatSeconds(result.total_duration_seconds)}
              {result.llm && (
                <>
                  {" "}
                  · <span className="font-mono">{result.llm.live ? `${result.llm.provider}/${result.llm.model}` : "simulated"}</span>
                </>
              )}
            </p>
            <div className="flex gap-2">
              <Button size="sm" icon={Download} onClick={() => downloadFile("benchmark_results.csv", toCsv(result.rows), "text/csv")}>
                CSV
              </Button>
              <Button size="sm" icon={FileJson} onClick={() => downloadFile("benchmark_report.json", JSON.stringify(result, null, 2), "application/json")}>
                JSON
              </Button>
            </div>
          </div>

          {result.llm?.live && result.llm.fallback_calls > 0 && (
            <Callout tone="amber">{result.llm.fallback_calls} LLM call(s) failed (likely rate limits). Some answers are placeholders, so treat scores with care.</Callout>
          )}

          {/* Summary table */}
          <Card padded={false} className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-[11px] uppercase tracking-wider text-slate-500">
                  <th className="px-4 py-3 font-semibold">Pipeline</th>
                  <th className="px-4 py-3 font-semibold">Accuracy</th>
                  <th className="px-4 py-3 font-semibold">Context recall</th>
                  <th className="px-4 py-3 text-right font-semibold">Avg tokens</th>
                  <th className="px-4 py-3 text-right font-semibold">Avg latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {PIPELINES.map((p) => {
                  const s = result.summary[p.id];
                  return (
                    <tr key={p.id}>
                      <td className="px-4 py-3">
                        <span className="flex items-center gap-2 font-medium text-slate-100">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: p.color }} aria-hidden />
                          {p.label}
                        </span>
                      </td>
                      <td className="px-4 py-3"><ScoreBar value={s.avg_accuracy} /></td>
                      <td className="px-4 py-3"><ScoreBar value={s.avg_completeness} /></td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-300">{s.avg_tokens.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-300">{formatSeconds(s.avg_latency)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>

          {/* Charts */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <SectionTitle>Answer quality (higher is better)</SectionTitle>
              {hasScores && qualityChart ? (
                <div className="h-64">
                  <Bar data={qualityChart} options={baseOptions(1, (v) => `${Math.round(v * 100)}%`)} />
                </div>
              ) : (
                <EmptyState icon={BarChart3} title="No ground truth for these questions" />
              )}
            </Card>
            <Card>
              <SectionTitle>Token cost (lower is cheaper)</SectionTitle>
              {costChart && (
                <div className="h-64">
                  <Bar data={costChart} options={{ ...baseOptions(), plugins: { ...baseOptions().plugins, legend: { display: false } } }} />
                </div>
              )}
            </Card>
          </div>

          {/* Per question */}
          <section>
            <SectionTitle>Per-question results</SectionTitle>
            <div className="space-y-3">
              {byQuestion.map(([q, rows], i) => (
                <QuestionResult key={q} question={q} rows={rows} defaultOpen={i === 0} />
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
