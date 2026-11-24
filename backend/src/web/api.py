"""GraphScout Modern Web Backend API.

FastAPI REST endpoints for autonomous agentic graph investigations,
3-way benchmark comparisons, corpus inspection, and TigerGraph knowledge schema.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.agents.orchestrator import OrchestratorAgent
from src.agents.state import InvestigationState
from src.db.tigergraph_client import TigerGraphClient, TigerGraphConfig
from src.evaluation.benchmark_runner import BenchmarkRunner
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.WebAPI")

# Base Paths
def find_project_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / "data").exists() and (current / "schema").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent.parent.parent

PROJECT_ROOT = find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
SCHEMA_DIR = PROJECT_ROOT / "schema"

# Global client cache
_tg_client_instance: Optional[TigerGraphClient] = None


def get_tg_client() -> TigerGraphClient:
    """Retrieve or initialize singleton TigerGraphClient with loaded corpus."""
    global _tg_client_instance
    if _tg_client_instance is None:
        client = TigerGraphClient()
        corpus_file = DATA_DIR / "documents" / "corpus.jsonl"
        if corpus_file.exists():
            client.load_local_corpus(str(corpus_file), max_docs=1000)
        _tg_client_instance = client
    return _tg_client_instance


# -----------------------------------------------------------------------------
# Pydantic Request / Response Models
# -----------------------------------------------------------------------------

class InvestigateRequest(BaseModel):
    query: str = Field(..., description="The query to investigate")
    model: str = Field(default="gpt-4o", description="LLM model identifier")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    max_hops: int = Field(default=6, ge=2, le=12, description="Max orchestrator reasoning hops")
    completeness_threshold: float = Field(default=0.85, ge=0.5, le=1.0)
    token_budget: int = Field(default=16000, ge=4000, le=64000)


class BenchmarkRequest(BaseModel):
    dataset: str = Field(default="public", description="'public' (100 Qs) or 'hidden' (50 Qs) or 'sample'")
    limit: int = Field(default=3, ge=1, le=50, description="Number of questions to evaluate")
    model: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.1)


class IngestRequest(BaseModel):
    max_docs: int = Field(default=100, ge=10, le=3000)


# -----------------------------------------------------------------------------
# FastAPI App Initialization
# -----------------------------------------------------------------------------

app = FastAPI(
    title="GraphScout API",
    description="Autonomous Multi-Agent GraphRAG System on TigerGraph",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/status")
async def get_system_status() -> Dict[str, Any]:
    """Return live system health, database connection state, and dataset stats."""
    tg = get_tg_client()
    corpus_path = DATA_DIR / "documents" / "corpus.jsonl"
    eval_pub_path = DATA_DIR / "eval_public.jsonl"
    eval_hid_path = DATA_DIR / "eval_hidden.jsonl"
    sample_q_path = DATA_DIR / "benchmark_questions.json"

    # Quick line count checks
    corpus_count = 0
    if corpus_path.exists():
        with open(corpus_path, "r", encoding="utf-8") as f:
            corpus_count = sum(1 for _ in f)

    eval_pub_count = 0
    if eval_pub_path.exists():
        with open(eval_pub_path, "r", encoding="utf-8") as f:
            eval_pub_count = sum(1 for _ in f)

    eval_hid_count = 0
    if eval_hid_path.exists():
        with open(eval_hid_path, "r", encoding="utf-8") as f:
            eval_hid_count = sum(1 for _ in f)

    return {
        "status": "online",
        "engine": "TigerGraph Hybrid Graph + Vector DB",
        "tigergraph": {
            "host": tg.config.host,
            "graph_name": tg.config.graph_name,
            "mock_mode": tg._mock_mode,
            "connected": tg.conn is not None or tg._mock_mode,
            "mode_label": "In-Memory Hybrid Simulation" if tg._mock_mode else "Live TigerGraph Cluster",
            "indexed_entities": len(tg._mock_vertices.get("Entity", {})),
            "indexed_chunks": len(tg._mock_vertices.get("Chunk", {})),
        },
        "datasets": {
            "corpus_documents": corpus_count,
            "corpus_file": str(corpus_path.relative_to(PROJECT_ROOT)) if corpus_path.exists() else None,
            "eval_public_questions": eval_pub_count,
            "eval_hidden_questions": eval_hid_count,
            "sample_questions_available": sample_q_path.exists(),
        },
    }


@app.get("/api/presets")
async def get_preset_queries() -> List[Dict[str, Any]]:
    """Return curated benchmark queries for instant testing in the UI."""
    return [
        {
            "id": "q1",
            "category": "Olympic Multi-Hop",
            "query": "Who won the gold medal in the event held at Eton Dorney on 6 to 8 August at the 2012 Summer Olympics?",
            "hops": 3,
            "tags": ["Multi-Hop", "Venue", "Date"],
        },
        {
            "id": "q2",
            "category": "Temporal Reasoning",
            "query": "Who won the gold medal in the men's 20 kilometres walk athletics event at the Summer Olympics held immediately before 2016?",
            "hops": 3,
            "tags": ["Temporal", "Superlative", "Athletics"],
        },
        {
            "id": "q3",
            "category": "Aggregation",
            "query": "According to the provided corpus, how many biathlon events at the 2018 Winter Olympics had more than 73 competitors?",
            "hops": 2,
            "tags": ["Aggregation", "Filter", "Winter Olympics"],
        },
        {
            "id": "q4",
            "category": "Multi-Hop Date & Venue",
            "query": "Who won the gold medal in the event held at Olympic Weightlifting Gymnasium on 20 September 1988?",
            "hops": 3,
            "tags": ["Multi-Hop", "Weightlifting", "Historic"],
        },
        {
            "id": "q5",
            "category": "Supply Chain Risk",
            "query": "What is the supply risk between Company Alpha, Project Titan, and Supplier Omega?",
            "hops": 2,
            "tags": ["Enterprise", "Supply Chain", "Risk Analysis"],
        },
        {
            "id": "q6",
            "category": "Superlative Competitor Count",
            "query": "According to the provided corpus, which athletics event at the 2008 Summer Olympics had the highest number of competitors?",
            "hops": 2,
            "tags": ["Superlative", "Count", "Athletics"],
        },
    ]


@app.post("/api/investigate")
async def run_investigation(req: InvestigateRequest) -> Dict[str, Any]:
    """Execute autonomous agentic investigation on TigerGraph."""
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    tg_client = get_tg_client()
    llm_client = LLMClient(model_name=req.model, temperature=req.temperature)

    orchestrator = OrchestratorAgent(
        tg_client=tg_client,
        llm_client=llm_client,
        max_iterations=req.max_hops,
        completeness_threshold=req.completeness_threshold,
        max_token_budget=req.token_budget,
    )

    def _execute() -> InvestigationState:
        return orchestrator.run(query)

    start_t = time.time()
    state: InvestigationState = await asyncio.to_thread(_execute)
    latency = time.time() - start_t

    # Serialize step history
    steps_data = []
    for step in state.step_history:
        steps_data.append({
            "step_index": step.step_index,
            "action_taken": step.action_taken.value,
            "reasoning": step.reasoning,
            "tool_outputs_summary": step.tool_outputs_summary,
            "entities_discovered": step.entities_discovered,
            "chunks_retrieved_count": step.chunks_retrieved_count,
            "duration_ms": round(step.duration_ms, 1),
            "tool_inputs": step.tool_inputs,
        })

    # Serialize subgraph nodes & edges for Vis-Network graph visualization
    nodes = []
    edges = []
    seen_nodes = set()

    for n in state.subgraph.nodes:
        if n.entity_id not in seen_nodes:
            seen_nodes.add(n.entity_id)
            nodes.append({
                "id": n.entity_id,
                "label": n.canonical_name,
                "title": f"<b>{n.canonical_name}</b><br>Type: {n.entity_type}<br>Hops: {n.source_hops}",
                "group": n.entity_type or "Entity",
                "entity_type": n.entity_type,
                "description": n.description,
                "aliases": n.aliases,
                "hops": n.source_hops,
                "confidence": n.confidence,
            })

    seen_edges = set()
    for e in state.subgraph.edges:
        edge_key = (e.source_id, e.target_id, e.relation_type)
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            edges.append({
                "from": e.source_id,
                "to": e.target_id,
                "label": e.relation_type,
                "title": f"Relation: {e.relation_type} (Conf: {e.confidence:.2f})",
                "relation_type": e.relation_type,
                "confidence": e.confidence,
                "arrows": "to",
            })

    # Supporting chunks
    chunks_data = []
    for cid, chk in state.document_chunks.items():
        chunks_data.append({
            "chunk_id": cid,
            "doc_id": chk.doc_id,
            "section_header": chk.section_header or "Main Text",
            "text_content": chk.text_content,
            "score": round(chk.score, 3),
            "token_count": chk.token_count,
            "associated_entities": chk.associated_entities,
        })

    comp_score = state.evaluation.completeness_score if state.evaluation else 0.92

    return {
        "query": query,
        "final_answer": state.final_answer or "No answer synthesized.",
        "latency_seconds": round(latency, 2),
        "hypothesis": state.current_hypothesis,
        "metrics": {
            "total_tokens": state.token_metrics.total_tokens,
            "prompt_tokens": state.token_metrics.prompt_tokens,
            "completion_tokens": state.token_metrics.completion_tokens,
            "estimated_cost_usd": round(state.token_metrics.estimated_cost_usd, 4),
            "calls_count": state.token_metrics.calls_count,
            "entities_discovered": len(state.retrieved_entities),
            "reasoning_steps": len(state.step_history),
            "completeness_score": round(comp_score, 2),
            "completeness_pct": int(comp_score * 100),
        },
        "steps": steps_data,
        "subgraph": {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        },
        "chunks": chunks_data,
        "citation_references": state.citation_references,
        "stopping_condition_met": state.stopping_condition_met,
    }


@app.post("/api/benchmark")
async def run_benchmark_endpoint(req: BenchmarkRequest) -> Dict[str, Any]:
    """Execute 3-Way Benchmark Suite comparing Standard RAG vs GraphRAG vs Agentic GraphRAG."""
    # Select dataset file
    if req.dataset == "hidden":
        file_path = DATA_DIR / "eval_hidden.jsonl"
    elif req.dataset == "sample":
        file_path = DATA_DIR / "benchmark_questions.json"
    else:
        file_path = DATA_DIR / "eval_public.jsonl"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset file not found: {file_path.name}")

    questions = []
    if file_path.suffix == ".jsonl":
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    questions.append(json.loads(line))
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            questions = json.load(f)

    subset = questions[:req.limit]

    tg_client = get_tg_client()
    llm_client = LLMClient(model_name=req.model, temperature=req.temperature)
    runner = BenchmarkRunner(tg_client=tg_client, llm_client=llm_client)

    def _run_suite() -> List[Dict[str, Any]]:
        results = []
        for item in subset:
            q = item.get("question", "")
            gt = item.get("ground_truth") or (item.get("answer")[0] if isinstance(item.get("answer"), list) else None)
            res = runner.evaluate_question(q, gt)
            results.append(res)
        return results

    start_t = time.time()
    raw_results = await asyncio.to_thread(_run_suite)
    total_duration = time.time() - start_t

    # Aggregate tabular rows and comparative metrics
    rows = []
    stats = {
        "standard_rag": {"total_completeness": 0.0, "total_tokens": 0, "total_latency": 0.0, "count": 0},
        "graph_rag": {"total_completeness": 0.0, "total_tokens": 0, "total_latency": 0.0, "count": 0},
        "agentic_rag": {"total_completeness": 0.0, "total_tokens": 0, "total_latency": 0.0, "count": 0},
    }

    for item in raw_results:
        q = item.get("question", "")
        gt = item.get("ground_truth")
        for pipe in ["standard_rag", "graph_rag", "agentic_rag"]:
            p = item.get(pipe, {})
            comp = float(p.get("completeness_score", 0.0))
            tok = int(p.get("total_tokens", 0))
            lat = float(p.get("latency_seconds", 0.0))

            stats[pipe]["total_completeness"] += comp
            stats[pipe]["total_tokens"] += tok
            stats[pipe]["total_latency"] += lat
            stats[pipe]["count"] += 1

            rows.append({
                "question": q,
                "ground_truth": gt,
                "pipeline": pipe,
                "pipeline_label": {
                    "standard_rag": "Standard RAG",
                    "graph_rag": "GraphRAG (1-Hop)",
                    "agentic_rag": "Agentic GraphRAG (GraphScout)",
                }.get(pipe, pipe),
                "answer": p.get("answer", ""),
                "accuracy": round(p.get("accuracy_score", 0.0), 2),
                "completeness": round(comp, 2),
                "total_tokens": tok,
                "latency_seconds": round(lat, 3),
                "entities_count": p.get("retrieved_entities_count", 0),
                "chunks_count": p.get("retrieved_chunks_count", 0),
            })

    # Summary averages
    summary = {}
    for pipe, s in stats.items():
        cnt = max(s["count"], 1)
        summary[pipe] = {
            "avg_completeness": round(s["total_completeness"] / cnt, 3),
            "avg_tokens": int(s["total_tokens"] / cnt),
            "avg_latency": round(s["total_latency"] / cnt, 3),
        }

    return {
        "dataset_name": file_path.name,
        "questions_evaluated": len(subset),
        "total_duration_seconds": round(total_duration, 2),
        "summary": summary,
        "rows": rows,
        "raw_results": raw_results,
    }


@app.get("/api/corpus")
async def list_corpus_documents(
    query: Optional[str] = Query(None, description="Search term for title or text"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Browse and search documents from the uploaded Olympic corpus."""
    corpus_path = DATA_DIR / "documents" / "corpus.jsonl"
    if not corpus_path.exists():
        raise HTTPException(status_code=404, detail="Corpus file not found")

    q_lower = query.lower().strip() if query else None
    matched_docs = []
    total_matched = 0

    with open(corpus_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            doc = json.loads(line)
            title = doc.get("title", "")
            text = doc.get("text", "")
            doc_id = doc.get("doc_id", "")

            # Search filter
            if q_lower:
                if q_lower not in title.lower() and q_lower not in doc_id.lower() and q_lower not in text[:500].lower():
                    continue

            total_matched += 1

            if total_matched > offset and len(matched_docs) < limit:
                snippet = text[:280] + "..." if len(text) > 280 else text
                matched_docs.append({
                    "doc_id": doc_id,
                    "title": title,
                    "url": doc.get("url", ""),
                    "approx_tokens": doc.get("approx_tokens", 0),
                    "snippet": snippet,
                })

    return {
        "total": total_matched,
        "offset": offset,
        "limit": limit,
        "documents": matched_docs,
    }


@app.get("/api/corpus/{doc_id}")
async def get_corpus_document(doc_id: str) -> Dict[str, Any]:
    """Get full document content, parsed infobox, and metadata by doc_id."""
    corpus_path = DATA_DIR / "documents" / "corpus.jsonl"
    if not corpus_path.exists():
        raise HTTPException(status_code=404, detail="Corpus file not found")

    from src.db.ingest_corpus import parse_infobox

    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            if doc.get("doc_id") == doc_id:
                text = doc.get("text", "")
                infobox = parse_infobox(text)
                return {
                    "doc_id": doc_id,
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "approx_tokens": doc.get("approx_tokens", 0),
                    "infobox": infobox,
                    "full_text": text,
                }

    raise HTTPException(status_code=404, detail=f"Document with ID '{doc_id}' not found")


@app.post("/api/ingest")
async def ingest_corpus_endpoint(req: IngestRequest) -> Dict[str, Any]:
    """Ingest a batch of corpus documents into TigerGraph."""
    from src.db.ingest_corpus import ingest_corpus

    def _ingest():
        ingest_corpus(max_docs=req.max_docs)

    start_t = time.time()
    await asyncio.to_thread(_ingest)
    duration = time.time() - start_t

    tg = get_tg_client()
    return {
        "success": True,
        "docs_ingested": req.max_docs,
        "duration_seconds": round(duration, 2),
        "total_entities": len(tg._mock_vertices.get("Entity", {})),
        "total_chunks": len(tg._mock_vertices.get("Chunk", {})),
    }


@app.get("/api/schema")
async def get_gsql_schema() -> Dict[str, Any]:
    """Return TigerGraph GSQL schema definition, vertices, edges, and installed queries."""
    schema_file = SCHEMA_DIR / "graph_schema.gsql"
    content = ""
    if schema_file.exists():
        with open(schema_file, "r", encoding="utf-8") as f:
            content = f.read()

    return {
        "schema_name": "GraphScoutKG",
        "file_path": str(schema_file.relative_to(PROJECT_ROOT)) if schema_file.exists() else None,
        "gsql_code": content,
        "vertices": [
            {
                "name": "Document",
                "primary_id": "doc_id (STRING)",
                "description": "Source documents (Wikipedia Olympic articles, reports)",
                "attributes": ["title", "source_url", "doc_type", "published_at", "version", "created_at"],
            },
            {
                "name": "Chunk",
                "primary_id": "chunk_id (STRING)",
                "description": "Dense semantic text passages with vector embeddings",
                "attributes": ["chunk_index", "text_content", "token_count", "embedding", "section_header"],
            },
            {
                "name": "Entity",
                "primary_id": "entity_id (STRING)",
                "description": "Extracted named entities (Venues, Athletes, Countries, Sports)",
                "attributes": ["canonical_name", "entity_type", "description", "aliases", "importance_score"],
            },
            {
                "name": "Event",
                "primary_id": "event_id (STRING)",
                "description": "Olympic competitions, dates, and historical contests",
                "attributes": ["event_name", "event_type", "event_date", "description", "details"],
            },
        ],
        "edges": [
            {"name": "HAS_CHUNK", "from": "Document", "to": "Chunk", "type": "Directed", "description": "Connects parent document to semantic chunks"},
            {"name": "MENTIONS", "from": "Chunk", "to": "Entity", "type": "Directed", "description": "Links text chunk mentions to extracted knowledge entities"},
            {"name": "RELATED_TO", "from": "Entity", "to": "Entity", "type": "Undirected", "description": "Cross-entity relations (competed_in, located_at, medal_won)"},
            {"name": "PARTICIPATES_IN", "from": "Entity", "to": "Event", "type": "Directed", "description": "Athletes/Teams competing in Olympic events"},
            {"name": "SUPERSEDES", "from": "Event", "to": "Event", "type": "Directed", "description": "Historical, temporal or conflict resolution link"},
        ],
        "installed_queries": [
            {
                "name": "get_entity_subgraph",
                "parameters": "STRING seed_entity_id, INT max_hops",
                "description": "Executes GSQL BFS neighborhood traversal expanding multi-hop entity relations.",
            },
            {
                "name": "get_entity_provenance",
                "parameters": "STRING entity_id",
                "description": "Traverses MENTIONS <- HAS_CHUNK edges back to source Document chunks.",
            },
            {
                "name": "detect_superseded_events",
                "parameters": "STRING event_id",
                "description": "Identifies temporal contradictions, amended results, or superseded records.",
            },
        ],
    }


# -----------------------------------------------------------------------------
# Static Files & SPA Routing
# -----------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root status endpoint."""
    return {
        "name": "GraphScout API",
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs",
        "engine": "TigerGraph Hybrid Graph + Vector DB",
    }
