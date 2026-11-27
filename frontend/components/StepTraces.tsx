"use client";

import React, { useState } from "react";
import { StepTrace } from "../lib/types";
import { formatMs } from "../lib/hooks";
import { Badge, EmptyState, cx } from "./ui";
import { CheckCircle2, ChevronDown, Filter, Footprints, Link2, Network, Scale, Search, type LucideIcon } from "lucide-react";

interface StepTracesProps {
  steps: StepTrace[];
  hypothesis?: string;
}

const ACTIONS: Record<string, { label: string; icon: LucideIcon; tone: "blue" | "violet" | "green" | "amber" | "cyan"; ring: string }> = {
  entity_linking: { label: "Link entities", icon: Link2, tone: "blue", ring: "border-blue-400/40 text-blue-300" },
  graph_traversal: { label: "Traverse graph", icon: Network, tone: "violet", ring: "border-violet-400/40 text-violet-300" },
  vector_search: { label: "Search passages", icon: Search, tone: "green", ring: "border-emerald-400/40 text-emerald-300" },
  find_events: { label: "Filter events", icon: Filter, tone: "cyan", ring: "border-cyan-400/40 text-cyan-300" },
  evaluate_evidence: { label: "Evaluate evidence", icon: Scale, tone: "amber", ring: "border-amber-400/40 text-amber-300" },
  finish: { label: "Finish", icon: CheckCircle2, tone: "cyan", ring: "border-cyan-400/40 text-cyan-300" },
};

/** "sport: Athletics", "year: 2008", "sort: competitors desc" from a find_events filter. */
function filterChips(filter: Record<string, unknown> | undefined): string[] {
  if (!filter) return [];
  const chips = Object.entries(filter)
    .filter(([k, v]) => v !== null && v !== undefined && v !== "" && !["descending", "limit", "sort_by"].includes(k))
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`);
  if (filter.sort_by) chips.push(`sort: ${filter.sort_by} ${filter.descending === false ? "asc" : "desc"}`);
  return chips;
}

function Chips({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((it, i) => (
          <span key={i} className="rounded-md border border-white/10 bg-slate-800/70 px-2 py-0.5 text-[12px] text-slate-200">
            {it}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function StepTraces({ steps, hypothesis }: StepTracesProps) {
  const [open, setOpen] = useState<Set<number>>(() => new Set(steps.slice(0, 1).map((s) => s.step_index)));

  if (steps.length === 0) {
    return <EmptyState icon={Footprints} title="No agent steps recorded" />;
  }

  const allOpen = open.size === steps.length;
  const toggle = (i: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-slate-500">Each step is a decision by the orchestrator LLM, followed by the tool it chose.</p>
        <button
          onClick={() => setOpen(allOpen ? new Set() : new Set(steps.map((s) => s.step_index)))}
          className="shrink-0 rounded px-2 py-1 text-xs font-medium text-slate-400 hover:bg-white/5 hover:text-slate-200"
        >
          {allOpen ? "Collapse all" : "Expand all"}
        </button>
      </div>

      <ol className="relative space-y-3 before:absolute before:bottom-4 before:left-[15px] before:top-4 before:w-px before:bg-white/10">
        {steps.map((step) => {
          const meta = ACTIONS[step.action_taken] ?? { label: step.action_taken, icon: Footprints, tone: "cyan" as const, ring: "border-white/20 text-slate-300" };
          const Icon = meta.icon;
          const isOpen = open.has(step.step_index);
          const inputs = step.tool_inputs ?? {};
          const queries = step.action_taken === "vector_search" ? (inputs.search_queries ?? []) : [];
          const seeds = step.action_taken === "graph_traversal" ? (inputs.seed_entities ?? []) : [];
          const filters = step.action_taken === "find_events" ? filterChips(inputs.event_filter) : [];
          const skipped = step.reasoning.startsWith("[Repeated step skipped]");

          return (
            <li key={step.step_index} className="relative pl-11">
              <span className={cx("absolute left-0 top-2 flex h-8 w-8 items-center justify-center rounded-full border bg-[#0b1120]", meta.ring)}>
                <Icon className="h-4 w-4" aria-hidden />
              </span>

              <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-900/40 transition-colors hover:border-white/20">
                <button
                  onClick={() => toggle(step.step_index)}
                  aria-expanded={isOpen}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left"
                >
                  <span className="shrink-0 font-mono text-[11px] text-slate-500">#{step.step_index}</span>
                  <Badge tone={meta.tone}>{meta.label}</Badge>
                  <span className="min-w-0 flex-1 truncate text-sm text-slate-300">{step.tool_outputs_summary || step.reasoning}</span>
                  <span className="hidden shrink-0 font-mono text-[11px] text-slate-500 sm:inline">{formatMs(step.duration_ms)}</span>
                  <ChevronDown className={cx("h-4 w-4 shrink-0 text-slate-500 transition-transform", isOpen && "rotate-180")} aria-hidden />
                </button>

                {isOpen && (
                  <div className="space-y-3 border-t border-white/10 bg-slate-950/40 px-4 py-3.5 text-sm animate-fade-in">
                    <div>
                      <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Why</div>
                      <p className={cx("leading-relaxed", skipped ? "text-amber-200/90" : "text-slate-300")}>{step.reasoning}</p>
                    </div>
                    <Chips label="Search queries" items={queries} />
                    <Chips label="Event filters" items={filters} />
                    <Chips label={`Seed entities${inputs.max_hops ? ` · ${inputs.max_hops} hops` : ""}`} items={seeds} />
                    {step.tool_outputs_summary && (
                      <div>
                        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Result</div>
                        <p className="rounded-md border border-white/5 bg-slate-900/80 px-3 py-2 font-mono text-[12px] text-slate-300">{step.tool_outputs_summary}</p>
                      </div>
                    )}
                    {step.entities_discovered.length > 0 && (
                      <Chips
                        label={`Entities found (${step.entities_discovered.length})`}
                        items={step.entities_discovered.slice(0, 20).concat(step.entities_discovered.length > 20 ? [`+${step.entities_discovered.length - 20} more`] : [])}
                      />
                    )}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {hypothesis && !hypothesis.startsWith("Initial hypothesis") && (
        <div className="rounded-xl border border-white/10 bg-slate-900/40 p-4">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Final working hypothesis</div>
          <p className="text-sm leading-relaxed text-slate-300">{hypothesis}</p>
        </div>
      )}
    </div>
  );
}
