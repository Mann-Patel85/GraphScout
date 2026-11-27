"use client";

import React, { useEffect, useState } from "react";
import { GraphSchema } from "../lib/types";
import { getGraphSchema } from "../lib/api";
import { Callout, Card, CopyButton, PageHeader, SectionTitle, Skeleton } from "./ui";
import { ArrowRight, Boxes, FileCode, GitBranch, Layers, Terminal } from "lucide-react";

export default function SchemaView() {
  const [schema, setSchema] = useState<GraphSchema | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getGraphSchema()
      .then(setSchema)
      .catch((err) => setError((err as Error).message));
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader
        icon={Layers}
        title="Graph Schema"
        description="The graph data model: node and relationship types, plus the Cypher queries the agent's graph tool runs on Neo4j. Without a Neo4j connection, the same model runs in an in-memory engine."
      />

      {error && <Callout tone="red">{error}</Callout>}

      {!schema && !error && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-3 rounded-xl border border-white/10 bg-surface/50 p-4">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-3/4" />
            </div>
          ))}
        </div>
      )}

      {schema && (
        <>
          <section>
            <SectionTitle icon={Boxes}>Node labels</SectionTitle>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {schema.nodes.map((v) => (
                <Card key={v.name} className="space-y-2.5">
                  <div className="flex items-baseline justify-between gap-2">
                    <h3 className="font-mono text-sm font-semibold text-cyan-300">{v.name}</h3>
                    <span className="truncate font-mono text-[10px] text-slate-500">key: {v.key}</span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-400">{v.description}</p>
                  <div className="flex flex-wrap gap-1 border-t border-white/5 pt-2.5">
                    {v.attributes.map((a) => (
                      <span key={a} className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
                        {a}
                      </span>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          </section>

          <section>
            <SectionTitle icon={GitBranch}>Relationship types</SectionTitle>
            <Card padded={false} className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-[11px] uppercase tracking-wider text-slate-500">
                    <th className="px-4 py-3 font-semibold">Relationship</th>
                    <th className="px-4 py-3 font-semibold">Connects</th>
                    <th className="px-4 py-3 font-semibold">Meaning</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {schema.relationships.map((e) => (
                    <tr key={e.name}>
                      <td className="px-4 py-3 font-mono text-[13px] font-semibold text-amber-300">
                        {e.name}
                        <span className="ml-2 font-sans text-[10px] font-normal text-slate-500">{e.type.toLowerCase()}</span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-slate-300">
                        <span className="inline-flex items-center gap-1.5 font-mono text-[12px]">
                          {e.from} <ArrowRight className="h-3 w-3 text-slate-500" aria-hidden /> {e.to}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400">{e.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </section>

          <section>
            <SectionTitle icon={Terminal}>Cypher queries</SectionTitle>
            <div className="grid gap-3 lg:grid-cols-3">
              {schema.queries.map((q) => (
                <Card key={q.name} className="space-y-2">
                  <h3 className="font-mono text-sm font-semibold text-emerald-300">{q.name}</h3>
                  <code className="block break-words font-mono text-[11px] text-slate-500">({q.parameters})</code>
                  <p className="text-xs leading-relaxed text-slate-400">{q.description}</p>
                </Card>
              ))}
            </div>
          </section>

          <section>
            <SectionTitle icon={FileCode} right={<CopyButton text={schema.code} label="Copy Cypher" />}>
              <span className="font-mono normal-case tracking-normal">{schema.file_path}</span>
            </SectionTitle>
            <pre className="max-h-[32rem] overflow-auto rounded-xl border border-white/10 bg-[#080d1a] p-4 font-mono text-[12px] leading-relaxed text-slate-300">
              <code>{schema.code}</code>
            </pre>
          </section>
        </>
      )}
    </div>
  );
}
