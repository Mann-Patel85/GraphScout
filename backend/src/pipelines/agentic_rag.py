"""Agentic GraphRAG Pipeline for GraphScout.

Executes autonomous multi-hop investigation loop and packages results for benchmarking.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from src.agents.orchestrator import OrchestratorAgent
from src.agents.state import InvestigationState


class AgenticRAGResult(BaseModel):
    user_query: str
    answer: str
    iterations_taken: int
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
    # The evaluator agent's own completeness estimate (not ground-truth based).
    self_assessed_completeness: Optional[float] = None
    pipeline_type: str = "agentic_rag"
    retrieved_context: str = Field(default="", exclude=True)


class AgenticRAGPipeline:
    """Agentic Multi-Hop GraphRAG Pipeline."""

    def __init__(self, orchestrator: OrchestratorAgent):
        self.orchestrator = orchestrator

    def run(self, query: str) -> AgenticRAGResult:
        state: InvestigationState = self.orchestrator.run(query)

        context_parts = [f"- {n.canonical_name} ({n.entity_type})" for n in state.subgraph.nodes]
        context_parts += [f"- {e.source_id} -[{e.relation_type}]-> {e.target_id}" for e in state.subgraph.edges]
        context_parts += [f"[{cid}] {c.text_content}" for cid, c in state.document_chunks.items()]

        return AgenticRAGResult(
            user_query=query,
            answer=state.final_answer or "",
            iterations_taken=len(state.step_history),
            retrieved_entities_count=len(state.subgraph.nodes),
            retrieved_edges_count=len(state.subgraph.edges),
            retrieved_chunks_count=len(state.document_chunks),
            prompt_tokens=state.token_metrics.prompt_tokens,
            completion_tokens=state.token_metrics.completion_tokens,
            total_tokens=state.token_metrics.total_tokens,
            latency_seconds=state.total_latency_seconds,
            self_assessed_completeness=state.evaluation.completeness_score if state.evaluation else None,
            retrieved_context="\n".join(context_parts),
        )
