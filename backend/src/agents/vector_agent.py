"""Vector Search Sub-Agent for GraphScout.

Handles semantic chunk retrieval and embedding similarity matching against TigerGraph.
"""

from __future__ import annotations

import logging
from typing import List, Tuple
from src.agents.state import DocumentChunk
from src.db.tigergraph_client import TigerGraphClient
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.VectorAgent")


class VectorAgent:
    """Specialized agent for dense semantic vector retrieval over TigerGraph chunks."""

    def __init__(self, tg_client: TigerGraphClient, llm_client: LLMClient):
        self.tg_client = tg_client
        self.llm = llm_client

    def retrieve_chunks(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.6,
    ) -> Tuple[List[DocumentChunk], dict[str, int]]:
        """Compute query embedding and retrieve nearest textual chunks from TigerGraph."""
        logger.info("VectorAgent retrieving chunks for query: '%s' (top_k=%d)", query[:60], top_k)
        embedding = self.llm.get_embedding(query)
        chunks = self.tg_client.vector_search(query_embedding=embedding, top_k=top_k, min_score=min_score)
        
        # Token metrics tracking for embedding step
        usage = {"prompt_tokens": len(query.split()) * 2, "completion_tokens": 0}
        return chunks, usage
