"use client";

import React, { useState } from "react";
import { StepTrace } from "../lib/types";
import { Clock, ChevronDown, ChevronRight, CheckCircle2 } from "lucide-react";

interface StepTracesProps {
  steps: StepTrace[];
}

export default function StepTraces({ steps }: StepTracesProps) {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({ 0: true, 1: true });

  const toggleStep = (idx: number) => {
    setExpandedSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const badgeStyles: Record<string, { bg: string; text: string; border: string }> = {
    entity_linking: { bg: "bg-blue-500/15", text: "text-blue-400", border: "border-blue-500/30" },
    graph_traversal: { bg: "bg-purple-500/15", text: "text-purple-400", border: "border-purple-500/30" },
    vector_search: { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30" },
    evaluate_evidence: { bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30" },
    finish: { bg: "bg-cyan-500/15", text: "text-cyan-400", border: "border-cyan-500/30" },
  };

  if (!steps || steps.length === 0) {
    return <p className="text-slate-500 text-sm py-4">No agent decision traces available.</p>;
  }

  return (
    <div className="space-y-3">
      {steps.map((step) => {
        const isExpanded = !!expandedSteps[step.step_index];
        const style = badgeStyles[step.action_taken] || {
          bg: "bg-slate-700/30",
          text: "text-slate-300",
          border: "border-slate-600/30",
        };

        return (
          <div
            key={step.step_index}
            className="border border-white/10 rounded-xl bg-slate-900/40 overflow-hidden transition-all hover:border-cyan-500/30"
          >
            {/* Step Header */}
            <button
              onClick={() => toggleStep(step.step_index)}
              className="w-full px-5 py-3.5 flex items-center justify-between text-left hover:bg-white/[0.02]"
            >
              <div className="flex items-center gap-3">
                <span
                  className={`px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wider border ${style.bg} ${style.text} ${style.border}`}
                >
                  Step {step.step_index}: {step.action_taken.replace("_", " ")}
                </span>
                <span className="text-sm font-semibold text-slate-200 line-clamp-1">
                  {step.reasoning}
                </span>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono text-slate-400 shrink-0">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {step.duration_ms.toFixed(1)}ms
                </span>
                {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </div>
            </button>

            {/* Step Expanded Content */}
            {isExpanded && (
              <div className="px-5 py-4 border-t border-white/10 bg-slate-950/40 text-xs space-y-3">
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                    Orchestrator Reasoning Narrative
                  </div>
                  <p className="text-slate-300 leading-relaxed font-sans">{step.reasoning}</p>
                </div>

                {step.tool_outputs_summary && (
                  <div>
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                      Tool Execution Summary
                    </div>
                    <div className="font-mono text-slate-300 bg-slate-900/80 p-2.5 rounded border border-white/5 whitespace-pre-wrap">
                      {step.tool_outputs_summary}
                    </div>
                  </div>
                )}

                {step.entities_discovered && step.entities_discovered.length > 0 && (
                  <div>
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                      Discovered Entities
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {step.entities_discovered.map((ent, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded text-[11px] font-semibold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20"
                        >
                          🔗 {ent}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
