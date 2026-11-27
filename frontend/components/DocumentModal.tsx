"use client";

import React, { useEffect, useRef } from "react";
import { CorpusDocDetail } from "../lib/types";
import { useEscapeKey } from "../lib/hooks";
import { splitInfobox } from "../lib/text";
import { CopyButton } from "./ui";
import { ExternalLink, X } from "lucide-react";

interface DocumentModalProps {
  doc: CorpusDocDetail | null;
  onClose: () => void;
}

/** The raw "[Infobox …]" block is shown as a table above, so only render the body. */
const bodyText = (text: string) => splitInfobox(text).body;

export default function DocumentModal({ doc, onClose }: DocumentModalProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEscapeKey(!!doc, onClose);

  useEffect(() => {
    if (!doc) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    return () => {
      document.body.style.overflow = prev;
    };
  }, [doc]);

  if (!doc) return null;
  const infobox = Object.entries(doc.infobox ?? {});

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm animate-fade-in sm:items-center sm:p-6"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="doc-modal-title"
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-t-2xl border border-white/15 bg-surface shadow-2xl animate-scale-in sm:rounded-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-white/10 px-5 py-4">
          <div className="min-w-0">
            <div className="font-mono text-[11px] text-slate-500">{doc.doc_id}</div>
            <h2 id="doc-modal-title" className="mt-0.5 text-base font-semibold leading-snug text-white">
              {doc.title}
            </h2>
          </div>
          <button ref={closeRef} onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="Close document">
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="space-y-5 overflow-y-auto px-5 py-5">
          {infobox.length > 0 && (
            <section>
              <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Infobox</h3>
              <dl className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-white/10 bg-white/10 sm:grid-cols-2">
                {infobox.map(([k, v]) => (
                  <div key={k} className="flex gap-3 bg-surface px-3 py-2 text-[13px]">
                    <dt className="w-24 shrink-0 text-slate-500">{k}</dt>
                    <dd className="min-w-0 break-words text-slate-200">{v}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          <section>
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Text</h3>
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-300">{bodyText(doc.full_text)}</p>
          </section>
        </div>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 px-5 py-3 text-xs text-slate-500">
          <span>~{doc.approx_tokens.toLocaleString()} tokens</span>
          <div className="flex items-center gap-2">
            <CopyButton text={doc.full_text} label="Copy text" />
            {doc.url && (
              <a
                href={doc.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-white/10 px-3 font-semibold text-cyan-300 hover:bg-cyan-400/10"
              >
                Source
                <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              </a>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
}
