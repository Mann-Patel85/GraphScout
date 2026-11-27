"""Vector search tool over the graph backend's chunk index."""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple
from src.agents.state import DocumentChunk
from src.db.graph_client import GraphClient
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.VectorTool")


class VectorTool:
    """Nearest-chunk search over the vector index."""

    def __init__(self, tg_client: GraphClient, llm_client: LLMClient):
        self.tg_client = tg_client
        self.llm = llm_client

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.6,
    ) -> Tuple[List[DocumentChunk], Dict[str, int]]:
        """Embed the query and retrieve the nearest text chunks."""
        logger.info("VectorTool executing vector search for: '%s' (top_k=%d)", query[:60], top_k)
        embedding = self.llm.get_embedding(query)
        chunks = self.tg_client.vector_search(
            query_embedding=embedding, top_k=top_k, min_score=min_score, query_text=query
        )
        
        usage = {"prompt_tokens": len(query.split()) * 2, "completion_tokens": 0}
        return chunks, usage
