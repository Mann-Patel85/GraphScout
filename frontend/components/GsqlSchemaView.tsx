"use client";

import React, { useState, useEffect } from "react";
import { GsqlSchema } from "../lib/types";
import { getGsqlSchema } from "../lib/api";
import { Layers, Copy, Check, FileCode, CheckCircle2 } from "lucide-react";

export default function GsqlSchemaView() {
  const [schema, setSchema] = useState<GsqlSchema | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getGsqlSchema().then(setSchema).catch(console.error);
  }, []);

  const copyCode = () => {
    if (!schema?.gsql_code) return;
    navigator.clipboard.writeText(schema.gsql_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
          TigerGraph GSQL Schema Blueprint <Layers className="w-5 h-5 text-cyan-400" />
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Graph model architecture defining vertex types, edges, and installed pattern traversal queries for hybrid vector-relational retrieval.
        </p>
      </div>

      {/* Vertex Cards */}
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3">
          Knowledge Graph Vertex Types
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {schema?.vertices.map((v) => (
            <div
              key={v.name}
              className="bg-[#0f172a]/70 border border-white/10 rounded-xl p-4 space-y-2"
            >
              <div className="text-sm font-bold text-cyan-400 flex items-center justify-between">
                <span>{v.name}</span>
                <span className="text-[10px] font-mono text-slate-500 uppercase">{v.primary_id}</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{v.description}</p>
              <div className="pt-2 border-t border-white/5 flex flex-wrap gap-1">
                {v.attributes.map((attr) => (
                  <span
                    key={attr}
                    className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono"
                  >
                    {attr}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Edges & Relations */}
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3">
          Edge Connections &amp; Semantics
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {schema?.edges.map((e) => (
            <div
              key={e.name}
              className="bg-[#0f172a]/70 border border-white/10 rounded-xl p-3.5 space-y-1.5 text-xs"
            >
              <div className="flex items-center justify-between font-mono font-bold text-amber-400">
                <span>{e.name}</span>
                <span className="text-[10px] text-slate-500">{e.type}</span>
              </div>
              <div className="text-slate-300 font-semibold">
                {e.from} &rarr; {e.to}
              </div>
              <div className="text-slate-400 text-[11px]">{e.description}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Installed Queries */}
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3">
          Installed TigerGraph GSQL Queries
        </h3>
        <div className="space-y-2">
          {schema?.installed_queries.map((q) => (
            <div
              key={q.name}
              className="bg-[#0f172a]/70 border border-white/10 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
            >
              <div>
                <span className="font-mono font-bold text-emerald-400 text-sm">{q.name}</span>
                <span className="text-slate-400 font-mono text-[11px] ml-2">({q.parameters})</span>
                <p className="text-slate-300 text-xs mt-1">{q.description}</p>
              </div>
              <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold uppercase shrink-0">
                Compiled GSQL
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* GSQL Code Block */}
      <div className="bg-[#0f172a]/70 border border-white/10 rounded-2xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <FileCode className="w-4 h-4 text-cyan-400" />
            <span>schema/graph_schema.gsql</span>
          </span>
          <button
            onClick={copyCode}
            className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white transition-all border border-white/10"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? "Copied" : "Copy GSQL"}</span>
          </button>
        </div>

        <pre className="font-mono text-xs text-slate-300 bg-slate-950 p-4 rounded-xl border border-white/5 overflow-x-auto max-h-96 leading-relaxed">
          <code>{schema?.gsql_code || "// Loading schema code..."}</code>
        </pre>
      </div>
    </div>
  );
}
