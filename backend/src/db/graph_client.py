"""Graph backend interface and factory.

Backend choice (``GRAPH_BACKEND`` in the environment or ``backend/.env``):

* ``auto`` (default): Neo4j when ``NEO4J_URI`` is set, else in-memory. If Neo4j is configured
  but unreachable, logs an error and falls back to in-memory so the app still starts.
* ``neo4j``: Neo4j only; a connection failure raises instead of falling back.
* ``memory``: always in-memory.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple, runtime_checkable

from src.agents.state import DocumentChunk, EntityNode, EntityRelation, SubgraphData
from src.db.events import EventFilter

logger = logging.getLogger("GraphScout.GraphClient")


@runtime_checkable
class GraphClient(Protocol):
    """What the agent, pipelines and API need from a graph backend."""

    backend: str          # "neo4j" | "memory"
    mode_label: str       # human-readable name for the UI
    persistent: bool      # does data survive a restart?
    location: Optional[str]
    database: Optional[str]

    def resolve_entity_ids(self, seeds: List[str], max_matches_per_seed: int = 3) -> List[str]: ...

    def get_entity_subgraph(
        self, seed_entity_ids: List[str], max_hops: int = 2, max_neighbors: int = 15, min_confidence: float = 0.5
    ) -> SubgraphData: ...

    def get_entity_provenance(self, entity_ids: List[str], max_chunks: int = 10) -> List[DocumentChunk]: ...

    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
    ) -> List[DocumentChunk]: ...

    def find_events(self, event_filter: EventFilter) -> Tuple[int, List[Dict[str, Any]]]: ...

    def upsert_entity(self, entity: EntityNode) -> bool: ...

    def upsert_chunk(self, chunk: DocumentChunk, embedding: Optional[List[float]] = None) -> bool: ...

    def upsert_relation(self, relation: EntityRelation) -> bool: ...

    def load_documents(self, docs: Iterable[Dict[str, Any]]) -> int: ...

    def stats(self) -> Dict[str, int]: ...

    def close(self) -> None: ...


def create_graph_client(autoload: bool = True) -> GraphClient:
    """Build the configured graph backend.

    ``autoload`` only affects the in-memory backend: load the corpus at start-up (Neo4j keeps
    its data, so it is loaded once with ``python -m src.db.ingest_corpus``).
    """
    from src.db.memory_graph import InMemoryGraphClient
    from src.db.neo4j_client import Neo4jConfig, Neo4jGraphClient
    from src.utils.env import load_backend_env

    load_backend_env()
    choice = (os.environ.get("GRAPH_BACKEND") or "auto").strip().lower()
    if choice not in ("auto", "neo4j", "memory"):
        raise ValueError(f"GRAPH_BACKEND must be auto, neo4j or memory (got {choice!r})")

    config = Neo4jConfig.from_env()
    if choice == "neo4j" or (choice == "auto" and config.uri):
        try:
            return Neo4jGraphClient(config)
        except Exception as exc:
            if choice == "neo4j":
                raise
            logger.error(
                "Could not connect to Neo4j at %s (%s). FALLING BACK TO THE IN-MEMORY GRAPH: "
                "data will not be saved. Set GRAPH_BACKEND=neo4j to make this an error.",
                config.uri, exc,
            )

    return InMemoryGraphClient(autoload=autoload)
