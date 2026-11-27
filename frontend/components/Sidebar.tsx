"use client";

import React from "react";
import { SystemStatus } from "../lib/types";
import { useEscapeKey } from "../lib/hooks";
import { Badge, Skeleton, cx } from "./ui";
import { Cpu, Database, FileText, Network, RotateCcw, X } from "lucide-react";

export interface OrchestratorSettings {
  model: string;
  temperature: number;
  maxHops: number;
  threshold: number;
  tokenBudget: number;
}

export const DEFAULT_SETTINGS: OrchestratorSettings = {
  model: "",
  temperature: 0.1,
  maxHops: 6,
  threshold: 0.85,
  tokenBudget: 16000,
};

interface SidebarProps {
  status: SystemStatus | null;
  statusError: string | null;
  settings: OrchestratorSettings;
  onChange: (s: OrchestratorSettings) => void;
  open: boolean;
  onClose: () => void;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="shrink-0 text-slate-400">{label}</span>
      <span className="min-w-0 truncate text-right font-medium text-slate-200">{children}</span>
    </div>
  );
}

function Slider({
  id,
  label,
  value,
  display,
  hint,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { id: string; label: string; display: string; hint?: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <label htmlFor={id} className="font-medium text-slate-300">
          {label}
        </label>
        <span className="font-mono font-semibold text-cyan-300">{display}</span>
      </div>
      <input id={id} type="range" value={value} className="range" {...props} />
      {hint && <p className="text-[11px] leading-snug text-slate-500">{hint}</p>}
    </div>
  );
}

function SectionLabel({ icon: Icon, children }: { icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
      <Icon className="h-3.5 w-3.5 text-cyan-400" aria-hidden />
      {children}
    </div>
  );
}

export default function Sidebar({ status, statusError, settings, onChange, open, onClose }: SidebarProps) {
  useEscapeKey(open, onClose);
  const set = <K extends keyof OrchestratorSettings>(key: K, value: OrchestratorSettings[K]) =>
    onChange({ ...settings, [key]: value });

  const loading = !status && !statusError;
  const llm = status?.llm;
  const models = llm?.models ?? [];

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className={cx("fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity lg:hidden", open ? "opacity-100" : "pointer-events-none opacity-0")}
        onClick={onClose}
        aria-hidden
      />

      <aside
        aria-label="Settings and system status"
        className={cx(
          "fixed inset-y-0 left-0 z-50 flex w-80 shrink-0 flex-col overflow-y-auto border-r border-white/10 bg-[#0b1120] transition-transform duration-200",
          "lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 shadow-lg shadow-cyan-500/20">
            <Network className="h-5 w-5 text-white" aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-base font-bold tracking-tight text-white">GraphScout</div>
            <div className="text-[11px] font-medium text-slate-500">Agentic GraphRAG</div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden" aria-label="Close settings panel">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* System status */}
        <section className="space-y-3 border-b border-white/10 px-5 py-4">
          <SectionLabel icon={Database}>System</SectionLabel>
          {loading ? (
            <div className="space-y-2.5">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-4 w-3/5" />
            </div>
          ) : statusError ? (
            <Badge tone="red" dot>
              Backend offline
            </Badge>
          ) : (
            status && (
              <>
                <Row label="Graph engine">
                  <Badge tone={status.graph.persistent ? "green" : "amber"} dot>
                    {status.graph.label}
                  </Badge>
                </Row>
                {status.graph.location && <Row label="Host">{status.graph.location}</Row>}
                {status.graph.database && <Row label="Database">{status.graph.database}</Row>}
                <Row label="LLM">
                  {llm ? (
                    <Badge tone={llm.live ? "green" : "amber"} dot>
                      {llm.live ? llm.provider : "Offline simulation"}
                    </Badge>
                  ) : (
                    <span className="text-slate-500">unknown (restart backend)</span>
                  )}
                </Row>
              </>
            )
          )}
          {status && llm && !llm.live && (
            <p className="text-[11px] leading-snug text-amber-300/80">
              No API key found, so answers are canned demo output. Add GROQ_API_KEY or OPENAI_API_KEY to backend/.env.
            </p>
          )}
        </section>

        {/* Orchestrator settings */}
        <section className="space-y-5 border-b border-white/10 px-5 py-4">
          <div className="-mb-1 flex items-center justify-between">
            <SectionLabel icon={Cpu}>Orchestrator</SectionLabel>
            <button
              onClick={() => onChange({ ...DEFAULT_SETTINGS, model: llm?.default_model ?? "" })}
              className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-slate-500 hover:bg-white/5 hover:text-slate-300"
              title="Reset to defaults"
            >
              <RotateCcw className="h-3 w-3" aria-hidden />
              Reset
            </button>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="model" className="text-xs font-medium text-slate-300">
              Model
            </label>
            <select
              id="model"
              value={settings.model}
              onChange={(e) => set("model", e.target.value)}
              disabled={models.length === 0}
              className="field py-1.5 text-xs disabled:opacity-60"
            >
              {models.length === 0 && <option value="">{loading ? "Loading…" : "Unavailable"}</option>}
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                  {m === llm?.default_model ? " (default)" : ""}
                </option>
              ))}
            </select>
          </div>

          <Slider
            id="temperature"
            label="Temperature"
            display={settings.temperature.toFixed(2)}
            min={0}
            max={1}
            step={0.05}
            value={settings.temperature}
            onChange={(e) => set("temperature", parseFloat(e.target.value))}
            hint="Lower values make tool choices more deterministic."
          />
          <Slider
            id="max-hops"
            label="Max reasoning steps"
            display={String(settings.maxHops)}
            min={2}
            max={10}
            step={1}
            value={settings.maxHops}
            onChange={(e) => set("maxHops", parseInt(e.target.value, 10))}
            hint="Upper bound on agent actions before it must answer."
          />
          <Slider
            id="threshold"
            label="Stop at completeness"
            display={`${Math.round(settings.threshold * 100)}%`}
            min={0.5}
            max={1}
            step={0.05}
            value={settings.threshold}
            onChange={(e) => set("threshold", parseFloat(e.target.value))}
            hint="The evaluator agent stops the loop once its score reaches this."
          />

          <div className="space-y-1.5">
            <label htmlFor="budget" className="text-xs font-medium text-slate-300">
              Token budget
            </label>
            <select
              id="budget"
              value={settings.tokenBudget}
              onChange={(e) => set("tokenBudget", parseInt(e.target.value, 10))}
              className="field py-1.5 text-xs"
            >
              <option value={8000}>8,000 · fast</option>
              <option value={16000}>16,000 · balanced</option>
              <option value={32000}>32,000 · thorough</option>
            </select>
          </div>
        </section>

        {/* Data */}
        <section className="space-y-3 px-5 py-4">
          <SectionLabel icon={FileText}>Data</SectionLabel>
          {status ? (
            <>
              <Row label="Corpus">{status.datasets.corpus_documents.toLocaleString()} docs</Row>
              <Row label="Graph entities">{status.graph.indexed_entities.toLocaleString()}</Row>
              <Row label="Relationships">{status.graph.indexed_relations.toLocaleString()}</Row>
              <Row label="Indexed chunks">{status.graph.indexed_chunks.toLocaleString()}</Row>
              <Row label="Eval questions">
                {status.datasets.eval_public_questions} public · {status.datasets.eval_hidden_questions} hidden
              </Row>
            </>
          ) : (
            <span className="text-xs text-slate-500">{loading ? "Loading…" : "Unavailable"}</span>
          )}
        </section>
      </aside>
    </>
  );
}
