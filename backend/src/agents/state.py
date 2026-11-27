"""GraphScout Agent State & Memory Schema.

Defines Pydantic models and TypedDict schemas for representing graph evidence,
retrieved chunks, multi-hop subgraphs, reasoning traces, knowledge gaps, and token usage.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class AgentActionType(str, Enum):
    """Supported agent actions in the autonomous decision loop."""
    ENTITY_LINKING = "entity_linking"
    GRAPH_TRAVERSAL = "graph_traversal"
    VECTOR_SEARCH = "vector_search"
    FIND_EVENTS = "find_events"
    EVALUATE_EVIDENCE = "evaluate_evidence"
    FINISH = "finish"


class EntityNode(BaseModel):
    """Representation of an entity node retrieved or extracted in GraphScout."""
    entity_id: str
    canonical_name: str
    entity_type: str = "Unknown"
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    importance_score: float = 1.0
    source_hops: int = 0
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityRelation(BaseModel):
    """Representation of an edge / relationship between two entities."""
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0
    confidence: float = 1.0
    evidence_snippet: Optional[str] = None
    provenance_chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubgraphData(BaseModel):
    """Represents a localized multi-hop knowledge graph structure."""
    nodes: List[EntityNode] = Field(default_factory=list)
    edges: List[EntityRelation] = Field(default_factory=list)
    center_entities: List[str] = Field(default_factory=list)
    depth: int = 1

    def merge(self, other: SubgraphData) -> SubgraphData:
        """Merge another subgraph into this one, deduplicating nodes and edges."""
        node_map = {n.entity_id: n for n in self.nodes}
        for node in other.nodes:
            if node.entity_id not in node_map:
                node_map[node.entity_id] = node
            else:
                existing = node_map[node.entity_id]
                existing.aliases = list(set(existing.aliases + node.aliases))
                existing.confidence = max(existing.confidence, node.confidence)

        edge_keys = {(e.source_id, e.target_id, e.relation_type) for e in self.edges}
        merged_edges = list(self.edges)
        for edge in other.edges:
            key = (edge.source_id, edge.target_id, edge.relation_type)
            if key not in edge_keys:
                merged_edges.append(edge)
                edge_keys.add(key)

        return SubgraphData(
            nodes=list(node_map.values()),
            edges=merged_edges,
            center_entities=list(set(self.center_entities + other.center_entities)),
            depth=max(self.depth, other.depth),
        )


class DocumentChunk(BaseModel):
    """Document text segment with vector and provenance metadata."""
    chunk_id: str
    doc_id: Optional[str] = None
    text_content: str
    section_header: Optional[str] = None
    score: float = 0.0
    token_count: int = 0
    associated_entities: List[str] = Field(default_factory=list)
    is_superseded: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeGap(BaseModel):
    """Identified missing information required to answer the query."""
    gap_id: str
    description: str
    target_entity: Optional[str] = None
    relation_sought: Optional[str] = None
    suggested_strategy: Literal["graph", "vector", "both"] = "both"
    priority: int = 1
    resolved: bool = False


class AgentStepTrace(BaseModel):
    """Audit trace of a single decision step executed by the Orchestrator."""
    step_index: int
    action_taken: AgentActionType
    reasoning: str
    tool_inputs: Dict[str, Any] = Field(default_factory=dict)
    tool_outputs_summary: str = ""
    entities_discovered: List[str] = Field(default_factory=list)
    chunks_retrieved_count: int = 0
    duration_ms: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class TokenMetrics(BaseModel):
    """Tracks token consumption and latency across all agent invocations."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    calls_count: int = 0
    total_latency_seconds: float = 0.0

    def add(self, prompt: int, completion: int, rate_per_1k_prompt: float = 0.005, rate_per_1k_comp: float = 0.015):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += (prompt + completion)
        self.calls_count += 1
        self.estimated_cost_usd += (prompt / 1000.0 * rate_per_1k_prompt) + (completion / 1000.0 * rate_per_1k_comp)


class EvaluationVerdict(BaseModel):
    """Output from the Evaluator Agent regarding evidence completeness and source conflicts."""
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    has_sufficient_evidence: bool = False
    evidence_contradictions_found: bool = False
    conflicts_identified: List[str] = Field(default_factory=list)
    knowledge_gaps: List[KnowledgeGap] = Field(default_factory=list)
    confidence_rationale: str = ""


class InvestigationState(BaseModel):
    """Core state and memory container for the GraphScout autonomous loop."""
    # 1. User & Hypothesis State
    user_query: str
    current_hypothesis: str = "Initial hypothesis pending evidence collection."
    original_query_plan: Optional[str] = None

    # 2. Graph & Subgraph Evidence
    retrieved_entities: Dict[str, EntityNode] = Field(default_factory=dict)
    retrieved_subgraphs: SubgraphData = Field(default_factory=SubgraphData)

    # 3. Vector / Unstructured Document Chunks
    document_chunks: Dict[str, DocumentChunk] = Field(default_factory=dict)

    # 3b. Structured event-query results (find_events tables, exact counts)
    event_findings: List[str] = Field(default_factory=list)

    # 4. Gaps & Audit Trace
    identified_gaps: List[KnowledgeGap] = Field(default_factory=list)
    step_history: List[AgentStepTrace] = Field(default_factory=list)

    # 5. Performance & Metrics
    token_metrics: TokenMetrics = Field(default_factory=TokenMetrics)
    start_time: float = Field(default_factory=time.time)
    total_latency_seconds: float = 0.0

    # 6. Loop Control & Termination
    iteration_count: int = 0
    max_iterations: int = 6
    stopping_condition_met: bool = False
    evaluation: Optional[EvaluationVerdict] = None
    final_answer: Optional[str] = None
    citation_references: List[str] = Field(default_factory=list)

    # Backwards compatibility properties
    @property
    def subgraph(self) -> SubgraphData:
        return self.retrieved_subgraphs

    @subgraph.setter
    def subgraph(self, value: SubgraphData) -> None:
        self.retrieved_subgraphs = value

    @property
    def is_finished(self) -> bool:
        return self.stopping_condition_met

    @is_finished.setter
    def is_finished(self, value: bool) -> None:
        self.stopping_condition_met = value

    @property
    def current_iteration(self) -> int:
        return self.iteration_count

    @current_iteration.setter
    def current_iteration(self, value: int) -> None:
        self.iteration_count = value

    def add_entity(self, entity: EntityNode) -> None:
        """Register or update an entity in the state."""
        if entity.entity_id in self.retrieved_entities:
            existing = self.retrieved_entities[entity.entity_id]
            existing.aliases = list(set(existing.aliases + entity.aliases))
            existing.confidence = max(existing.confidence, entity.confidence)
        else:
            self.retrieved_entities[entity.entity_id] = entity

    def add_chunk(self, chunk: DocumentChunk) -> None:
        """Register or update a document chunk in the state."""
        self.document_chunks[chunk.chunk_id] = chunk

    def record_step(self, step: AgentStepTrace) -> None:
        """Record an execution step into the audit history."""
        self.step_history.append(step)
        self.iteration_count += 1


# Alias for compatibility
GraphScoutState = InvestigationState
