"""Neo4j graph backend (works with Neo4j AuraDB Free or any Neo4j 5.11+ server).

Data model::

    (:Entity {entity_id, name, name_lower, entity_type, description})
        Olympic events also carry their infobox fields: sport, event, games, year, season,
        venue, date, competitors, nations, gold, gold_noc (+ *_norm copies for matching)
    (:Entity)-[:RELATED_TO {relation_type, weight, confidence, evidence_snippet, provenance_chunk_id}]->(:Entity)
    (:Chunk {chunk_id, doc_id, text_content, section_header, token_count, embedding})
    (:Chunk)-[:MENTIONS]->(:Entity)

Chunk embeddings come from the local hashed embedder (``src.utils.embeddings``), for stored
chunks and for queries alike. That keeps vector search consistent and free whichever LLM
provider is configured.
"""

from __future__ import annotations

import logging
import os
from itertools import islice
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.agents.state import DocumentChunk, EntityNode, EntityRelation, SubgraphData
from src.db.events import EventFilter, apply_event_filter, normalize
from src.db.ingest_corpus import document_to_graph
from src.utils.embeddings import LOCAL_EMBEDDING_DIM, local_embed

logger = logging.getLogger("GraphScout.Neo4j")

VECTOR_INDEX = "chunk_embedding"
VECTOR_OVERFETCH = 20       # candidates requested per result wanted...
VECTOR_MIN_CANDIDATES = 100  # ...but never fewer than this
MAX_HOPS = 4  # hard cap: each hop is one query, and graph hubs (a Games node) fan out fast

# Applied (idempotently) on every connect. Also shown on the UI's Schema tab.
SCHEMA_STATEMENTS: List[str] = [
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
    "CREATE INDEX entity_name_lower IF NOT EXISTS FOR (e:Entity) ON (e.name_lower)",
    "CREATE INDEX entity_sport IF NOT EXISTS FOR (e:Entity) ON (e.sport)",
    "CREATE INDEX entity_year IF NOT EXISTS FOR (e:Entity) ON (e.year)",
    (
        f"CREATE VECTOR INDEX {VECTOR_INDEX} IF NOT EXISTS FOR (c:Chunk) ON (c.embedding) "
        f"OPTIONS {{indexConfig: {{`vector.dimensions`: {LOCAL_EMBEDDING_DIM}, "
        f"`vector.similarity_function`: 'cosine'}}}}"
    ),
]

UPSERT_ENTITIES = """
UNWIND $rows AS row
MERGE (e:Entity {entity_id: row.entity_id})
ON CREATE SET e.name = row.name, e.name_lower = row.name_lower, e.entity_type = row.entity_type
SET e.description = CASE WHEN row.description <> '' THEN row.description ELSE coalesce(e.description, '') END
FOREACH (_ IN CASE WHEN row.overwrite THEN [1] ELSE [] END |
    SET e.name = row.name, e.name_lower = row.name_lower, e.entity_type = row.entity_type)
SET e += row.props
"""

UPSERT_RELATIONS = """
UNWIND $rows AS row
MERGE (s:Entity {entity_id: row.source_id})
ON CREATE SET s.name = row.source_id, s.name_lower = toLower(row.source_id), s.entity_type = 'Unknown'
MERGE (t:Entity {entity_id: row.target_id})
ON CREATE SET t.name = row.target_id, t.name_lower = toLower(row.target_id), t.entity_type = 'Unknown'
MERGE (s)-[r:RELATED_TO {relation_type: row.relation_type}]->(t)
SET r.weight = row.weight, r.confidence = row.confidence,
    r.evidence_snippet = row.evidence_snippet, r.provenance_chunk_id = row.provenance_chunk_id
"""

UPSERT_CHUNKS = """
UNWIND $rows AS row
MERGE (c:Chunk {chunk_id: row.chunk_id})
SET c.doc_id = row.doc_id, c.text_content = row.text_content, c.section_header = row.section_header,
    c.token_count = row.token_count, c.embedding = row.embedding
WITH c, row
UNWIND row.mentions AS eid
MATCH (e:Entity {entity_id: eid})
MERGE (c)-[:MENTIONS]->(e)
"""

# One BFS hop: up to $k relationships per frontier node.
EXPAND_HOP = """
UNWIND $frontier AS fid
MATCH (s:Entity {entity_id: fid})-[r:RELATED_TO]-(t:Entity)
WHERE coalesce(r.confidence, 1.0) >= $min_confidence
WITH s, r, t ORDER BY t.entity_id
WITH s, collect({r: r, t: t})[..$k] AS pairs
UNWIND pairs AS p
WITH s, p.r AS r, p.t AS t
RETURN s.entity_id AS from_id,
       startNode(r).entity_id AS source_id, endNode(r).entity_id AS target_id,
       r.relation_type AS relation_type, r.weight AS weight, r.confidence AS confidence,
       r.evidence_snippet AS evidence_snippet, r.provenance_chunk_id AS provenance_chunk_id,
       t.entity_id AS entity_id, t.name AS name, t.entity_type AS entity_type, t.description AS description
"""

PROVENANCE = """
MATCH (e:Entity)<-[:MENTIONS]-(c:Chunk)
WHERE e.entity_id IN $ids
WITH c, max(CASE WHEN c.chunk_id = 'chunk_' + e.entity_id THEN 1.0 ELSE 0.9 END) AS score
RETURN c.chunk_id AS chunk_id, c.doc_id AS doc_id, c.text_content AS text_content,
       c.section_header AS section_header, c.token_count AS token_count, score
ORDER BY score DESC, chunk_id
LIMIT $k
"""

VECTOR_QUERY = f"""
CALL db.index.vector.queryNodes('{VECTOR_INDEX}', $k, $vector) YIELD node, score
RETURN node.chunk_id AS chunk_id, node.doc_id AS doc_id, node.text_content AS text_content,
       node.section_header AS section_header, node.token_count AS token_count, score
"""

# Coarse pre-filter: every CONTAINS here is a superset of the exact rule applied afterwards
# in Python (src/db/events.py), so both backends return identical results.
FIND_EVENTS = """
MATCH (e:Entity) WHERE e.sport IS NOT NULL
  AND ($year IS NULL OR e.year = $year)
  AND ($season IS NULL OR e.season = $season)
  AND ($year_before IS NULL OR e.year < $year_before)
  AND ($sport IS NULL OR e.sport_norm CONTAINS $sport)
  AND ($event IS NULL OR e.title_norm CONTAINS $event)
  AND ($venue IS NULL OR e.venue_norm CONTAINS $venue)
  AND ($min_competitors IS NULL OR e.competitors > $min_competitors)
  AND ($max_competitors IS NULL OR e.competitors < $max_competitors)
RETURN e.entity_id AS entity_id, e.name AS title, e.sport AS sport, e.event AS event, e.games AS games,
       e.year AS year, e.season AS season, e.venue AS venue, e.date AS date,
       e.competitors AS competitors, e.nations AS nations, e.gold AS gold, e.gold_noc AS gold_noc
"""

STATS = """
MATCH (e:Entity) WITH count(e) AS entities
OPTIONAL MATCH ()-[r:RELATED_TO]->() WITH entities, count(r) AS relations
OPTIONAL MATCH (c:Chunk) RETURN entities, relations, count(c) AS chunks
"""

# Shown on the UI's Schema tab next to SCHEMA_STATEMENTS.
QUERIES = [
    {"name": "expand_hop", "parameters": "$frontier, $k, $min_confidence",
     "description": "One BFS hop over RELATED_TO, capped at $k neighbours per node; run once per hop.", "cypher": EXPAND_HOP},
    {"name": "provenance", "parameters": "$ids, $k",
     "description": "Text chunks that MENTION the given entities, the entity's own document first.", "cypher": PROVENANCE},
    {"name": "find_events", "parameters": "$sport, $event, $year, $season, $year_before, $venue, $min/max_competitors",
     "description": "Structured filter over Olympic events (counts, superlatives, 'immediately before', venue + date).", "cypher": FIND_EVENTS},
    {"name": "vector_search", "parameters": "$vector, $k",
     "description": "Nearest chunks from the native vector index (cosine).", "cypher": VECTOR_QUERY},
]


class Neo4jConfig:
    """Connection settings, read from NEO4J_* variables (the names Aura's credentials file uses)."""

    def __init__(self, uri: str, username: str = "neo4j", password: str = "", database: str = "neo4j"):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database

    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        from src.utils.env import load_backend_env
        load_backend_env()
        env = os.environ.get
        return cls(
            uri=env("NEO4J_URI", ""),
            username=env("NEO4J_USERNAME", "neo4j"),
            password=env("NEO4J_PASSWORD", ""),
            database=env("NEO4J_DATABASE", "") or "neo4j",
        )


class Neo4jGraphClient:
    """Graph client backed by a Neo4j database."""

    backend = "neo4j"
    mode_label = "Neo4j"
    persistent = True

    def __init__(self, config: Neo4jConfig, batch_size: int = 100):
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
            raise RuntimeError("The 'neo4j' package is not installed: pip install -r requirements.txt") from exc
        if not config.uri:
            raise ValueError("NEO4J_URI is not set")

        self.config = config
        self.batch_size = batch_size
        self.location = config.uri
        self.database = config.database
        # Silence server notifications such as "property key does not exist yet" on an empty database.
        self._driver = GraphDatabase.driver(
            config.uri, auth=(config.username, config.password), notifications_min_severity="OFF"
        )
        try:
            self._driver.verify_connectivity()
            for statement in SCHEMA_STATEMENTS:
                self._write(statement)
        except Exception:
            self._driver.close()
            raise

        counts = self.stats()
        logger.info("Connected to Neo4j at %s (database %s): %s", config.uri, config.database, counts)
        if counts["chunks"] == 0:
            logger.warning(
                "The Neo4j database is empty. Load the corpus with "
                "`python -m src.db.ingest_corpus --all` (from backend/) or the UI's ingest button."
            )

    # ------------------------------------------------------------------
    # Query plumbing
    # ------------------------------------------------------------------
    def _read(self, query: str, **params: Any) -> List[Dict[str, Any]]:
        from neo4j import RoutingControl
        records, _, _ = self._driver.execute_query(
            query, parameters_=params, database_=self.database, routing_=RoutingControl.READ
        )
        return [r.data() for r in records]

    def _write(self, query: str, **params: Any) -> None:
        self._driver.execute_query(query, parameters_=params, database_=self.database)

    def close(self) -> None:
        self._driver.close()

    # ------------------------------------------------------------------
    # Writes (errors propagate so ingestion fails loudly)
    # ------------------------------------------------------------------
    def load_documents(self, docs: Iterable[Dict[str, Any]]) -> int:
        """Batch-ingest corpus documents. Returns how many were processed."""
        it = iter(docs)
        total = 0
        while batch := list(islice(it, self.batch_size)):
            entities: Dict[str, Dict[str, Any]] = {}
            relations: List[Dict[str, Any]] = []
            chunks: List[Dict[str, Any]] = []
            for doc in batch:
                records = document_to_graph(doc)
                for entity in records.entities:
                    row = self._entity_row(entity, overwrite=False)
                    # Within a batch keep the first row, but take a description from any duplicate.
                    kept = entities.setdefault(entity.entity_id, row)
                    if not kept["description"] and row["description"]:
                        kept["description"] = row["description"]
                relations.extend(self._relation_row(r) for r in records.relations)
                if records.chunk:
                    chunks.append(self._chunk_row(records.chunk))
            self._write(UPSERT_ENTITIES, rows=list(entities.values()))
            self._write(UPSERT_RELATIONS, rows=relations)
            self._write(UPSERT_CHUNKS, rows=chunks)
            total += len(batch)
            logger.info("Ingested %d documents into Neo4j...", total)
        return total

    def upsert_entity(self, entity: EntityNode) -> bool:
        self._write(UPSERT_ENTITIES, rows=[self._entity_row(entity, overwrite=True)])
        return True

    def upsert_chunk(self, chunk: DocumentChunk, embedding: Optional[List[float]] = None) -> bool:
        """Store a chunk. ``embedding`` is ignored: chunks always get the local embedding, so the
        vector index has one consistent dimension and metric."""
        self._write(UPSERT_CHUNKS, rows=[self._chunk_row(chunk)])
        return True

    def upsert_relation(self, relation: EntityRelation) -> bool:
        self._write(UPSERT_RELATIONS, rows=[self._relation_row(relation)])
        return True

    @staticmethod
    def _entity_row(entity: EntityNode, overwrite: bool) -> Dict[str, Any]:
        attrs = entity.metadata or {}
        props: Dict[str, Any] = {}
        if attrs.get("sport"):
            props = {k: v for k, v in attrs.items() if isinstance(v, (str, int, float))}
            props.update(
                sport_norm=normalize(attrs.get("sport")),
                title_norm=normalize(entity.canonical_name),
                venue_norm=normalize(attrs.get("venue")),
            )
        return {
            "entity_id": entity.entity_id,
            "name": entity.canonical_name,
            "name_lower": entity.canonical_name.strip().lower(),
            "entity_type": entity.entity_type,
            "description": entity.description or "",
            "overwrite": overwrite,
            "props": props,
        }

    @staticmethod
    def _relation_row(relation: EntityRelation) -> Dict[str, Any]:
        return {
            "source_id": relation.source_id,
            "target_id": relation.target_id,
            "relation_type": relation.relation_type,
            "weight": relation.weight,
            "confidence": relation.confidence,
            "evidence_snippet": relation.evidence_snippet or "",
            "provenance_chunk_id": relation.provenance_chunk_id or "",
        }

    @staticmethod
    def _chunk_row(chunk: DocumentChunk) -> Dict[str, Any]:
        return {
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id or "",
            "text_content": chunk.text_content,
            "section_header": chunk.section_header or "",
            "token_count": chunk.token_count or len(chunk.text_content.split()),
            "embedding": local_embed(f"{chunk.section_header or ''}\n{chunk.text_content}"),
            "mentions": list(chunk.associated_entities),
        }

    # ------------------------------------------------------------------
    # Reads (errors are logged and return empty results, so one failed
    # lookup does not abort a whole investigation)
    # ------------------------------------------------------------------
    def stats(self) -> Dict[str, int]:
        try:
            rows = self._read(STATS)
            return {k: int(rows[0][k]) for k in ("entities", "relations", "chunks")}
        except Exception as exc:
            logger.error("Neo4j stats query failed: %s", exc)
            return {"entities": 0, "relations": 0, "chunks": 0}

    def resolve_entity_ids(self, seeds: List[str], max_matches_per_seed: int = 3) -> List[str]:
        """Map seed strings (ids or free-text names from the LLM) to entity ids:
        exact id, then exact name, then shortest names containing (or contained in) the seed."""
        resolved: List[str] = []
        try:
            for seed in seeds:
                name = seed.replace("_", " ").strip().lower()
                exact = self._read(
                    "MATCH (e:Entity) WHERE e.entity_id = $raw OR e.name_lower = $name "
                    "RETURN e.entity_id AS id ORDER BY (e.entity_id = $raw) DESC, e.entity_id LIMIT 1",
                    raw=seed, name=name,
                )
                if exact:
                    resolved.append(exact[0]["id"])
                    continue
                if len(name) < 4:
                    continue
                fuzzy = self._read(
                    "MATCH (e:Entity) WHERE e.name_lower CONTAINS $name "
                    "OR (size(e.name_lower) >= 5 AND $name CONTAINS e.name_lower) "
                    "RETURN e.entity_id AS id ORDER BY size(e.name_lower), e.entity_id LIMIT $k",
                    name=name, k=max_matches_per_seed,
                )
                resolved.extend(r["id"] for r in fuzzy)
        except Exception as exc:
            logger.error("Neo4j entity resolution failed: %s", exc)
        return list(dict.fromkeys(resolved))

    def find_events(self, event_filter: EventFilter) -> Tuple[int, List[Dict[str, Any]]]:
        """Olympic events matching ``event_filter``: (total matches, shown rows)."""
        f = event_filter
        try:
            candidates = self._read(
                FIND_EVENTS,
                year=f.year, season=f.season, year_before=f.year_before,
                sport=normalize(f.sport) or None, event=normalize(f.event) or None, venue=normalize(f.venue) or None,
                min_competitors=f.min_competitors, max_competitors=f.max_competitors,
            )
        except Exception as exc:
            logger.error("Neo4j find_events failed: %s", exc)
            return 0, []
        return apply_event_filter(candidates, f)

    def get_entity_subgraph(
        self,
        seed_entity_ids: List[str],
        max_hops: int = 2,
        max_neighbors: int = 15,
        min_confidence: float = 0.5,
    ) -> SubgraphData:
        """BFS from the seeds (ids or names), one query per hop."""
        seeds = self.resolve_entity_ids(seed_entity_ids)
        hops = max(0, min(int(max_hops), MAX_HOPS))
        visited: Dict[str, EntityNode] = {}
        edges: Dict[tuple, EntityRelation] = {}
        try:
            for row in self._read(
                "MATCH (e:Entity) WHERE e.entity_id IN $ids "
                "RETURN e.entity_id AS entity_id, e.name AS name, e.entity_type AS entity_type, e.description AS description",
                ids=seeds,
            ):
                visited[row["entity_id"]] = self._node(row, 0)

            frontier = list(visited)
            for hop in range(1, hops + 1):
                if not frontier:
                    break
                next_frontier: List[str] = []
                for row in self._read(
                    EXPAND_HOP, frontier=frontier, k=max_neighbors, min_confidence=min_confidence
                ):
                    key = (row["source_id"], row["target_id"], row["relation_type"])
                    if key not in edges:
                        edges[key] = EntityRelation(
                            source_id=row["source_id"],
                            target_id=row["target_id"],
                            relation_type=row["relation_type"] or "RELATED_TO",
                            weight=row["weight"] if row["weight"] is not None else 1.0,
                            confidence=row["confidence"] if row["confidence"] is not None else 1.0,
                            evidence_snippet=row["evidence_snippet"] or None,
                            provenance_chunk_id=row["provenance_chunk_id"] or None,
                        )
                    if row["entity_id"] not in visited:
                        visited[row["entity_id"]] = self._node(row, hop)
                        next_frontier.append(row["entity_id"])
                frontier = next_frontier
        except Exception as exc:
            logger.error("Neo4j subgraph traversal failed: %s", exc)

        return SubgraphData(nodes=list(visited.values()), edges=list(edges.values()), center_entities=seeds, depth=max_hops)

    def get_entity_provenance(self, entity_ids: List[str], max_chunks: int = 10) -> List[DocumentChunk]:
        """Chunks that mention the given entities (ids or names), each entity's own document first."""
        ids = self.resolve_entity_ids(entity_ids)
        if not ids:
            return []
        try:
            return [self._chunk(row, row["score"], ids) for row in self._read(PROVENANCE, ids=ids, k=max_chunks)]
        except Exception as exc:
            logger.error("Neo4j provenance query failed: %s", exc)
            return []

    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
    ) -> List[DocumentChunk]:
        """Nearest chunks from the vector index. Pass ``query_text`` (preferred) to embed it with the
        same local embedder the chunks use; a raw ``query_embedding`` must match its dimension."""
        if query_text:
            vector, threshold = local_embed(query_text), 0.05  # same cut-off as the in-memory engine
        elif len(query_embedding) == LOCAL_EMBEDDING_DIM:
            vector, threshold = query_embedding, min_score
        else:
            logger.warning("vector_search got a %d-dim embedding and no query_text; skipping.", len(query_embedding))
            return []
        try:
            # The index is approximate (HNSW) and the sparse local embeddings make it miss close
            # matches, so fetch extra candidates and keep the best top_k.
            rows = self._read(VECTOR_QUERY, k=max(top_k * VECTOR_OVERFETCH, VECTOR_MIN_CANDIDATES), vector=vector)
        except Exception as exc:
            logger.error("Neo4j vector search failed: %s", exc)
            return []
        results = []
        for row in rows:
            cosine = 2.0 * float(row["score"]) - 1.0  # Neo4j reports cosine similarity as (1 + cos) / 2
            if cosine > threshold:
                results.append(self._chunk(row, cosine))
        results.sort(key=lambda c: c.score, reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------
    @staticmethod
    def _node(row: Dict[str, Any], hops: int) -> EntityNode:
        return EntityNode(
            entity_id=row["entity_id"],
            canonical_name=row.get("name") or row["entity_id"],
            entity_type=row.get("entity_type") or "Unknown",
            description=row.get("description") or None,
            source_hops=hops,
        )

    @staticmethod
    def _chunk(row: Dict[str, Any], score: float, entities: Optional[List[str]] = None) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=row["chunk_id"],
            doc_id=row.get("doc_id") or None,
            text_content=row.get("text_content") or "",
            section_header=row.get("section_header") or None,
            token_count=row.get("token_count") or 0,
            score=float(score),
            associated_entities=entities or [],
        )
