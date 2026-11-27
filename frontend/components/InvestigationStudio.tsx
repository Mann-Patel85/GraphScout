"use client";

import React, { useCallback, useRef, useState } from "react";
import { CorpusDocDetail, InvestigationResult, LlmInfo, PresetQuery } from "../lib/types";
import { getCorpusDocDetail, runInvestigation } from "../lib/api";
import { formatSeconds, useElapsed } from "../lib/hooks";
import type { OrchestratorSettings } from "./Sidebar";
import KnowledgeGraph from "./KnowledgeGraph";
import StepTraces from "./StepTraces";
import DocumentChunks from "./DocumentChunks";
import DocumentModal from "./DocumentModal";
import { Badge, Button, Callout, Card, CopyButton, EmptyState, PageHeader, Segmented, Stat } from "./ui";
import {
  Clock,
  Coins,
  Compass,
  FileText,
  Footprints,
  Lightbulb,
  Network,
  Play,
  Quote,
  Sparkles,
  Square,
  Target,
} from "lucide-react";

interface InvestigationStudioProps {
  presets: PresetQuery[];
  settings: OrchestratorSettings;
  llm?: LlmInfo;
}

type EvidenceTab = "graph" | "steps" | "chunks";

const DEFAULT_QUERY =
  "Who won the gold medal in the event held at Eton Dorney on 6 to 8 August at the 2012 Summer Olympics?";

export default function InvestigationStudio({ presets, settings, llm }: InvestigationStudioProps) {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<EvidenceTab>("graph");
  const [highlightChunk, setHighlightChunk] = useState<string | null>(null);
  const [openDoc, setOpenDoc] = useState<CorpusDocDetail | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const evidenceRef = useRef<HTMLDivElement>(null);
  const elapsed = useElapsed(isLoading);

  const handleInvestigate = async () => {
    const q = query.trim();
    if (!q || isLoading) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setIsLoading(true);
    setError(null);
    setHighlightChunk(null);

    try {
      const data = await runInvestigation(
        {
          query: q,
          model: settings.model,
          temperature: settings.temperature,
          max_hops: settings.maxHops,
          completeness_threshold: settings.threshold,
          token_budget: settings.tokenBudget,
        },
        controller.signal
      );
      setResult(data);
      setTab(data.subgraph.nodes.length > 0 ? "graph" : "steps");
    } catch (err) {
      if ((err as Error).name !== "AbortError") setError((err as Error).message);
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  };

  const cancel = () => abortRef.current?.abort();

  const openDocument = useCallback(async (docId: string) => {
    try {
      setOpenDoc(await getCorpusDocDetail(docId));
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  const chunkIds = new Set(result?.chunks.map((c) => c.chunk_id));

  const jumpToChunk = (chunkId: string) => {
    setHighlightChunk(chunkId);
    setTab("chunks");
    evidenceRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const answerFailed = result?.final_answer.startsWith("⚠");

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Compass}
        title="Investigation Studio"
        description="Ask a multi-hop question. An orchestrator agent decides each step: linking entities, traversing the knowledge graph, searching passages, or evaluating whether it has enough evidence, then writes a cited answer."
      />

      {/* Query composer */}
      <Card className="space-y-4">
        <div>
          <label htmlFor="query" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
            Question
          </label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                handleInvestigate();
              }
            }}
            rows={2}
            placeholder="e.g. Which athletics event at the 2008 Summer Olympics had the most competitors?"
            className="field min-h-[4.5rem] resize-y text-[15px] leading-relaxed"
          />
        </div>

        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500">
            <kbd className="rounded border border-white/10 bg-slate-800 px-1.5 py-0.5 font-mono text-[10px]">Ctrl</kbd> +{" "}
            <kbd className="rounded border border-white/10 bg-slate-800 px-1.5 py-0.5 font-mono text-[10px]">Enter</kbd> to run
            {settings.model && (
              <>
                {" "}
                · <span className="font-mono text-slate-400">{settings.model}</span>
              </>
            )}
          </p>
          <div className="flex gap-2">
            {isLoading && (
              <Button variant="secondary" icon={Square} onClick={cancel}>
                Cancel
              </Button>
            )}
            <Button variant="primary" size="lg" icon={Play} loading={isLoading} disabled={!query.trim()} onClick={handleInvestigate}>
              {isLoading ? `Investigating… ${formatSeconds(elapsed)}` : "Run investigation"}
            </Button>
          </div>
        </div>

        {isLoading && llm?.provider === "groq" && elapsed > 8 && (
          <p className="text-xs text-slate-500 animate-fade-in">
            Free-tier Groq limits tokens per minute, so a full run usually takes 1–2 minutes. The agent is still working.
          </p>
        )}
        {error && <Callout tone="red">{error}</Callout>}
      </Card>

      {/* Presets */}
      {presets.length > 0 && !result && !isLoading && (
        <section aria-label="Example questions" className="animate-fade-in">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <Lightbulb className="h-3.5 w-3.5 text-cyan-400" aria-hidden />
            Try an example
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {presets.map((p) => (
              <button
                key={p.id}
                onClick={() => setQuery(p.query)}
                className="group flex flex-col gap-2 rounded-xl border border-white/10 bg-surface/50 p-4 text-left transition-all hover:border-cyan-400/40 hover:bg-surface"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-cyan-300">{p.category}</span>
                  <span className="text-[11px] text-slate-500">{p.hops} hops</span>
                </div>
                <span className="line-clamp-2 text-sm leading-snug text-slate-300 group-hover:text-white">{p.query}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {!result && !isLoading && presets.length === 0 && (
        <Card padded={false}>
          <EmptyState icon={Sparkles} title="Ready when you are">
            Enter a question above and run an investigation to see the agent&apos;s reasoning, knowledge graph and cited answer.
          </EmptyState>
        </Card>
      )}

      {/* Results */}
      {result && (
        <div className={`space-y-6 animate-slide-up ${isLoading ? "opacity-50 transition-opacity" : ""}`}>
          {result.llm && !result.llm.live && (
            <Callout tone="amber" title="Offline simulation">
              No LLM API key is configured, so this answer is canned demo output, not real reasoning over the question.
            </Callout>
          )}
          {result.llm?.live && result.llm.fallback_calls > 0 && (
            <Callout tone="amber" title={`${result.llm.fallback_calls} LLM call(s) failed during this run`}>
              Usually a provider rate limit. Affected steps returned placeholders, so the answer may be incomplete. Try again in a minute
              or lower the token budget.
            </Callout>
          )}

          {/* Answer */}
          <Card as="section" className={answerFailed ? "border-red-400/30" : "border-cyan-400/25 bg-gradient-to-b from-cyan-400/[0.04] to-transparent"}>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-cyan-300">
                <Sparkles className="h-4 w-4" aria-hidden />
                Answer
              </h2>
              <div className="flex items-center gap-2">
                {result.llm && (
                  <Badge tone={result.llm.live ? "neutral" : "amber"}>
                    {result.llm.live ? `${result.llm.provider} · ${result.llm.model}` : "simulated"}
                  </Badge>
                )}
                <CopyButton text={result.final_answer} />
              </div>
            </div>

            <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-slate-100">{result.final_answer}</p>

            <div className="mt-4 text-xs text-slate-500">Question: {result.query}</div>

            {result.citation_references.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-white/10 pt-4">
                <span className="flex items-center gap-1.5 text-xs font-medium text-slate-400">
                  <Quote className="h-3.5 w-3.5" aria-hidden />
                  Citations
                </span>
                {result.citation_references.map((c) =>
                  chunkIds.has(c) ? (
                    <button
                      key={c}
                      onClick={() => jumpToChunk(c)}
                      className="rounded-md border border-cyan-400/25 bg-cyan-400/10 px-2 py-0.5 font-mono text-[11px] text-cyan-200 transition-colors hover:bg-cyan-400/20"
                      title="Show this passage"
                    >
                      {c}
                    </button>
                  ) : (
                    <Badge key={c} tone="neutral" className="font-mono">
                      {c}
                    </Badge>
                  )
                )}
              </div>
            )}
          </Card>

          {/* Metrics */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
            <Stat icon={Footprints} label="Agent steps" value={result.metrics.reasoning_steps} tone="amber" />
            <Stat icon={Network} label="Graph" value={`${result.subgraph.total_nodes} / ${result.subgraph.total_edges}`} hint="nodes / edges" tone="violet" />
            <Stat icon={FileText} label="Passages" value={result.chunks.length} tone="blue" />
            <Stat
              icon={Coins}
              label="Tokens"
              value={result.metrics.total_tokens.toLocaleString()}
              hint={`${result.metrics.calls_count} LLM calls`}
              tone="cyan"
            />
            <Stat icon={Clock} label="Latency" value={formatSeconds(result.latency_seconds)} tone="green" />
          </div>

          {result.metrics.completeness_score > 0 && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Target className="h-3.5 w-3.5 text-cyan-400" aria-hidden />
              Evaluator&apos;s self-assessed completeness:{" "}
              <span className="font-mono font-semibold text-slate-200">{result.metrics.completeness_pct}%</span>
              <span className="text-slate-600">(the agent&apos;s own estimate, not checked against ground truth)</span>
            </div>
          )}

          {/* Evidence */}
          <section ref={evidenceRef} aria-label="Evidence" className="scroll-mt-20">
            <Card padded={false} className="overflow-hidden">
              <div className="flex flex-col gap-3 border-b border-white/10 bg-[#0b1120]/50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
                <h2 className="text-sm font-semibold text-slate-200">Evidence</h2>
                <Segmented<EvidenceTab>
                  label="Evidence views"
                  value={tab}
                  onChange={setTab}
                  options={[
                    { value: "graph", label: "Knowledge graph", icon: Network, count: result.subgraph.total_nodes },
                    { value: "steps", label: "Agent steps", icon: Footprints, count: result.steps.length },
                    { value: "chunks", label: "Passages", icon: FileText, count: result.chunks.length },
                  ]}
                />
              </div>
              <div className="p-4 sm:p-5">
                {tab === "graph" && <KnowledgeGraph subgraph={result.subgraph} />}
                {tab === "steps" && <StepTraces steps={result.steps} hypothesis={result.hypothesis} />}
                {tab === "chunks" && <DocumentChunks chunks={result.chunks} highlightId={highlightChunk} onOpenDocument={openDocument} />}
              </div>
            </Card>
          </section>
        </div>
      )}

      <DocumentModal doc={openDoc} onClose={() => setOpenDoc(null)} />
    </div>
  );
}
