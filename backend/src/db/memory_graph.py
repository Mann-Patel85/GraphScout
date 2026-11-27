"""In-memory graph backend.

A dependency-free graph held in Python dicts. It needs no setup and is rebuilt from the
corpus on every start (nothing is persisted). Used when Neo4j is not configured, and by
the test suite.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from src.agents.state import DocumentChunk, EntityNode, EntityRelation, SubgraphData
from src.db.events import EventFilter, apply_event_filter
from src.db.ingest_corpus import DEFAULT_CORPUS, document_to_graph, iter_corpus
from src.utils.embeddings import local_embed_array

logger = logging.getLogger("GraphScout.MemoryGraph")


class InMemoryGraphClient:
    """Graph + lexical-vector index kept entirely in process memory."""

    backend = "memory"
    mode_label = "In-memory graph"
    persistent = False
    location: Optional[str] = None
    database: Optional[str] = None

    def __init__(self, corpus_path: str = DEFAULT_CORPUS, autoload: bool = True):
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._chunks: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, Any]] = []
        # Indexes: adjacency list, edge de-dup keys, lower-cased name -> id, and a
        # lexical embedding matrix over chunks (rebuilt lazily when chunks change).
        self._adj: Dict[str, List[Dict[str, Any]]] = {}
        self._edge_keys: set = set()
        self._name_index: Dict[str, str] = {}
        self._lex_ids: List[str] = []
        self._lex_vectors: List[np.ndarray] = []
        self._lex_matrix: Optional[np.ndarray] = None
        if autoload:
            loaded = self.load_documents(iter_corpus(corpus_path))
            logger.info("Loaded %d documents into the in-memory graph (%s).", loaded, self.stats())

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------
    def load_documents(self, docs: Iterable[Dict[str, Any]]) -> int:
        """Add corpus documents to the graph. Returns how many were processed."""
        count = 0
        for doc in docs:
            records = document_to_graph(doc)
            for entity in records.entities:
                self._add_entity(entity, overwrite=False)
            for relation in records.relations:
                self._add_edge(relation.model_dump())
            if records.chunk:
                self._add_chunk(records.chunk.chunk_id, records.chunk.model_dump())
            count += 1
        return count

    def upsert_entity(self, entity: EntityNode) -> bool:
        self._add_entity(entity, overwrite=True)
        return True

    def upsert_chunk(self, chunk: DocumentChunk, embedding: Optional[List[float]] = None) -> bool:
        data = chunk.model_dump()
        if embedding:
            data["embedding"] = embedding
        self._add_chunk(chunk.chunk_id, data)
        return True

    def upsert_relation(self, relation: EntityRelation) -> bool:
        self._add_edge(relation.model_dump())
        return True

    def _add_entity(self, entity: EntityNode, overwrite: bool) -> None:
        if overwrite or entity.entity_id not in self._entities:
            self._entities[entity.entity_id] = entity.model_dump()
        self._name_index.setdefault(entity.canonical_name.strip().lower(), entity.entity_id)

    def _add_edge(self, edge: Dict[str, Any]) -> None:
        key = (edge["source_id"], edge["target_id"], edge["relation_type"])
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self._edges.append(edge)
        self._adj.setdefault(edge["source_id"], []).append(edge)
        if edge["target_id"] != edge["source_id"]:
            self._adj.setdefault(edge["target_id"], []).append(edge)

    def _add_chunk(self, chunk_id: str, data: Dict[str, Any]) -> None:
        is_new = chunk_id not in self._chunks
        self._chunks[chunk_id] = data
        vec = local_embed_array(f"{data.get('section_header') or ''}\n{data.get('text_content', '')}")
        if is_new:
            self._lex_ids.append(chunk_id)
            self._lex_vectors.append(vec)
        else:
            self._lex_vectors[self._lex_ids.index(chunk_id)] = vec
        self._lex_matrix = None

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def stats(self) -> Dict[str, int]:
        return {"entities": len(self._entities), "relations": len(self._edges), "chunks": len(self._chunks)}

    def resolve_entity_ids(self, seeds: List[str], max_matches_per_seed: int = 3) -> List[str]:
        """Map seed strings (ids or free-text names from the LLM) to known entity ids."""
        resolved: List[str] = []
        for seed in seeds:
            if seed in self._entities:
                resolved.append(seed)
                continue
            name = seed.replace("_", " ").strip().lower()
            if name in self._name_index:
                resolved.append(self._name_index[name])
                continue
            if len(name) < 4:
                continue
            candidates = [
                (len(n), eid) for n, eid in self._name_index.items()
                if name in n or (len(n) >= 5 and n in name)
            ]
            resolved.extend(eid for _, eid in sorted(candidates)[:max_matches_per_seed])
        return list(dict.fromkeys(resolved))

    def get_entity_subgraph(
        self,
        seed_entity_ids: List[str],
        max_hops: int = 2,
        max_neighbors: int = 15,
        min_confidence: float = 0.5,
    ) -> SubgraphData:
        """BFS from the seeds (ids or names); each node expands to at most ``max_neighbors`` edges."""
        seeds = self.resolve_entity_ids(seed_entity_ids)
        visited: Dict[str, EntityNode] = {s: self._entity_node(s, 0) for s in seeds}
        edge_keys = set()
        collected: List[EntityRelation] = []

        frontier = list(seeds)
        for hop in range(1, max_hops + 1):
            next_frontier: List[str] = []
            for s_id in frontier:
                for e_data in self._adj.get(s_id, [])[:max_neighbors]:
                    if e_data.get("confidence", 1.0) < min_confidence:
                        continue
                    key = (e_data["source_id"], e_data["target_id"], e_data["relation_type"])
                    if key not in edge_keys:
                        edge_keys.add(key)
                        collected.append(EntityRelation(**e_data))
                    neighbor = e_data["target_id"] if e_data["source_id"] == s_id else e_data["source_id"]
                    if neighbor not in visited and neighbor in self._entities:
                        visited[neighbor] = self._entity_node(neighbor, hop)
                        next_frontier.append(neighbor)
            frontier = next_frontier

        return SubgraphData(nodes=list(visited.values()), edges=collected, center_entities=seeds, depth=max_hops)

    def get_entity_provenance(self, entity_ids: List[str], max_chunks: int = 10) -> List[DocumentChunk]:
        """Chunks backing the given entities: the entity's own document first, then chunks mentioning its name."""
        resolved = self.resolve_entity_ids(entity_ids)
        results: Dict[str, DocumentChunk] = {}

        for eid in resolved:
            own = self._chunks.get(f"chunk_{eid}")
            if own:
                results.setdefault(own["chunk_id"], self._chunk(own, 1.0))
            for e_data in self._adj.get(eid, []):
                pid = e_data.get("provenance_chunk_id")
                if pid in self._chunks and len(results) < max_chunks:
                    results.setdefault(pid, self._chunk(self._chunks[pid], 0.9))
            if len(results) >= max_chunks:
                break

        if len(results) < max_chunks:
            names = [self._entities[e]["canonical_name"].lower() for e in resolved]
            names = [n for n in names if len(n) >= 4]
            for c_id, c_data in self._chunks.items():
                if len(results) >= max_chunks:
                    break
                if c_id not in results and any(n in c_data.get("text_content", "").lower() for n in names):
                    results[c_id] = self._chunk(c_data, 0.7)

        return list(results.values())[:max_chunks]

    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
    ) -> List[DocumentChunk]:
        """Nearest chunks. With ``query_text`` this uses the local lexical index, so results do not
        depend on which LLM provider produced ``query_embedding``."""
        if query_text:
            return self._lexical_search(query_text, top_k)
        return self._embedding_search(query_embedding, top_k, min_score)

    def find_events(self, event_filter: EventFilter) -> Tuple[int, List[Dict[str, Any]]]:
        """Olympic events matching ``event_filter``: (total matches, shown rows)."""
        candidates = (
            {**info["metadata"], "entity_id": eid, "title": info["canonical_name"]}
            for eid, info in self._entities.items()
            if (info.get("metadata") or {}).get("sport")
        )
        return apply_event_filter(candidates, event_filter)

    def close(self) -> None:
        """Nothing to release; present so callers can treat every backend alike."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _entity_node(self, entity_id: str, hops: int) -> EntityNode:
        info = self._entities[entity_id]
        node = EntityNode(**{k: v for k, v in info.items() if k in EntityNode.model_fields})
        node.source_hops = hops
        return node

    @staticmethod
    def _chunk(c_data: Dict[str, Any], score: float) -> DocumentChunk:
        fields = {k: v for k, v in c_data.items() if k in DocumentChunk.model_fields and k != "score"}
        return DocumentChunk(**fields, score=score)

    def _lexical_search(self, query_text: str, top_k: int) -> List[DocumentChunk]:
        if not self._lex_ids:
            return []
        if self._lex_matrix is None:
            self._lex_matrix = np.vstack(self._lex_vectors)
        sims = self._lex_matrix @ local_embed_array(query_text)
        top = np.argsort(-sims)[:top_k]
        return [self._chunk(self._chunks[self._lex_ids[i]], float(sims[i])) for i in top if sims[i] > 0.05]

    def _embedding_search(self, query_emb: List[float], top_k: int, min_score: float) -> List[DocumentChunk]:
        scored: List[Tuple[float, DocumentChunk]] = []
        q_vec = np.array(query_emb, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec) + 1e-9
        for c_data in self._chunks.values():
            emb = c_data.get("embedding")
            if emb:
                c_vec = np.array(emb, dtype=np.float32)
                sim = float(np.dot(q_vec, c_vec) / (q_norm * np.linalg.norm(c_vec) + 1e-9))
                if sim >= min_score:
                    scored.append((sim, self._chunk(c_data, sim)))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]
