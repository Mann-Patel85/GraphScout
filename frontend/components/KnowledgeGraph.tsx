"use client";

import React, { useEffect, useRef, useState } from "react";
import { SubgraphData, GraphNode } from "../lib/types";
import { ZoomIn, ZoomOut, Maximize2, Info, Activity } from "lucide-react";

interface KnowledgeGraphProps {
  subgraph: SubgraphData;
}

export default function KnowledgeGraph({ subgraph }: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<any>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    if (!containerRef.current || !subgraph.nodes || subgraph.nodes.length === 0) return;

    let isMounted = true;

    // Dynamically import vis-network to avoid SSR window errors
    Promise.all([
      import("vis-network/standalone/umd/vis-network.min.js"),
    ]).then(([visModule]) => {
      if (!isMounted || !containerRef.current) return;
      const vis = (visModule as any).default || visModule;

      const colorMap: Record<string, { bg: string; border: string; highlight: string }> = {
        Organization: { bg: "#00d2ff", border: "#38bdf8", highlight: "#bae6fd" },
        Event: { bg: "#f59e0b", border: "#fbbf24", highlight: "#fef3c7" },
        Person: { bg: "#10b981", border: "#34d399", highlight: "#d1fae5" },
        Athlete: { bg: "#10b981", border: "#34d399", highlight: "#d1fae5" },
        Sport: { bg: "#3b82f6", border: "#60a5fa", highlight: "#dbeafe" },
        Venue: { bg: "#a855f7", border: "#c084fc", highlight: "#f3e8ff" },
        Document: { bg: "#6366f1", border: "#818cf8", highlight: "#e0e7ff" },
        Chunk: { bg: "#64748b", border: "#94a3b8", highlight: "#f1f5f9" },
      };

      const nodes = subgraph.nodes.map((n) => {
        const col = colorMap[n.entity_type] || { bg: "#38bdf8", border: "#0284c7", highlight: "#bae6fd" };
        return {
          id: n.id,
          label: n.label,
          title: `${n.label} (${n.entity_type})`,
          shape: "box",
          margin: 10,
          font: { color: "#ffffff", size: 13, face: "sans-serif" },
          color: {
            background: col.bg,
            border: col.border,
            highlight: { background: col.highlight, border: "#ffffff" },
          },
          shadow: { enabled: true, color: "rgba(0,0,0,0.6)", size: 8, x: 2, y: 2 },
          data: n,
        };
      });

      const edges = subgraph.edges.map((e, idx) => ({
        id: `e-${idx}`,
        from: e.from,
        to: e.to,
        label: e.label || "",
        arrows: "to",
        font: { color: "#94a3b8", size: 10, align: "middle" },
        color: { color: "rgba(148, 163, 184, 0.4)", highlight: "#00d2ff" },
        smooth: { type: "continuous" },
      }));

      const data = {
        nodes: new vis.DataSet(nodes),
        edges: new vis.DataSet(edges),
      };

      const options = {
        physics: {
          enabled: true,
          barnesHut: {
            gravitationalConstant: -2800,
            centralGravity: 0.25,
            springLength: 130,
            springConstant: 0.04,
          },
          stabilization: { iterations: 120 },
        },
        interaction: {
          hover: true,
          zoomView: true,
          dragView: true,
          navigationButtons: false,
        },
      };

      if (networkRef.current) {
        networkRef.current.destroy();
      }

      const network = new vis.Network(containerRef.current, data, options);
      networkRef.current = network;

      network.on("click", (params: any) => {
        if (params.nodes && params.nodes.length > 0) {
          const clickedId = params.nodes[0];
          const nodeObj = subgraph.nodes.find((n) => n.id === clickedId) || null;
          setSelectedNode(nodeObj);
        } else {
          setSelectedNode(null);
        }
      });

      setTimeout(() => {
        network.fit({ animation: { duration: 600, easingFunction: "easeInOutQuad" } });
      }, 300);
    });

    return () => {
      isMounted = false;
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, [subgraph]);

  const handleFit = () => networkRef.current?.fit({ animation: true });
  const handleZoomIn = () => {
    if (!networkRef.current) return;
    const scale = networkRef.current.getScale();
    networkRef.current.moveTo({ scale: scale * 1.3, animation: true });
  };
  const handleZoomOut = () => {
    if (!networkRef.current) return;
    const scale = networkRef.current.getScale();
    networkRef.current.moveTo({ scale: scale * 0.7, animation: true });
  };

  if (!subgraph.nodes || subgraph.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-slate-500 text-sm">
        <Activity className="w-8 h-8 mb-2 opacity-50" />
        <p>No knowledge graph entities discovered for this query.</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Legend & Controls Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-3 px-1">
        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#00d2ff]" /> Organization</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]" /> Event / Date</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#10b981]" /> Athlete / Person</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#a855f7]" /> Venue</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#3b82f6]" /> Sport</div>
        </div>

        <div className="flex items-center gap-1.5">
          <button onClick={handleZoomIn} title="Zoom In" className="p-1.5 rounded bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button onClick={handleZoomOut} title="Zoom Out" className="p-1.5 rounded bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700">
            <ZoomOut className="w-4 h-4" />
          </button>
          <button onClick={handleFit} title="Fit View" className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 text-xs font-semibold">
            <Maximize2 className="w-3.5 h-3.5" />
            <span>Fit</span>
          </button>
        </div>
      </div>

      {/* Network Canvas */}
      <div
        ref={containerRef}
        className="w-full h-[520px] bg-[#080d1a] border border-white/10 rounded-xl overflow-hidden relative shadow-inner"
      />

      {/* Node Details Inspection Panel */}
      {selectedNode && (
        <div className="absolute top-16 right-4 w-72 bg-slate-900/90 border border-cyan-400/40 rounded-xl p-4 shadow-2xl backdrop-blur-md text-xs space-y-2 animate-in fade-in zoom-in-95">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <span className="font-bold text-cyan-400 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5" /> Entity Inspection
            </span>
            <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-white text-sm">&times;</button>
          </div>
          <div>
            <div className="text-slate-400">Canonical Name</div>
            <div className="font-semibold text-slate-100 text-sm">{selectedNode.label}</div>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Type</span>
            <span className="font-bold text-amber-400">{selectedNode.entity_type}</span>
          </div>
          {selectedNode.hops !== undefined && (
            <div className="flex justify-between">
              <span className="text-slate-400">Traversal Hops</span>
              <span className="font-mono text-slate-200">{selectedNode.hops}</span>
            </div>
          )}
          {selectedNode.aliases && selectedNode.aliases.length > 0 && (
            <div>
              <div className="text-slate-400 mb-1">Aliases</div>
              <div className="flex flex-wrap gap-1">
                {selectedNode.aliases.map((a, i) => (
                  <span key={i} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">{a}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
