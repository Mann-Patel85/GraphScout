"use client";

import React from "react";
import { DocumentChunk } from "../lib/types";
import { FileText, Tag, Hash } from "lucide-react";

interface DocumentChunksProps {
  chunks: DocumentChunk[];
}

export default function DocumentChunks({ chunks }: DocumentChunksProps) {
  if (!chunks || chunks.length === 0) {
    return <p className="text-slate-500 text-sm py-4">No textual vector chunks retrieved.</p>;
  }

  return (
    <div className="space-y-3">
      {chunks.map((chk, i) => (
        <div
          key={chk.chunk_id || i}
          className="border border-white/10 rounded-xl bg-slate-900/40 p-4 space-y-2 hover:border-cyan-500/30 transition-all"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-bold text-cyan-400 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" />
              {chk.chunk_id} &bull; {chk.section_header || "Passage Segment"}
            </span>
            <div className="flex items-center gap-3 text-xs">
              <span className="font-semibold text-emerald-400">Relevance: {(chk.score || 0.85).toFixed(2)}</span>
              <span className="text-slate-400">~{chk.token_count || 120} tokens</span>
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-sans">{chk.text_content}</p>

          {chk.associated_entities && chk.associated_entities.length > 0 && (
            <div className="flex items-center gap-1.5 pt-1 text-[11px] text-slate-400">
              <Tag className="w-3 h-3 text-cyan-400" />
              <span>Mentions:</span>
              <div className="flex flex-wrap gap-1">
                {chk.associated_entities.map((e, idx) => (
                  <span key={idx} className="text-slate-300 font-semibold">{e}{idx < chk.associated_entities.length - 1 ? "," : ""}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
