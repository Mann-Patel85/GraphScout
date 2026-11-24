"""Autonomous Orchestrator Agent for GraphScout.

Implements the central multi-hop reasoning loop, dynamic tool selection,
gap-driven investigation, hypothesis refinement, and evidence synthesis on TigerGraph.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.agents.state import (
    AgentActionType,
    AgentStepTrace,
    DocumentChunk,
    EntityNode,
    EvaluationVerdict,
    InvestigationState,
    KnowledgeGap,
    SubgraphData,
)
from src.agents.tools.evaluator_tool import EvaluatorTool
from src.agents.tools.graph_tool import GraphTool
from src.agents.tools.vector_tool import VectorTool
from src.db.tigergraph_client import TigerGraphClient
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.Orchestrator")


class OrchestratorDecision(BaseModel):
    """Structured decision output from the Orchestrator LLM engine."""
    action: AgentActionType
    reasoning: str
    updated_hypothesis: Optional[str] = None
    search_queries: List[str] = Field(default_factory=list, description="Queries if action is vector_search")
    seed_entities: List[str] = Field(default_factory=list, description="Target entity IDs if action is graph_traversal")
    max_hops: int = Field(default=2, description="Hop depth for graph traversal")
    resolved_gap_ids: List[str] = Field(default_factory=list)


class SynthesisResult(BaseModel):
    """Structured synthesis of the final multi-hop answer."""
    answer: str
    key_findings: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)


class OrchestratorAgent:
    """Core autonomous decision engine coordinating Graph, Vector, and Evaluation tools."""

    def __init__(
        self,
        tg_client: TigerGraphClient,
        llm_client: LLMClient,
        max_iterations: int = 6,
        completeness_threshold: float = 0.85,
        max_token_budget: int = 16000,
    ):
        self.tg_client = tg_client
        self.llm = llm_client
        self.max_iterations = max_iterations
        self.completeness_threshold = completeness_threshold
        self.max_token_budget = max_token_budget

        # Initialize sub-agent tools
        self.graph_tool = GraphTool(tg_client, llm_client)
        self.vector_tool = VectorTool(tg_client, llm_client)
        self.evaluator_tool = EvaluatorTool(llm_client, completeness_threshold)

    def run(self, user_query: str) -> InvestigationState:
        """Execute the autonomous multi-hop investigation loop."""
        state = InvestigationState(
            user_query=user_query,
            max_iterations=self.max_iterations,
        )
        logger.info("Starting GraphScout investigation for query: '%s'", user_query)
        start_time = time.time()

        # Step 0: Initial Entity Linking
        initial_entities, usage = self.graph_tool.link_entities(user_query)
        state.token_metrics.add(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))

        for ent_name in initial_entities:
            state.add_entity(
                EntityNode(
                    entity_id=ent_name.replace(" ", "_"),
                    canonical_name=ent_name,
                    source_hops=0,
                )
            )

        # Autonomous Reasoning Loop
        while not state.stopping_condition_met and state.iteration_count < state.max_iterations:
            # Check Token Budget
            if state.token_metrics.total_tokens >= self.max_token_budget:
                logger.warning("Token budget (%d) reached. Forcing synthesis.", self.max_token_budget)
                break

            step_start = time.time()
            decision = self._decide_next_step(state)
            if decision.updated_hypothesis:
                state.current_hypothesis = decision.updated_hypothesis

            step_trace = self._execute_decision(decision, state)
            step_trace.duration_ms = (time.time() - step_start) * 1000.0
            state.record_step(step_trace)

            # Stopping Condition Check
            if decision.action == AgentActionType.FINISH:
                state.stopping_condition_met = True
                break

        # Final Evidence Synthesis
        self._synthesize_final_answer(state)
        state.total_latency_seconds = time.time() - start_time
        state.token_metrics.total_latency_seconds = state.total_latency_seconds
        
        logger.info(
            "GraphScout finished in %.2fs with %d steps and %d total tokens.",
            state.total_latency_seconds,
            len(state.step_history),
            state.token_metrics.total_tokens,
        )
        return state

    def _decide_next_step(self, state: InvestigationState) -> OrchestratorDecision:
        """LLM-guided meta-decision engine selecting the optimal tool action."""
        system_prompt = (
            "You are the Master Orchestrator for GraphScout, an Agentic GraphRAG system on TigerGraph. "
            "Your objective is to answer complex multi-hop queries through dynamic tool routing:\n"
            "- 'entity_linking': extract new entity anchors from latest observations\n"
            "- 'graph_traversal': expand N-hop relationships around specific seed entities via TigerGraph GSQL\n"
            "- 'vector_search': query TigerGraph Vector DB for dense textual chunk context\n"
            "- 'evaluate_evidence': assess completeness, detect contradictions/superseded facts, and formulate gaps\n"
            "- 'finish': conclude investigation when sufficient evidence is accumulated."
        )

        discovered_nodes = [f"{n.canonical_name} ({n.entity_id})" for n in state.subgraph.nodes[:10]]
        known_gaps = [f"[{g.gap_id}] {g.description}" for g in state.identified_gaps if not g.resolved]

        user_prompt = f"""
USER QUERY:
{state.user_query}

CURRENT HYPOTHESIS:
{state.current_hypothesis}

ITERATION: {state.iteration_count} / {state.max_iterations}

DISCOVERED ENTITIES ({len(state.retrieved_entities)}):
{", ".join(state.retrieved_entities.keys()) if state.retrieved_entities else "None"}

SUBGRAPH NODES ({len(state.subgraph.nodes)}):
{", ".join(discovered_nodes) if discovered_nodes else "None"}

CHUNKS ACCUMULATED: {len(state.document_chunks)}

UNRESOLVED GAPS:
{chr(10).join(known_gaps) if known_gaps else "None identified yet."}

STEP HISTORY:
{chr(10).join(f"Step {s.step_index}: {s.action_taken.value} -> {s.reasoning}" for s in state.step_history[-3:]) if state.step_history else "Initial Step"}

Decide the best next action and return an OrchestratorDecision.
"""

        decision, usage = self.llm.generate_json(system_prompt, user_prompt, OrchestratorDecision)
        state.token_metrics.add(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        return decision

    def _execute_decision(self, decision: OrchestratorDecision, state: InvestigationState) -> AgentStepTrace:
        """Execute selected tool and update state."""
        action = decision.action
        discovered_entities: List[str] = []
        chunks_retrieved_count = 0
        summary = ""

        if action == AgentActionType.ENTITY_LINKING:
            entities, usage = self.graph_tool.link_entities(state.user_query)
            state.token_metrics.add(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
            for ent in entities:
                state.add_entity(EntityNode(entity_id=ent.replace(" ", "_"), canonical_name=ent))
                discovered_entities.append(ent)
            summary = f"Linked {len(entities)} entity anchors."

        elif action == AgentActionType.VECTOR_SEARCH:
            queries = decision.search_queries or [state.user_query]
            for q in queries:
                chunks, usage = self.vector_tool.search(q, top_k=3)
                state.token_metrics.add(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
                for c in chunks:
                    state.add_chunk(c)
                chunks_retrieved_count += len(chunks)
            summary = f"Retrieved {chunks_retrieved_count} chunks using {len(queries)} semantic queries."

        elif action == AgentActionType.GRAPH_TRAVERSAL:
            seeds = decision.seed_entities or list(state.retrieved_entities.keys())[:3]
            subgraph = self.graph_tool.traverse_subgraph(seeds, max_hops=decision.max_hops)
            state.retrieved_subgraphs = state.retrieved_subgraphs.merge(subgraph)

            for node in subgraph.nodes:
                state.add_entity(node)
                discovered_entities.append(node.canonical_name)

            prov_chunks = self.tg_client.get_entity_provenance(seeds, max_chunks=5)
            for c in prov_chunks:
                state.add_chunk(c)

            summary = f"Traversed {len(subgraph.nodes)} nodes & {len(subgraph.edges)} edges around {seeds}."

        elif action == AgentActionType.EVALUATE_EVIDENCE:
            verdict, usage = self.evaluator_tool.evaluate(
                state.user_query,
                state.current_hypothesis,
                state.retrieved_subgraphs,
                state.document_chunks,
                state.identified_gaps,
            )
            state.token_metrics.add(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
            state.evaluation = verdict
            state.identified_gaps.extend(verdict.knowledge_gaps)
            summary = f"Evaluated completeness: score={verdict.completeness_score:.2f}, sufficient={verdict.has_sufficient_evidence}"

            if verdict.has_sufficient_evidence:
                state.stopping_condition_met = True

        elif action == AgentActionType.FINISH:
            summary = "Agent concluded evidence collection."

        return AgentStepTrace(
            step_index=state.iteration_count + 1,
            action_taken=action,
            reasoning=decision.reasoning,
            tool_inputs=decision.model_dump(),
            tool_outputs_summary=summary,
            entities_discovered=discovered_entities,
            chunks_retrieved_count=chunks_retrieved_count,
        )

    def _synthesize_final_answer(self, state: InvestigationState) -> None:
        """Synthesize final structured answer referencing multi-hop graph paths and chunks."""
        system_prompt = (
            "You are GraphScout, an elite investigative reasoning engine on TigerGraph. "
            "Synthesize a rigorous, evidence-backed answer to the user query using the multi-hop subgraphs and text chunks. "
            "Include explicit citations to entities and chunk identifiers."
        )

        subgraph_nodes = [f"- {n.canonical_name} ({n.entity_type})" for n in state.subgraph.nodes]
        subgraph_edges = [f"- {e.source_id} -[{e.relation_type}]-> {e.target_id} (conf={e.confidence})" for e in state.subgraph.edges]
        chunks_text = [f"[{c_id}] {c.text_content}" for c_id, c in state.document_chunks.items()]

        user_prompt = f"""
USER QUERY:
{state.user_query}

WORKING HYPOTHESIS:
{state.current_hypothesis}

GRAPH RELATIONS:
{chr(10).join(subgraph_edges) if subgraph_edges else "None"}

GRAPH NODES:
{chr(10).join(subgraph_nodes) if subgraph_nodes else "None"}

DOCUMENT EVIDENCE:
{chr(10).join(chunks_text) if chunks_text else "None"}

Please provide a detailed final answer, key findings, and citations.
"""

        res, usage = self.llm.generate_json(system_prompt, user_prompt, SynthesisResult)
        state.token_metrics.add(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        state.final_answer = res.answer
        state.citation_references = res.citations
