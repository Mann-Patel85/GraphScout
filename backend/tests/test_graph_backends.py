"""Backend selection and Neo4j client logic (no Neo4j server needed)."""

import pytest

from src.agents.state import DocumentChunk
from src.db import graph_client
from src.db.ingest_corpus import document_to_graph
from src.db.memory_graph import InMemoryGraphClient
from src.db.neo4j_client import Neo4jGraphClient
from src.utils.embeddings import LOCAL_EMBEDDING_DIM

UNREACHABLE = "bolt://127.0.0.1:1"


def _set_env(monkeypatch, backend="", uri=""):
    monkeypatch.setenv("GRAPH_BACKEND", backend)
    monkeypatch.setenv("NEO4J_URI", uri)


def test_default_backend_is_memory(monkeypatch):
    _set_env(monkeypatch)
    client = graph_client.create_graph_client(autoload=False)
    assert isinstance(client, InMemoryGraphClient)


def test_auto_falls_back_to_memory_when_neo4j_unreachable(monkeypatch):
    _set_env(monkeypatch, uri=UNREACHABLE)
    client = graph_client.create_graph_client(autoload=False)
    assert client.backend == "memory"


def test_explicit_neo4j_raises_when_unreachable(monkeypatch):
    _set_env(monkeypatch, backend="neo4j", uri=UNREACHABLE)
    with pytest.raises(Exception):
        graph_client.create_graph_client(autoload=False)


def test_invalid_backend_name(monkeypatch):
    _set_env(monkeypatch, backend="tigergraph")
    with pytest.raises(ValueError):
        graph_client.create_graph_client(autoload=False)


def test_document_to_graph_links_chunk_to_all_entities():
    doc = {
        "doc_id": "Q1",
        "title": "Rowing at the 2012 Summer Olympics – Men's eight",
        "text": "[Infobox Olympic event]\n  event: Men's eight\n  games: 2012 Summer\n  venue: Eton Dorney\n  gold: Canada\n\nBody.",
    }
    rec = document_to_graph(doc)
    ids = [e.entity_id for e in rec.entities]
    assert ids == ["Q1", "Venue_Eton_Dorney", "Games_2012_Summer", "Athlete_Canada"]
    assert {r.relation_type for r in rec.relations} == {"HELD_AT", "PART_OF_GAMES", "WON_GOLD"}
    assert rec.chunk.associated_entities == ids
    assert all(r.provenance_chunk_id == "chunk_Q1" for r in rec.relations)


class FakeNeo4j(Neo4jGraphClient):
    """Neo4jGraphClient with the database replaced by canned query results."""

    def __init__(self, responses):
        self.responses = responses  # list of (substring of the query, rows)
        self.calls = []

    def _read(self, query, **params):
        self.calls.append((query, params))
        for needle, rows in self.responses:
            if needle in query:
                return rows
        return []


def test_neo4j_vector_search_converts_scores_and_filters():
    client = FakeNeo4j([("db.index.vector.queryNodes", [
        {"chunk_id": "a", "doc_id": "A", "text_content": "x", "section_header": "A", "token_count": 1, "score": 0.9},
        {"chunk_id": "b", "doc_id": "B", "text_content": "y", "section_header": "B", "token_count": 1, "score": 0.51},
    ])])
    hits = client.vector_search([], top_k=2, query_text="rowing eton dorney")
    # Neo4j's 0.9 -> cosine 0.8 (kept); 0.51 -> cosine 0.02 (below the 0.05 cut-off)
    assert [h.chunk_id for h in hits] == ["a"]
    assert hits[0].score == pytest.approx(0.8)
    assert len(client.calls[0][1]["vector"]) == LOCAL_EMBEDDING_DIM


def test_neo4j_vector_search_rejects_wrong_dimension_without_text():
    client = FakeNeo4j([])
    assert client.vector_search([0.1, 0.2], top_k=3) == []
    assert client.calls == []


def test_neo4j_subgraph_assembles_bfs_layers():
    edge = {"relation_type": "HELD_AT", "weight": 1.0, "confidence": 1.0, "evidence_snippet": "s", "provenance_chunk_id": "chunk_Q1"}
    client = FakeNeo4j([
        ("e.entity_id = $raw", [{"id": "Venue_Eton_Dorney"}]),  # name resolution
        ("e.entity_id IN $ids", [{"entity_id": "Venue_Eton_Dorney", "name": "Eton Dorney", "entity_type": "Venue", "description": ""}]),
        ("UNWIND $frontier", [
            {"from_id": "Venue_Eton_Dorney", "source_id": "Q1", "target_id": "Venue_Eton_Dorney", **edge,
             "entity_id": "Q1", "name": "Men's eight", "entity_type": "OlympicEvent", "description": "d"},
        ]),
    ])
    sg = client.get_entity_subgraph(["Eton Dorney"], max_hops=2)
    assert {n.entity_id: n.source_hops for n in sg.nodes} == {"Venue_Eton_Dorney": 0, "Q1": 1}
    assert len(sg.edges) == 1 and sg.edges[0].relation_type == "HELD_AT"
    hop_calls = [c for c in client.calls if "UNWIND $frontier" in c[0]]
    assert hop_calls[0][1]["frontier"] == ["Venue_Eton_Dorney"]
    assert hop_calls[1][1]["frontier"] == ["Q1"]  # second hop expands only newly found nodes


def test_neo4j_chunk_row_uses_local_embedding_and_mentions():
    row = Neo4jGraphClient._chunk_row(DocumentChunk(chunk_id="c", text_content="rowing", associated_entities=["Q1"]))
    assert len(row["embedding"]) == LOCAL_EMBEDDING_DIM
    assert row["mentions"] == ["Q1"]
