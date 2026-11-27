"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { DocumentChunk } from "../lib/types";
import { KEY_FIELDS, splitInfobox } from "../lib/text";
import { EmptyState, cx } from "./ui";
import { ChevronDown, ExternalLink, FileText } from "lucide-react";

interface DocumentChunksProps {
  chunks: DocumentChunk[];
  highlightId?: string | null;
  onOpenDocument?: (docId: string) => void;
}

const PREVIEW_CHARS = 360;

function ChunkCard({
  chunk,
  highlighted,
  onOpenDocument,
}: {
  chunk: DocumentChunk;
  highlighted: boolean;
  onOpenDocument?: (docId: string) => void;
}) {
  const ref = useRef<HTMLElement>(null);
  const [expanded, setExpanded] = useState(highlighted);
  const { fields, body } = useMemo(() => splitInfobox(chunk.text_content), [chunk.text_content]);
  const shownFields = expanded ? fields : fields.filter(([k]) => KEY_FIELDS.includes(k));
  const long = body.length > PREVIEW_CHARS || shownFields.length < fields.length;
  const text = expanded || body.length <= PREVIEW_CHARS ? body : `${body.slice(0, PREVIEW_CHARS).trimEnd()}…`;

  useEffect(() => {
    if (highlighted) {
      setExpanded(true);
      ref.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlighted]);

  return (
    <article
      ref={ref}
      className={cx(
        "rounded-xl border bg-slate-900/40 p-4 transition-colors",
        highlighted ? "border-cyan-400/60 ring-2 ring-cyan-400/20" : "border-white/10 hover:border-white/20"
      )}
    >
      <header className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold leading-snug text-slate-100">{chunk.section_header || "Passage"}</h3>
          <div className="mt-0.5 font-mono text-[11px] text-slate-500">{chunk.chunk_id}</div>
        </div>
        <div className="flex items-center gap-2">
          {chunk.score > 0 && (
            <span className="rounded-md bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-slate-300" title="Retrieval score from the tool that found this passage">
              score {chunk.score.toFixed(2)}
            </span>
          )}
          {chunk.doc_id && onOpenDocument && (
            <button
              onClick={() => onOpenDocument(chunk.doc_id!)}
              className="flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium text-cyan-300 hover:bg-cyan-400/10"
            >
              Full document
              <ExternalLink className="h-3 w-3" aria-hidden />
            </button>
          )}
        </div>
      </header>

      {shownFields.length > 0 && (
        <dl className="mb-3 grid grid-cols-1 gap-x-6 gap-y-1 rounded-lg border border-white/5 bg-slate-950/40 px-3 py-2 text-[12px] sm:grid-cols-2">
          {shownFields.map(([k, v]) => (
            <div key={k} className="flex min-w-0 gap-2">
              <dt className="w-20 shrink-0 text-slate-500">{k}</dt>
              <dd className={cx("min-w-0 break-words", k === "gold" ? "font-medium text-amber-200" : "text-slate-200")}>{v}</dd>
            </div>
          ))}
        </dl>
      )}

      {text && <p className="whitespace-pre-line text-[13px] leading-relaxed text-slate-300">{text}</p>}

      {long && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-slate-200"
          aria-expanded={expanded}
        >
          {expanded ? "Show less" : "Show more"}
          <ChevronDown className={cx("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")} aria-hidden />
        </button>
      )}
    </article>
  );
}

export default function DocumentChunks({ chunks, highlightId, onOpenDocument }: DocumentChunksProps) {
  if (chunks.length === 0) {
    return (
      <EmptyState icon={FileText} title="No passages retrieved">
        The agent didn&apos;t run a passage search or provenance lookup in this investigation.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-3">
      {chunks.map((c) => (
        <ChunkCard key={c.chunk_id} chunk={c} highlighted={c.chunk_id === highlightId} onOpenDocument={onOpenDocument} />
      ))}
    </div>
  );
}
