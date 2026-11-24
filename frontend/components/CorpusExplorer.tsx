"use client";

import React, { useState, useEffect } from "react";
import { CorpusDocDetail, CorpusDocSummary } from "../lib/types";
import { getCorpusDocuments, getCorpusDocDetail, ingestCorpus } from "../lib/api";
import DocumentModal from "./DocumentModal";
import { Search, RotateCw, BookOpen, ExternalLink, Hash, Check } from "lucide-react";

export default function CorpusExplorer() {
  const [searchTerm, setSearchTerm] = useState("");
  const [documents, setDocuments] = useState<CorpusDocSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<CorpusDocDetail | null>(null);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      fetchDocs(searchTerm);
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [searchTerm]);

  const fetchDocs = async (q: string) => {
    setIsLoading(true);
    try {
      const res = await getCorpusDocuments(q, 24, 0);
      setDocuments(res.documents);
      setTotal(res.total);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDocClick = async (docId: string) => {
    try {
      const doc = await getCorpusDocDetail(docId);
      setSelectedDoc(doc);
    } catch (err) {
      console.error(err);
    }
  };

  const handleIngest = async () => {
    setIsIngesting(true);
    setIngestSuccess(null);
    try {
      const res = await ingestCorpus(100);
      setIngestSuccess(`Ingested ${res.docs_ingested} docs into TigerGraph in ${res.duration_seconds}s!`);
      setTimeout(() => setIngestSuccess(null), 4000);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsIngesting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
          Olympic Corpus &amp; Document Index <BookOpen className="w-5 h-5 text-cyan-400" />
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Explore and inspect the 2,951 Olympic event documents with infoboxes, dates, competitors, and medalists indexed in TigerGraph.
        </p>
      </div>

      {/* Search & Ingest Toolbar */}
      <div className="bg-[#0f172a]/80 border border-white/10 rounded-2xl p-4 shadow-xl backdrop-blur-md flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 top-3" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search articles by title, event, venue, or keywords..."
            className="w-full pl-11 pr-4 py-2.5 bg-slate-900 border border-white/10 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
          />
        </div>

        <button
          onClick={handleIngest}
          disabled={isIngesting}
          className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-white/10 text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-50 shrink-0"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isIngesting ? "animate-spin text-cyan-400" : ""}`} />
          <span>{isIngesting ? "Ingesting Documents..." : "Ingest Sample Corpus"}</span>
        </button>
      </div>

      {ingestSuccess && (
        <div className="p-3 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
          <Check className="w-4 h-4" />
          <span>{ingestSuccess}</span>
        </div>
      )}

      {/* Grid of Documents */}
      {isLoading ? (
        <div className="text-slate-500 text-sm py-12 text-center">Searching corpus...</div>
      ) : documents.length === 0 ? (
        <div className="text-slate-500 text-sm py-12 text-center">No matching documents found.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <div
              key={doc.doc_id}
              onClick={() => handleDocClick(doc.doc_id)}
              className="bg-[#0f172a]/60 hover:bg-[#0f172a] border border-white/10 hover:border-cyan-400/40 rounded-xl p-4 cursor-pointer transition-all flex flex-col justify-between group shadow-lg"
            >
              <div>
                <div className="flex items-center justify-between text-[11px] font-mono text-cyan-400 font-bold mb-1">
                  <span>{doc.doc_id}</span>
                  <span className="text-slate-500">~{doc.approx_tokens} tokens</span>
                </div>
                <h4 className="font-bold text-slate-100 text-sm line-clamp-1 group-hover:text-cyan-300 transition-colors">
                  {doc.title}
                </h4>
                <p className="text-xs text-slate-400 line-clamp-3 mt-1.5 leading-relaxed">
                  {doc.snippet}
                </p>
              </div>

              <div className="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-[11px] font-semibold text-slate-500 group-hover:text-cyan-400">
                <span>Inspect Document</span>
                <span>&rarr;</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Drawer */}
      <DocumentModal doc={selectedDoc} onClose={() => setSelectedDoc(null)} />
    </div>
  );
}
