"use client";

import React, { useEffect, useRef, useState } from "react";
import { CorpusDocDetail, CorpusDocSummary } from "../lib/types";
import { getCorpusDocDetail, getCorpusDocuments } from "../lib/api";
import { splitInfobox } from "../lib/text";
import DocumentModal from "./DocumentModal";
import { Button, Callout, Card, EmptyState, PageHeader, Skeleton } from "./ui";
import { BookOpen, Loader2, Search, SearchX, X } from "lucide-react";

const PAGE_SIZE = 24;

/** Card snippet: "venue · games · date" from the infobox when present, else the raw text. */
function snippetText(snippet: string): string {
  const { fields, body } = splitInfobox(snippet);
  if (!fields.length) return body;
  const get = (k: string) => fields.find(([key]) => key === k)?.[1];
  return [get("venue"), get("games") && `${get("games")} Games`, get("date") ?? get("dates"), get("competitors") && `${get("competitors")} competitors`]
    .filter(Boolean)
    .join(" · ");
}

export default function CorpusExplorer({ totalDocs }: { totalDocs?: number }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [documents, setDocuments] = useState<CorpusDocSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<CorpusDocDetail | null>(null);
  const requestId = useRef(0);

  // Debounced search; responses from superseded requests are ignored.
  useEffect(() => {
    const id = ++requestId.current;
    setIsLoading(true);
    const t = setTimeout(async () => {
      try {
        const res = await getCorpusDocuments(searchTerm.trim(), PAGE_SIZE, 0);
        if (id !== requestId.current) return;
        setDocuments(res.documents);
        setTotal(res.total);
        setError(null);
      } catch (err) {
        if (id === requestId.current) setError((err as Error).message);
      } finally {
        if (id === requestId.current) setIsLoading(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [searchTerm]);

  const loadMore = async () => {
    setIsLoadingMore(true);
    try {
      const res = await getCorpusDocuments(searchTerm.trim(), PAGE_SIZE, documents.length);
      setDocuments((prev) => [...prev, ...res.documents]);
      setTotal(res.total);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoadingMore(false);
    }
  };

  const openDoc = async (docId: string) => {
    setOpeningId(docId);
    try {
      setSelectedDoc(await getCorpusDocDetail(docId));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setOpeningId(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={BookOpen}
        title="Corpus"
        description={`The ${totalDocs ? totalDocs.toLocaleString() : ""} source documents the agent retrieves from: Olympic event articles with infoboxes (venue, dates, competitors, medalists) that are turned into graph entities and links.`}
      />

      <Card className="py-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden />
          <input
            type="search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by title, venue, athlete or keyword…"
            aria-label="Search the corpus"
            className="field h-11 pl-10 pr-10"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:bg-white/5 hover:text-slate-200"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <p className="mt-2 text-xs text-slate-500" aria-live="polite">
          {isLoading ? "Searching…" : `${total.toLocaleString()} document${total === 1 ? "" : "s"}${searchTerm ? ` matching "${searchTerm.trim()}"` : ""}`}
        </p>
      </Card>

      {error && <Callout tone="red">{error}</Callout>}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="space-y-3 rounded-xl border border-white/10 bg-surface/50 p-4">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          ))}
        </div>
      ) : documents.length === 0 ? (
        <Card padded={false}>
          <EmptyState icon={SearchX} title="No matching documents">
            Try a venue (&quot;Eton Dorney&quot;), a Games (&quot;2012 Summer&quot;) or an athlete name.
          </EmptyState>
        </Card>
      ) : (
        <>
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {documents.map((doc) => (
              <li key={doc.doc_id}>
                <button
                  onClick={() => openDoc(doc.doc_id)}
                  className="group flex h-full w-full flex-col rounded-xl border border-white/10 bg-surface/50 p-4 text-left transition-all hover:border-cyan-400/40 hover:bg-surface"
                >
                  <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px]">
                    <span className="font-mono text-slate-500">{doc.doc_id}</span>
                    {openingId === doc.doc_id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400" aria-label="Opening" />
                    ) : (
                      <span className="text-slate-600">~{doc.approx_tokens.toLocaleString()} tok</span>
                    )}
                  </div>
                  <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-slate-100 group-hover:text-cyan-200">{doc.title}</h3>
                  <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-slate-400">{snippetText(doc.snippet)}</p>
                </button>
              </li>
            ))}
          </ul>

          {documents.length < total && (
            <div className="flex flex-col items-center gap-2">
              <Button onClick={loadMore} loading={isLoadingMore}>
                Load more
              </Button>
              <span className="text-xs text-slate-500">
                Showing {documents.length.toLocaleString()} of {total.toLocaleString()}
              </span>
            </div>
          )}
        </>
      )}

      <DocumentModal doc={selectedDoc} onClose={() => setSelectedDoc(null)} />
    </div>
  );
}
