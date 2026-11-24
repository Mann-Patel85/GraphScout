"use client";

import React from "react";
import { CorpusDocDetail } from "../lib/types";
import { X, ExternalLink, Hash, BookOpen } from "lucide-react";

interface DocumentModalProps {
  doc: CorpusDocDetail | null;
  onClose: () => void;
}

export default function DocumentModal({ doc, onClose }: DocumentModalProps) {
  if (!doc) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-3xl max-h-[85vh] bg-[#0f172a] border border-white/15 rounded-2xl flex flex-col overflow-hidden shadow-2xl">
        {/* Modal Header */}
        <div className="p-5 border-b border-white/10 flex items-center justify-between bg-[#0b1120]/80">
          <div>
            <div className="font-mono text-xs text-cyan-400 font-bold">{doc.doc_id}</div>
            <h3 className="text-base font-bold text-slate-100">{doc.title}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          {/* Infobox Attributes Table */}
          {doc.infobox && Object.keys(doc.infobox).length > 0 && (
            <div className="p-4 rounded-xl bg-cyan-500/5 border border-cyan-500/20 space-y-2">
              <div className="text-[11px] font-bold uppercase tracking-wider text-cyan-400">
                Extracted Infobox Attributes
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {Object.entries(doc.infobox).map(([k, v]) => (
                  <div key={k}>
                    <span className="text-slate-400 font-medium">{k}:</span>{" "}
                    <strong className="text-slate-200">{v}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Meta bar */}
          <div className="flex items-center justify-between text-slate-400 pt-1">
            <span className="flex items-center gap-1.5">
              <Hash className="w-3.5 h-3.5 text-cyan-400" />
              <span>Tokens: ~{doc.approx_tokens.toLocaleString()}</span>
            </span>
            {doc.url && (
              <a
                href={doc.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-cyan-400 hover:underline"
              >
                <span>Wikipedia Source</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>

          {/* Document Content */}
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Document Text Segment
            </div>
            <div className="font-mono text-slate-300 bg-slate-950 p-4 rounded-xl border border-white/5 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto text-xs">
              {doc.full_text}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
