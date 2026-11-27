"""Tests for ground-truth benchmark metrics and regressions fixed alongside them."""

from src.agents.state import DocumentChunk
from src.db.memory_graph import InMemoryGraphClient
from src.evaluation.metrics import answer_accuracy, context_recall, extract_ground_truth
from src.utils.llm_client import LLMClient


def test_answer_accuracy_exact_and_partial():
    assert answer_accuracy("The winner was Chen Ding of China.", ["Chen Ding"]) == 1.0
    assert answer_accuracy("There were 5 events.", ["5"]) == 1.0
    assert answer_accuracy("There were 15 events.", ["5"]) == 0.0  # no substring false-positive
    assert 0.0 < answer_accuracy("Ding won", ["Chen Ding"]) < 1.0
    assert answer_accuracy("anything", None) is None


def test_context_recall():
    assert context_recall("... gold: Chen Ding ...", ["Chen Ding"]) == 1.0
    assert context_recall("Ding was there", ["Chen Ding"]) == 0.5
    assert context_recall("", []) is None


def test_extract_ground_truth_formats():
    assert extract_ground_truth({"answer": ["5"]}) == ["5"]
    assert extract_ground_truth({"ground_truth": "Some text"}) == ["Some text"]
    assert extract_ground_truth({"question": "q"}) == []


def test_mock_embedding_is_deterministic():
    llm = LLMClient(api_key="")
    llm._openai_client = None
    assert llm.get_embedding("hello") == llm.get_embedding("hello")


def test_in_memory_graph_links_and_resolves_names():
    tg = InMemoryGraphClient()
    # Corpus doc: K-2 1000m canoe sprint at Eton Dorney, 2012 Summer
    assert tg.resolve_entity_ids(["Eton Dorney"]) == ["Venue_Eton_Dorney"]
    sg = tg.get_entity_subgraph(["Eton Dorney"], max_hops=2, max_neighbors=50)
    names = {n.canonical_name for n in sg.nodes}
    assert "Rudolf DombiRoland Kökény" in names
    assert any(e.relation_type == "WON_GOLD" for e in sg.edges)


def test_lexical_vector_search_finds_relevant_doc():
    tg = InMemoryGraphClient()
    hits = tg.vector_search([], top_k=5, query_text="canoe sprint K-2 1000 metres Eton Dorney 2012")
    assert hits
    assert any("Eton Dorney" in h.text_content for h in hits)


def test_provider_resolution(monkeypatch):
    from src.utils.llm_client import LLMClient, available_models

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    llm = LLMClient(model_name="gpt-4o")  # not a Groq model -> provider default
    assert llm.provider.name == "groq"
    assert llm.model_name == "openai/gpt-oss-120b"
    assert available_models()["provider"] == "groq"

    monkeypatch.setenv("GROQ_API_KEY", "")
    assert LLMClient().provider is None
    assert available_models()["live"] is False


def test_vector_search_with_upserted_embedding():
    """Upserted chunks carry a 'score' key; vector search must not crash on it."""
    llm = LLMClient(api_key="")
    llm._openai_client = None
    tg = InMemoryGraphClient()
    emb = llm.get_embedding("rowing at Eton Dorney")
    tg.upsert_chunk(DocumentChunk(chunk_id="c1", text_content="rowing at Eton Dorney"), embedding=emb)
    results = tg.vector_search(emb, top_k=1, min_score=0.9)
    assert results and results[0].chunk_id == "c1"
    assert results[0].score > 0.99
