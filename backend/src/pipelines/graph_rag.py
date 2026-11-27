"""Static GraphRAG Pipeline.

Implements single-pass hybrid Graph + Vector retrieval without iterative agentic loop.
"""

from __future__ import annotations

import time
from typing import Optional
from pydantic import BaseModel, Field

from src.db.graph_client import GraphClient
from src.utils.llm_client import LLMClient
from src.agents.tools.graph_tool import GraphTool


class GraphRAGResult(BaseModel):
    user_query: str
    answer: str
    retrieved_entities_count: int
    retrieved_edges_count: int
    retrieved_chunks_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_seconds: float
    # Filled in by the benchmark runner against ground truth (None = not scored).
    accuracy_score: Optional[float] = None
    completeness_score: Optional[float] = None
    pipeline_type: str = "graph_rag"
    retrieved_context: str = Field(default="", exclude=True)


class GraphRAGPipeline:
    """One-shot Static Graph + Vector RAG Pipeline."""

    def __init__(self, tg_client: GraphClient, llm_client: LLMClient, max_hops: int = 1, top_k_chunks: int = 3):
        self.tg_client = tg_client
        self.llm = llm_client
        self.max_hops = max_hops
        self.top_k_chunks = top_k_chunks
        self.graph_tool = GraphTool(tg_client, llm_client)

    def run(self, query: str) -> GraphRAGResult:
        start_time = time.time()
        prompt_tokens = 0
        completion_tokens = 0

        # Step 1: Entity linking
        seed_entities, usage_ent = self.graph_tool.link_entities(query)
        prompt_tokens += usage_ent.get("prompt_tokens", 0)
        completion_tokens += usage_ent.get("completion_tokens", 0)

        # Step 2: 1-pass Graph Subgraph retrieval
        subgraph = self.tg_client.get_entity_subgraph(seed_entities, max_hops=self.max_hops)

        # Step 3: Vector retrieval
        embedding = self.llm.get_embedding(query)
        chunks = self.tg_client.vector_search(embedding, top_k=self.top_k_chunks, query_text=query)
        prompt_tokens += len(query.split()) * 2

        # Step 4: Single-pass synthesis
        graph_text = "\n".join([f"- {e.source_id} -[{e.relation_type}]-> {e.target_id}" for e in subgraph.edges])
        nodes_text = "\n".join([f"- {n.canonical_name} ({n.entity_type})" for n in subgraph.nodes])
        chunks_text = "\n\n".join([f"[{c.chunk_id}] {c.text_content}" for c in chunks])

        system_prompt = "You are a GraphRAG expert. Answer the query using both graph relationships and document chunks."
        user_prompt = f"GRAPH RELATIONS:\n{graph_text}\n\nDOCUMENT CHUNKS:\n{chunks_text}\n\nQUERY:\n{query}"

        answer, usage_syn = self.llm.generate_text(system_prompt, user_prompt)
        prompt_tokens += usage_syn.get("prompt_tokens", 0)
        completion_tokens += usage_syn.get("completion_tokens", 0)

        latency = time.time() - start_time

        return GraphRAGResult(
            user_query=query,
            answer=answer,
            retrieved_entities_count=len(subgraph.nodes),
            retrieved_edges_count=len(subgraph.edges),
            retrieved_chunks_count=len(chunks),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_seconds=latency,
            retrieved_context="\n".join([nodes_text, graph_text, chunks_text]),
        )
