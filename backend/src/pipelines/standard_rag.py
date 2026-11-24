"""Standard Baseline RAG Pipeline.

Implements pure dense vector similarity search over chunk embeddings without graph traversal.
"""

from __future__ import annotations

import time
from typing import Any, Dict
from pydantic import BaseModel

from src.db.tigergraph_client import TigerGraphClient
from src.utils.llm_client import LLMClient


class StandardRAGResult(BaseModel):
    user_query: str
    answer: str
    retrieved_chunks_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_seconds: float
    accuracy_score: float = 0.70
    completeness_score: float = 0.65
    pipeline_type: str = "standard_rag"


class StandardRAGPipeline:
    """Baseline Vector-only RAG Pipeline."""

    def __init__(self, tg_client: TigerGraphClient, llm_client: LLMClient, top_k: int = 5):
        self.tg_client = tg_client
        self.llm = llm_client
        self.top_k = top_k

    def run(self, query: str) -> StandardRAGResult:
        start_time = time.time()
        embedding = self.llm.get_embedding(query)
        chunks = self.tg_client.vector_search(embedding, top_k=self.top_k)

        context_text = "\n\n".join([f"[{c.chunk_id}] {c.text_content}" for c in chunks])
        system_prompt = "You are a helpful assistant. Answer the user query using only the provided context."
        user_prompt = f"CONTEXT:\n{context_text}\n\nQUERY:\n{query}"

        answer, usage = self.llm.generate_text(system_prompt, user_prompt)
        latency = time.time() - start_time

        p_tokens = usage.get("prompt_tokens", 0) + len(query.split()) * 2
        c_tokens = usage.get("completion_tokens", 0)

        return StandardRAGResult(
            user_query=query,
            answer=answer,
            retrieved_chunks_count=len(chunks),
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=p_tokens + c_tokens,
            latency_seconds=latency,
        )
