"""Tests for GraphScout Modern Web Interface & FastAPI Endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.web.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "tigergraph" in data
    assert "datasets" in data
    assert data["datasets"]["corpus_documents"] > 0


def test_presets_endpoint(client):
    response = client.get("/api/presets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert "query" in data[0]


def test_schema_endpoint(client):
    response = client.get("/api/schema")
    assert response.status_code == 200
    data = response.json()
    assert data["schema_name"] == "GraphScoutKG"
    assert len(data["vertices"]) == 4
    assert len(data["edges"]) == 5
    assert len(data["installed_queries"]) == 3
    assert "gsql_code" in data
    assert len(data["gsql_code"]) > 50


def test_corpus_endpoints(client):
    # Test listing
    response = client.get("/api/corpus?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert len(data["documents"]) <= 5
    assert data["total"] > 0

    # Test single document
    doc_id = data["documents"][0]["doc_id"]
    doc_res = client.get(f"/api/corpus/{doc_id}")
    assert doc_res.status_code == 200
    doc_data = doc_res.json()
    assert doc_data["doc_id"] == doc_id
    assert "full_text" in doc_data


def test_investigate_endpoint(client):
    payload = {
        "query": "Who won the gold medal in the event held at Eton Dorney on 6 to 8 August at the 2012 Summer Olympics?",
        "model": "gpt-4o",
        "temperature": 0.1,
        "max_hops": 3,
        "completeness_threshold": 0.85,
        "token_budget": 8000,
    }
    response = client.post("/api/investigate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == payload["query"]
    assert "final_answer" in data
    assert "metrics" in data
    assert data["metrics"]["total_tokens"] > 0
    assert "steps" in data
    assert len(data["steps"]) > 0
    assert "subgraph" in data
    assert "nodes" in data["subgraph"]
    assert "edges" in data["subgraph"]


def test_benchmark_endpoint(client):
    payload = {
        "dataset": "sample",
        "limit": 1,
        "model": "gpt-4o",
        "temperature": 0.1,
    }
    response = client.post("/api/benchmark", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["questions_evaluated"] == 1
    assert "summary" in data
    assert "standard_rag" in data["summary"]
    assert "graph_rag" in data["summary"]
    assert "agentic_rag" in data["summary"]
    assert len(data["rows"]) == 3  # 1 question x 3 pipelines


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "GraphScout API"
    assert data["status"] == "online"
    assert data["version"] == "2.0.0"
