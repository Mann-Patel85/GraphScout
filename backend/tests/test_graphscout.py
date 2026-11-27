"""Unit tests for GraphScout components."""

import pytest
from src.agents.state import (
    AgentActionType,
    DocumentChunk,
    EntityNode,
    EntityRelation,
    InvestigationState,
    SubgraphData,
)
from src.agents.orchestrator import OrchestratorAgent
from src.db.memory_graph import InMemoryGraphClient
from src.utils.llm_client import LLMClient
from src.pipelines.standard_rag import StandardRAGPipeline
from src.pipelines.graph_rag import GraphRAGPipeline
from src.pipelines.agentic_rag import AgenticRAGPipeline


@pytest.fixture
def tg_client():
    client = InMemoryGraphClient()
    # Seed sample entities
    e1 = EntityNode(entity_id="Company_A", canonical_name="Company A", entity_type="Org")
    e2 = EntityNode(entity_id="Company_B", canonical_name="Company B", entity_type="Org")
    client.upsert_entity(e1)
    client.upsert_entity(e2)
    client.upsert_relation(
        EntityRelation(source_id="Company_A", target_id="Company_B", relation_type="PARTNERS_WITH")
    )
    return client


@pytest.fixture
def llm_client():
    return LLMClient()


def test_subgraph_merge():
    sg1 = SubgraphData(
        nodes=[EntityNode(entity_id="N1", canonical_name="Node 1")],
        edges=[EntityRelation(source_id="N1", target_id="N2", relation_type="LINKED")],
    )
    sg2 = SubgraphData(
        nodes=[EntityNode(entity_id="N2", canonical_name="Node 2")],
        edges=[EntityRelation(source_id="N2", target_id="N3", relation_type="CONNECTED")],
    )
    merged = sg1.merge(sg2)
    assert len(merged.nodes) == 2
    assert len(merged.edges) == 2


def test_investigation_state():
    state = InvestigationState(user_query="What is the relation?")
    state.add_entity(EntityNode(entity_id="E1", canonical_name="Entity 1"))
    assert "E1" in state.retrieved_entities
    assert state.iteration_count == 0
    assert not state.stopping_condition_met


def test_orchestrator_autonomous_run(tg_client, llm_client):
    orchestrator = OrchestratorAgent(tg_client, llm_client, max_iterations=4)
    state = orchestrator.run("What is the connection between Company A and Company B?")
    assert state.final_answer is not None
    assert state.iteration_count > 0
    assert state.token_metrics.total_tokens > 0


def test_pipelines_execution(tg_client, llm_client):
    query = "Test query"
    std_pipe = StandardRAGPipeline(tg_client, llm_client)
    res_std = std_pipe.run(query)
    assert res_std.answer != ""

    graph_pipe = GraphRAGPipeline(tg_client, llm_client)
    res_graph = graph_pipe.run(query)
    assert res_graph.answer != ""

    orchestrator = OrchestratorAgent(tg_client, llm_client, max_iterations=3)
    agentic_pipe = AgenticRAGPipeline(orchestrator)
    res_agentic = agentic_pipe.run(query)
    assert res_agentic.answer != ""
