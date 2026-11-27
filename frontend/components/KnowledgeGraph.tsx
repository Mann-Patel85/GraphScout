"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { GraphNode, SubgraphData } from "../lib/types";
import { Maximize2, MousePointerClick, Network, X, ZoomIn, ZoomOut } from "lucide-react";
import { EmptyState } from "./ui";

interface KnowledgeGraphProps {
  subgraph: SubgraphData;
}

const TYPE_COLORS: Record<string, string> = {
  OlympicEvent: "#f59e0b",
  Event: "#f59e0b",
  OlympicGames: "#3b82f6",
  Venue: "#a855f7",
  Athlete: "#10b981",
  Person: "#10b981",
  Organization: "#22d3ee",
  Document: "#6366f1",
};
const FALLBACK_COLOR = "#64748b";

const TYPE_LABELS: Record<string, string> = {
  OlympicEvent: "Event",
  OlympicGames: "Games",
};

const colorFor = (type: string) => TYPE_COLORS[type] ?? FALLBACK_COLOR;
const truncate = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

export default function KnowledgeGraph({ subgraph }: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const networkRef = useRef<any>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [ready, setReady] = useState(false);

  const nodeById = useMemo(() => new Map(subgraph.nodes.map((n) => [n.id, n])), [subgraph]);
  const presentTypes = useMemo(() => {
    const counts = new Map<string, number>();
    subgraph.nodes.forEach((n) => counts.set(n.entity_type, (counts.get(n.entity_type) ?? 0) + 1));
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [subgraph]);

  const connections = useMemo(() => {
    if (!selected) return [];
    return subgraph.edges
      .filter((e) => e.from === selected.id || e.to === selected.id)
      .map((e) => {
        const otherId = e.from === selected.id ? e.to : e.from;
        return { relation: e.relation_type, outgoing: e.from === selected.id, other: nodeById.get(otherId), otherId };
      });
  }, [selected, subgraph, nodeById]);

  useEffect(() => {
    if (!containerRef.current || subgraph.nodes.length === 0) return;
    let cancelled = false;
    setReady(false);
    setSelected(null);

    import("vis-network/standalone/umd/vis-network.min.js").then((visModule) => {
      if (cancelled || !containerRef.current) return;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const vis = (visModule as any).default || visModule;
      const degree = new Map<string, number>();
      subgraph.edges.forEach((e) => {
        degree.set(e.from, (degree.get(e.from) ?? 0) + 1);
        degree.set(e.to, (degree.get(e.to) ?? 0) + 1);
      });

      const nodes = subgraph.nodes.map((n) => {
        const color = colorFor(n.entity_type);
        const isSeed = (n.hops ?? 1) === 0;
        return {
          id: n.id,
          label: truncate(n.label, 28),
          title: `${n.label}\n${TYPE_LABELS[n.entity_type] ?? n.entity_type}`,
          shape: "dot",
          size: isSeed ? 20 : 9 + Math.min(degree.get(n.id) ?? 0, 10),
          borderWidth: isSeed ? 3 : 1.5,
          color: {
            background: color,
            border: isSeed ? "#ffffff" : color,
            highlight: { background: color, border: "#ffffff" },
            hover: { background: color, border: "#e2e8f0" },
          },
          font: { color: "#cbd5e1", size: isSeed ? 13 : 11, face: "Inter, system-ui, sans-serif", strokeWidth: 3, strokeColor: "#080d1a" },
        };
      });

      const edges = subgraph.edges.map((e, i) => ({
        id: `e-${i}`,
        from: e.from,
        to: e.to,
        title: e.relation_type,
        arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        color: { color: "rgba(148,163,184,0.25)", highlight: "#22d3ee", hover: "rgba(148,163,184,0.6)" },
        width: 1,
        selectionWidth: 1.5,
        smooth: { enabled: true, type: "continuous", roundness: 0.3 },
      }));

      networkRef.current?.destroy();
      const network = new vis.Network(
        containerRef.current,
        { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) },
        {
          physics: {
            solver: "forceAtlas2Based",
            forceAtlas2Based: { gravitationalConstant: -45, springLength: 90, avoidOverlap: 0.4 },
            stabilization: { iterations: 250, fit: true },
          },
          interaction: { hover: true, tooltipDelay: 150, hideEdgesOnDrag: true },
          layout: { improvedLayout: subgraph.nodes.length < 150 },
        }
      );
      networkRef.current = network;

      network.once("stabilizationIterationsDone", () => {
        network.setOptions({ physics: false }); // stop the jitter once laid out
        network.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });
        if (!cancelled) setReady(true);
      });
      network.on("click", (params: { nodes: string[] }) => {
        setSelected(params.nodes.length ? (nodeById.get(params.nodes[0]) ?? null) : null);
      });
    });

    return () => {
      cancelled = true;
      networkRef.current?.destroy();
      networkRef.current = null;
    };
  }, [subgraph, nodeById]);

  const zoom = (factor: number) => {
    const net = networkRef.current;
    if (net) net.moveTo({ scale: net.getScale() * factor, animation: { duration: 200 } });
  };

  const focusNode = (id: string) => {
    const net = networkRef.current;
    if (!net) return;
    net.selectNodes([id]);
    net.focus(id, { scale: 1.2, animation: { duration: 400 } });
    setSelected(nodeById.get(id) ?? null);
  };

  if (subgraph.nodes.length === 0) {
    return (
      <EmptyState icon={Network} title="No graph entities for this run">
        The agent answered without traversing the graph, or the entities it looked for weren&apos;t found. Check the Agent steps tab.
      </EmptyState>
    );
  }

  const ctrl = "rounded-md border border-white/10 bg-slate-900/90 p-1.5 text-slate-300 backdrop-blur hover:bg-slate-800 hover:text-white";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-400" aria-label="Legend">
          {presentTypes.map(([type, count]) => (
            <li key={type} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colorFor(type) }} aria-hidden />
              {TYPE_LABELS[type] ?? type}
              <span className="text-slate-600">{count}</span>
            </li>
          ))}
          <li className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full border-2 border-white bg-slate-600" aria-hidden />
            Starting entity
          </li>
        </ul>
        <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
          <MousePointerClick className="h-3.5 w-3.5" aria-hidden />
          Click a node to inspect · scroll to zoom
        </span>
      </div>

      <div className="relative overflow-hidden rounded-xl border border-white/10 bg-[#080d1a]">
        <div ref={containerRef} className="h-[420px] w-full sm:h-[540px]" role="img" aria-label={`Knowledge graph with ${subgraph.total_nodes} nodes and ${subgraph.total_edges} edges`} />

        {!ready && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-500">Laying out graph…</div>
        )}

        <div className="absolute left-3 top-3 flex flex-col gap-1">
          <button onClick={() => zoom(1.3)} className={ctrl} aria-label="Zoom in">
            <ZoomIn className="h-4 w-4" />
          </button>
          <button onClick={() => zoom(0.75)} className={ctrl} aria-label="Zoom out">
            <ZoomOut className="h-4 w-4" />
          </button>
          <button onClick={() => networkRef.current?.fit({ animation: { duration: 300 } })} className={ctrl} aria-label="Fit graph to view">
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>

        {selected && (
          <aside className="absolute inset-x-3 bottom-3 max-h-[70%] overflow-y-auto rounded-xl border border-white/15 bg-slate-950/95 p-4 text-xs shadow-2xl backdrop-blur animate-scale-in sm:inset-x-auto sm:right-3 sm:top-3 sm:bottom-auto sm:w-80">
            <div className="mb-3 flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider" style={{ color: colorFor(selected.entity_type) }}>
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: colorFor(selected.entity_type) }} aria-hidden />
                  {TYPE_LABELS[selected.entity_type] ?? selected.entity_type}
                  {selected.hops !== undefined && <span className="font-normal normal-case text-slate-500">· {selected.hops} hop{selected.hops === 1 ? "" : "s"} from start</span>}
                </div>
                <div className="mt-1 text-sm font-semibold leading-snug text-white">{selected.label}</div>
              </div>
              <button onClick={() => setSelected(null)} className="rounded p-1 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="Close details">
                <X className="h-4 w-4" />
              </button>
            </div>

            {selected.description && <p className="mb-3 leading-relaxed text-slate-300">{selected.description}</p>}

            {connections.length > 0 && (
              <div>
                <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Connections ({connections.length})
                </div>
                <ul className="space-y-1">
                  {connections.slice(0, 12).map((c, i) => (
                    <li key={i}>
                      <button
                        onClick={() => focusNode(c.otherId)}
                        className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-white/5"
                      >
                        <span className="shrink-0 font-mono text-[10px] text-slate-500">
                          {c.outgoing ? "→" : "←"} {c.relation}
                        </span>
                        <span className="truncate text-slate-200">{c.other?.label ?? c.otherId}</span>
                      </button>
                    </li>
                  ))}
                  {connections.length > 12 && <li className="px-1.5 text-slate-500">+{connections.length - 12} more</li>}
                </ul>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}
