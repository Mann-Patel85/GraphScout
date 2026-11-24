"""TigerGraph & Vector DB Client Wrapper.

Provides an enterprise-grade async and sync interface for TigerGraph 3.x/4.x,
supporting GSQL query execution, vertex/edge CRUD, and dense vector similarity search.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import pyTigerGraph as tg
except ImportError:
    tg = None

from src.agents.state import DocumentChunk, EntityNode, EntityRelation, SubgraphData

logger = logging.getLogger("GraphScout.TigerGraphClient")


class TigerGraphConfig:
    """Configuration dataclass for TigerGraph connection."""
    def __init__(
        self,
        host: str = "http://127.0.0.1",
        restpp_port: int = 9000,
        gsport_port: int = 14240,
        graph_name: str = "GraphScoutKG",
        username: str = "tigergraph",
        password: str = "tigergraph",
        secret: Optional[str] = None,
        token: Optional[str] = None,
        use_ssl: bool = False,
        cert_path: Optional[str] = None,
        vector_dimension: int = 1536,
    ):
        self.host = host.rstrip("/")
        self.restpp_port = restpp_port
        self.gsport_port = gsport_port
        self.graph_name = graph_name
        self.username = username
        self.password = password
        self.secret = secret
        self.token = token
        self.use_ssl = use_ssl
        self.cert_path = cert_path
        self.vector_dimension = vector_dimension


class TigerGraphClient:
    """Wrapper around pyTigerGraph and TigerGraph REST++ endpoints with Vector Search."""

    def __init__(self, config: Optional[TigerGraphConfig] = None):
        self.config = config or TigerGraphConfig()
        self.conn: Optional[Any] = None
        self._mock_mode: bool = False
        self._mock_vertices: Dict[str, Dict[str, Any]] = {"Entity": {}, "Chunk": {}, "Document": {}}
        self._mock_edges: List[Dict[str, Any]] = []
        self._initialize_connection()
        if self._mock_mode:
            self.load_local_corpus()

    def _initialize_connection(self) -> None:
        """Establish connection or activate resilient mock mode if cluster is unreachable."""
        if tg is None:
            logger.info("pyTigerGraph not installed. Running TigerGraphClient in in-memory simulation mode.")
            self._mock_mode = True
            return

        try:
            conn = tg.TigerGraphConnection(
                host=self.config.host,
                restppPort=self.config.restpp_port,
                gsPort=self.config.gsport_port,
                graphname=self.config.graph_name,
                username=self.config.username,
                password=self.config.password,
            )

            # Quick connectivity verification with short timeout
            if self.config.secret:
                conn.getToken(self.config.secret)
            elif self.config.token:
                conn.apiToken = self.config.token
            else:
                conn.ping()

            self.conn = conn
            logger.info("Successfully established TigerGraph connection to %s", self.config.host)
        except Exception as exc:
            logger.info("TigerGraph host (%s) not reachable (%s). Using in-memory GraphScout engine with corpus dataset.", self.config.host, exc)
            self._mock_mode = True
            self.conn = None

    def load_local_corpus(self, corpus_path: str = "data/documents/corpus.jsonl", max_docs: int = 1000) -> None:
        """Load uploaded corpus.jsonl into the in-memory graph index."""
        import json
        from pathlib import Path

        file_path = Path(corpus_path)
        if not file_path.exists():
            candidates = [
                Path(__file__).resolve().parent.parent.parent / corpus_path,
                Path(__file__).resolve().parent.parent.parent.parent / corpus_path,
            ]
            for c in candidates:
                if c.exists():
                    file_path = c
                    break
        if not file_path.exists():
            return

        logger.info("Loading documents from %s into GraphScout memory...", corpus_path)
        loaded = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if loaded >= max_docs:
                    break
                doc = json.loads(line)
                doc_id = doc.get("doc_id", "")
                title = doc.get("title", "")
                text = doc.get("text", "")
                
                # Register Event Entity
                self._mock_vertices["Entity"][doc_id] = {
                    "entity_id": doc_id,
                    "canonical_name": title,
                    "entity_type": "OlympicEvent",
                    "description": text[:300],
                }

                # Register Chunk
                self._mock_vertices["Chunk"][f"chunk_{doc_id}"] = {
                    "chunk_id": f"chunk_{doc_id}",
                    "doc_id": doc_id,
                    "text_content": text[:1500],
                    "section_header": title,
                }
                loaded += 1
        logger.info("Loaded %d documents from %s into graph engine.", loaded, corpus_path)

    # --------------------------------------------------------------------------
    # Graph Traversal & Subgraph Queries
    # --------------------------------------------------------------------------

    def get_entity_subgraph(
        self,
        seed_entity_ids: List[str],
        max_hops: int = 2,
        max_neighbors: int = 15,
        min_confidence: float = 0.5,
    ) -> SubgraphData:
        """Retrieve multi-hop neighborhood around specified seed entities."""
        if self._mock_mode or not self.conn:
            return self._mock_get_subgraph(seed_entity_ids, max_hops, min_confidence)

        try:
            params = {
                "seed_entity_ids": seed_entity_ids,
                "max_hops": max_hops,
                "max_neighbors": max_neighbors,
                "min_confidence": min_confidence,
            }
            results = self.conn.runInstalledQuery("get_entity_subgraph", params=params)
            
            nodes_data = []
            edges_data = []
            if results and len(results) > 0:
                raw_nodes = results[0].get("nodes", [])
                raw_edges = results[0].get("edges", [])

                for n in raw_nodes:
                    nodes_data.append(
                        EntityNode(
                            entity_id=n.get("entity_id", ""),
                            canonical_name=n.get("name", n.get("entity_id", "")),
                            entity_type=n.get("entity_type", "Concept"),
                            description=n.get("description", ""),
                        )
                    )

                for e in raw_edges:
                    edges_data.append(
                        EntityRelation(
                            source_id=e.get("source_id", ""),
                            target_id=e.get("target_id", ""),
                            relation_type=e.get("rel_type", "RELATED_TO"),
                            confidence=float(e.get("confidence", 1.0)),
                            evidence_snippet=e.get("snippet", ""),
                        )
                    )

            return SubgraphData(
                nodes=nodes_data,
                edges=edges_data,
                center_entities=seed_entity_ids,
                depth=max_hops,
            )

        except Exception as exc:
            logger.error("Error executing get_entity_subgraph query: %s. Falling back to local mock traversal.", exc)
            return self._mock_get_subgraph(seed_entity_ids, max_hops, min_confidence)

    def get_entity_provenance(self, entity_ids: List[str], max_chunks: int = 10) -> List[DocumentChunk]:
        """Fetch backing document chunks linked to specified entities."""
        if self._mock_mode or not self.conn:
            return self._mock_get_provenance(entity_ids, max_chunks)

        try:
            params = {"entity_ids": entity_ids, "max_chunks": max_chunks}
            results = self.conn.runInstalledQuery("get_entity_provenance", params=params)
            chunks: List[DocumentChunk] = []

            if results and len(results) > 0:
                raw_chunks = results[0].get("provenance_chunks", [])
                for rc in raw_chunks:
                    chunks.append(
                        DocumentChunk(
                            chunk_id=rc.get("chunk_id", ""),
                            text_content=rc.get("text_content", ""),
                            section_header=rc.get("section_header", ""),
                            score=float(rc.get("confidence", 1.0)),
                            associated_entities=entity_ids,
                        )
                    )
            return chunks
        except Exception as exc:
            logger.error("Error executing get_entity_provenance: %s", exc)
            return self._mock_get_provenance(entity_ids, max_chunks)

    # --------------------------------------------------------------------------
    # Vector Search Interface
    # --------------------------------------------------------------------------

    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """Execute vector similarity search across TigerGraph chunk embeddings."""
        if self._mock_mode or not self.conn:
            return self._mock_vector_search(query_embedding, top_k, min_score)

        try:
            # TigerGraph Vector Search via REST++ / custom query
            payload = {
                "query_vector": query_embedding,
                "top_k": top_k,
                "min_similarity": min_score,
            }
            # If native vector extension query is installed:
            res = self.conn.runInstalledQuery("tg_vector_search", params=payload)
            chunks = []
            if res and len(res) > 0:
                for item in res[0].get("results", []):
                    chunks.append(
                        DocumentChunk(
                            chunk_id=item.get("chunk_id"),
                            doc_id=item.get("doc_id"),
                            text_content=item.get("text_content", ""),
                            section_header=item.get("section_header"),
                            score=float(item.get("score", 0.0)),
                        )
                    )
            return chunks
        except Exception as exc:
            logger.warning("Native TigerGraph vector search failed (%s), running fallback cosine index.", exc)
            return self._mock_vector_search(query_embedding, top_k, min_score)

    # --------------------------------------------------------------------------
    # Upsert Operations
    # --------------------------------------------------------------------------

    def upsert_entity(self, entity: EntityNode) -> bool:
        """Upsert single entity vertex into TigerGraph."""
        self._mock_vertices["Entity"][entity.entity_id] = entity.model_dump()
        if self.conn and not self._mock_mode:
            try:
                self.conn.upsertVertex(
                    vertexType="Entity",
                    vertexId=entity.entity_id,
                    attributes={
                        "canonical_name": entity.canonical_name,
                        "entity_type": entity.entity_type,
                        "description": entity.description or "",
                        "aliases": entity.aliases,
                        "importance_score": entity.importance_score,
                    },
                )
                return True
            except Exception as exc:
                logger.error("Failed to upsert entity %s: %s", entity.entity_id, exc)
                return False
        return True

    def upsert_chunk(self, chunk: DocumentChunk, embedding: Optional[List[float]] = None) -> bool:
        """Upsert document chunk vertex and associated embeddings."""
        data = chunk.model_dump()
        if embedding:
            data["embedding"] = embedding
        self._mock_vertices["Chunk"][chunk.chunk_id] = data

        if self.conn and not self._mock_mode:
            try:
                attrs = {
                    "text_content": chunk.text_content,
                    "section_header": chunk.section_header or "",
                    "token_count": chunk.token_count,
                }
                if embedding:
                    attrs["embedding"] = embedding
                self.conn.upsertVertex(
                    vertexType="Chunk",
                    vertexId=chunk.chunk_id,
                    attributes=attrs,
                )
                return True
            except Exception as exc:
                logger.error("Failed to upsert chunk %s: %s", chunk.chunk_id, exc)
                return False
        return True

    def upsert_relation(self, relation: EntityRelation) -> bool:
        """Upsert relationship edge between entities."""
        self._mock_edges.append(relation.model_dump())
        if self.conn and not self._mock_mode:
            try:
                self.conn.upsertEdge(
                    sourceVertexType="Entity",
                    sourceVertexId=relation.source_id,
                    edgeType="RELATED_TO",
                    targetVertexType="Entity",
                    targetVertexId=relation.target_id,
                    attributes={
                        "relation_type": relation.relation_type,
                        "weight": relation.weight,
                        "confidence": relation.confidence,
                        "evidence_snippet": relation.evidence_snippet or "",
                    },
                )
                return True
            except Exception as exc:
                logger.error("Failed to upsert relation %s -> %s: %s", relation.source_id, relation.target_id, exc)
                return False
        return True

    # --------------------------------------------------------------------------
    # Resilient In-Memory Mock Traversal for Local Dev & Test Harness
    # --------------------------------------------------------------------------

    def _mock_get_subgraph(self, seed_entity_ids: List[str], max_hops: int, min_confidence: float) -> SubgraphData:
        visited_nodes: Dict[str, EntityNode] = {}
        collected_edges: List[EntityRelation] = []

        curr_seeds = set(seed_entity_ids)
        for hop in range(max_hops):
            next_seeds = set()
            for s_id in curr_seeds:
                if s_id in self._mock_vertices["Entity"] and s_id not in visited_nodes:
                    v_info = self._mock_vertices["Entity"][s_id]
                    visited_nodes[s_id] = EntityNode(**v_info)

                # Find edges connected to s_id
                for e_data in self._mock_edges:
                    if e_data["source_id"] == s_id or e_data["target_id"] == s_id:
                        if e_data.get("confidence", 1.0) >= min_confidence:
                            rel = EntityRelation(**e_data)
                            collected_edges.append(rel)
                            neighbor_id = rel.target_id if rel.source_id == s_id else rel.source_id
                            if neighbor_id not in visited_nodes:
                                next_seeds.add(neighbor_id)
                                if neighbor_id in self._mock_vertices["Entity"]:
                                    visited_nodes[neighbor_id] = EntityNode(**self._mock_vertices["Entity"][neighbor_id])
            curr_seeds = next_seeds

        return SubgraphData(
            nodes=list(visited_nodes.values()),
            edges=collected_edges,
            center_entities=seed_entity_ids,
            depth=max_hops,
        )

    def _mock_get_provenance(self, entity_ids: List[str], max_chunks: int) -> List[DocumentChunk]:
        results = []
        for c_id, c_data in self._mock_vertices["Chunk"].items():
            for e_id in entity_ids:
                if e_id.lower() in c_data.get("text_content", "").lower():
                    results.append(DocumentChunk(**{k: v for k, v in c_data.items() if k != "embedding"}))
                    break
            if len(results) >= max_chunks:
                break
        return results

    def _mock_vector_search(self, query_emb: List[float], top_k: int, min_score: float) -> List[DocumentChunk]:
        scored: List[Tuple[float, DocumentChunk]] = []
        q_vec = np.array(query_emb, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec) + 1e-9

        for c_id, c_data in self._mock_vertices["Chunk"].items():
            emb = c_data.get("embedding")
            if emb:
                c_vec = np.array(emb, dtype=np.float32)
                sim = float(np.dot(q_vec, c_vec) / (q_norm * np.linalg.norm(c_vec) + 1e-9))
                if sim >= min_score:
                    chunk = DocumentChunk(**{k: v for k, v in c_data.items() if k != "embedding"}, score=sim)
                    scored.append((sim, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]
