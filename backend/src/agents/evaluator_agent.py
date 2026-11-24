"""Evaluator Sub-Agent for GraphScout.

Inspects collected graph & chunk evidence, checks for contradictions or gaps,
and determines stopping conditions.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple
from pydantic import BaseModel, Field

from src.agents.state import EvaluationVerdict, KnowledgeGap, SubgraphData, DocumentChunk
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.EvaluatorAgent")


class EvaluatorAgent:
    """Evaluator agent responsible for stopping condition checks and gap identification."""

    def __init__(self, llm_client: LLMClient, completeness_threshold: float = 0.85):
        self.llm = llm_client
        self.completeness_threshold = completeness_threshold

    def evaluate(
        self,
        user_query: str,
        subgraph: SubgraphData,
        chunks: Dict[str, DocumentChunk],
        identified_gaps: List[KnowledgeGap],
    ) -> Tuple[EvaluationVerdict, Dict[str, int]]:
        """Evaluate whether current evidence is sufficient to decisively answer user query."""
        system_prompt = (
            "You are the Chief Evidence Evaluator in an Agentic GraphRAG system. "
            "Analyze the accumulated graph entities, relations, and text chunks against the user query. "
            "Identify remaining knowledge gaps, contradictions, or missing links, and output an objective completeness score [0.0 to 1.0]."
        )

        nodes_summary = [f"- {n.canonical_name} ({n.entity_type}): {n.description}" for n in subgraph.nodes[:15]]
        edges_summary = [f"- {e.source_id} -> [{e.relation_type}] -> {e.target_id}" for e in subgraph.edges[:15]]
        chunks_summary = [f"[{c.chunk_id}] {c.text_content[:200]}..." for c in list(chunks.values())[:5]]

        user_prompt = f"""
USER QUERY:
{user_query}

ACCUMULATED GRAPH NODES:
{chr(10).join(nodes_summary) if nodes_summary else "No graph nodes discovered yet."}

ACCUMULATED GRAPH EDGES:
{chr(10).join(edges_summary) if edges_summary else "No graph relations discovered yet."}

DOCUMENT CHUNK SNIPPETS:
{chr(10).join(chunks_summary) if chunks_summary else "No text chunks retrieved yet."}

CURRENT UNRESOLVED GAPS:
{chr(10).join(f"- {g.description}" for g in identified_gaps) if identified_gaps else "None"}

Please evaluate completeness and return an EvaluationVerdict.
"""

        verdict, usage = self.llm.generate_json(system_prompt, user_prompt, EvaluationVerdict)

        # Force sufficiency check based on threshold
        if verdict.completeness_score >= self.completeness_threshold:
            verdict.has_sufficient_evidence = True

        logger.info(
            "Evaluation complete: score=%.2f, sufficient=%s, gaps_found=%d",
            verdict.completeness_score,
            verdict.has_sufficient_evidence,
            len(verdict.knowledge_gaps),
        )
        return verdict, usage
