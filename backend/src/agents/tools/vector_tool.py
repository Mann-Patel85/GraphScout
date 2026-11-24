"""Vector Search Tool and Sub-Agent for TigerGraph Vector DB."""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple
from src.agents.state import DocumentChunk
from src.db.tigergraph_client import TigerGraphClient
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.VectorTool")


class VectorTool:
    """Specialized tool for semantic chunk search over TigerGraph embeddings."""

    def __init__(self, tg_client: TigerGraphClient, llm_client: LLMClient):
        self.tg_client = tg_client
        self.llm = llm_client

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.6,
    ) -> Tuple[List[DocumentChunk], Dict[str, int]]:
        """Compute query embedding and retrieve nearest textual chunks from TigerGraph."""
        logger.info("VectorTool executing vector search for: '%s' (top_k=%d)", query[:60], top_k)
        embedding = self.llm.get_embedding(query)
        chunks = self.tg_client.vector_search(query_embedding=embedding, top_k=top_k, min_score=min_score)
        
        usage = {"prompt_tokens": len(query.split()) * 2, "completion_tokens": 0}
        return chunks, usage
