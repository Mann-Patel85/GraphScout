"""find_events: structured event filtering, and the agent using it end to end (scripted LLM)."""

import pytest

from src.agents.orchestrator import OrchestratorAgent
from src.db.events import EventFilter as F
from src.db.events import apply_event_filter, event_attributes, normalize
from src.db.memory_graph import InMemoryGraphClient
from src.db.neo4j_client import Neo4jGraphClient


@pytest.fixture(scope="module")
def graph():
    return InMemoryGraphClient()  # full corpus


def titles(graph, f):
    total, rows = graph.find_events(f)
    return total, [r["title"] for r in rows]


# Expected values below are the answers recorded in data/eval_public.jsonl.

def test_superlative_most_competitors(graph):
    total, rows = titles(graph, F(sport="Athletics", year=2008, sort_by="competitors", limit=1))
    assert total == 43
    assert rows == ["Athletics at the 2008 Summer Olympics – Men's marathon"]


def test_aggregation_counts_all_matches(graph):
    total, _ = graph.find_events(F(sport="Biathlon", year=2018, min_competitors=73, limit=1))
    assert total == 5


def test_immediately_before_year(graph):
    _, rows = graph.find_events(F(sport="Athletics", event="men's 20 kilometres walk", season="Summer",
                                  year_before=2016, sort_by="year", limit=1))
    assert rows[0]["year"] == 2012 and rows[0]["gold"] == "Chen Ding"


def test_venue_and_date(graph):
    _, rows = graph.find_events(F(venue="Richmond Olympic Oval", date="14 February 2010"))
    assert [r["gold"] for r in rows] == ["Martina Sáblíková"]


def test_date_without_year_in_infobox(graph):
    # Infobox says "30 July"; the question says "30 July" and the year separately.
    _, rows = graph.find_events(F(venue="ExCeL Exhibition Centre", date="30 July", year=2012))
    assert "Yana Shemyakina" in [r["gold"] for r in rows]


def test_ambiguous_venue_date_returns_every_match(graph):
    total, _ = graph.find_events(F(venue="Eton Dorney", date="6 to 8 August", year=2012))
    assert total == 4


def test_mens_does_not_match_womens(graph):
    _, rows = titles(graph, F(sport="Athletics", year=2008, event="men's 100 metres"))
    assert rows == ["Athletics at the 2008 Summer Olympics – Men's 100 metres"]


def test_sport_exact_then_substring_fallback(graph):
    exact, _ = graph.find_events(F(sport="Speed skating", year=2010))
    loose, rows = graph.find_events(F(sport="skiing", year=2010, limit=60))
    assert exact == 10  # not short-track
    assert {r["sport"] for r in rows} >= {"Alpine skiing", "Cross-country skiing"}


def test_date_word_boundaries():
    rows = [{"title": "x", "date": "14 August", "entity_id": "a"}]
    assert apply_event_filter(rows, F(date="4 August"))[0] == 0
    assert apply_event_filter(rows, F(date="14 August 2012"))[0] == 1


def test_normalize_quotes_and_dashes():
    assert normalize("Men’s  10 000 – Final") == "men's 10 000 - final"


def test_event_attributes_parses_numbers_and_games():
    attrs = event_attributes("Rowing at the 2012 Summer Olympics – Men's eight",
                             {"event": "Men's eight", "games": "2012 Summer", "competitors": "1,024", "nations": "8"})
    assert attrs["sport"] == "Rowing" and attrs["year"] == 2012 and attrs["season"] == "Summer"
    assert attrs["competitors"] == 1024 and attrs["event"] == "Men's eight"


def test_neo4j_find_events_pushes_down_and_applies_exact_rules():
    class Fake(Neo4jGraphClient):
        def __init__(self):
            self.params = None

        def _read(self, query, **params):
            self.params = params
            return [  # coarse CONTAINS lets women's through; the exact rule must drop it
                {"entity_id": "m", "title": "Athletics at the 2008 Summer Olympics – Men's 100 metres",
                 "sport": "Athletics", "year": 2008, "competitors": 80},
                {"entity_id": "w", "title": "Athletics at the 2008 Summer Olympics – Women's 100 metres",
                 "sport": "Athletics", "year": 2008, "competitors": 85},
            ]

    client = Fake()
    total, rows = client.find_events(F(sport="Athletics", year=2008, event="Men’s 100 metres"))
    assert client.params["year"] == 2008 and client.params["event"] == "men's 100 metres"
    assert total == 1 and rows[0]["entity_id"] == "m"


class ScriptedLLM:
    """Stands in for LLMClient: returns scripted orchestrator decisions and records prompts."""

    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.prompts = {}

    def generate_json(self, system_prompt, user_prompt, schema_cls):
        name = schema_cls.__name__
        self.prompts.setdefault(name, []).append(user_prompt)
        if name == "OrchestratorDecision":
            data = self.decisions.pop(0) if self.decisions else {"action": "finish", "reasoning": "done"}
        elif name == "SynthesisResult":
            data = {"answer": "Athletics at the 2008 Summer Olympics – Men's marathon"}
        elif name == "EvaluationVerdict":
            data = {"completeness_score": 1.0}
        else:  # EntityExtractionResult
            data = {"extracted_entities": ["2008 Summer Olympics"]}
        return schema_cls.model_validate(data), {"prompt_tokens": 1, "completion_tokens": 1}

    def get_embedding(self, text):
        return []


def test_agent_uses_find_events_and_feeds_synthesis(graph):
    llm = ScriptedLLM([
        {"action": "find_events", "reasoning": "superlative over all events",
         "event_filter": {"sport": "Athletics", "year": 2008, "sort_by": "competitors", "limit": 5}},
        {"action": "finish", "reasoning": "the table answers it"},
    ])
    state = OrchestratorAgent(graph, llm).run(
        "Which athletics event at the 2008 Summer Olympics had the highest number of competitors?"
    )
    assert state.step_history[0].action_taken.value == "find_events"
    assert "Matched 43 event(s)" in state.step_history[0].tool_outputs_summary
    assert "chunk_Q693595" in state.document_chunks  # marathon passage added as evidence
    synthesis_prompt = llm.prompts["SynthesisResult"][0]
    assert "43 matching event(s)" in synthesis_prompt and "Men's marathon" in synthesis_prompt
    # The second decision saw the table, so the orchestrator can stop once it has the answer.
    assert "Men's marathon" in llm.prompts["OrchestratorDecision"][1]


def test_agent_skips_empty_filter(graph):
    llm = ScriptedLLM([{"action": "find_events", "reasoning": "oops"}])
    state = OrchestratorAgent(graph, llm).run("anything")
    assert "skipped" in state.step_history[0].tool_outputs_summary


def test_traversal_provenance_ranked_by_question(graph):
    llm = ScriptedLLM([
        {"action": "graph_traversal", "reasoning": "venue", "seed_entities": ["Eton Dorney"], "max_hops": 1},
    ])
    state = OrchestratorAgent(graph, llm).run(
        "Who won the canoe sprint K-2 1000 metres held at Eton Dorney on 6 to 8 August at the 2012 Summer Olympics?"
    )
    assert "chunk_Q303623" in state.document_chunks  # the K-2 1000 m document, not an arbitrary Eton Dorney one
