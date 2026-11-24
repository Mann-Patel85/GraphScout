"""Graph Sub-Agent for GraphScout.

Handles entity linking, multi-hop neighborhood expansion, and GSQL query execution.
"""

from __future__ import annotations

import logging
from typing import List, Tuple
from pydantic import BaseModel, Field

from src.agents.state import EntityNode, SubgraphData
from src.db.tigergraph_client import TigerGraphClient
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.GraphAgent")


class EntityExtractionResult(BaseModel):
    """Structured entity linking output."""
    extracted_entities: List[str] = Field(default_factory=list)
    reasoning: str = ""


class GraphAgent:
    """Specialized agent for Graph reasoning and TigerGraph multi-hop exploration."""

    def __init__(self, tg_client: TigerGraphClient, llm_client: LLMClient):
        self.tg_client = tg_client
        self.llm = llm_client

    def extract_seed_entities(self, text: str) -> Tuple[List[str], dict[str, int]]:
        """Extract key named entities and domain concepts from raw query or text."""
        system_prompt = (
            "You are an expert Graph Entity Extractor for TigerGraph. Extract key named entities, "
            "organizations, concepts, and identifiers from the input text suitable for graph traversal."
        )
        user_prompt = f"Extract graph entity seeds from:\n\n{text}"
        result, usage = self.llm.generate_json(system_prompt, user_prompt, EntityExtractionResult)
        return result.extracted_entities, usage

    def explore_subgraph(
        self,
        seed_entities: List[str],
        max_hops: int = 2,
        min_confidence: float = 0.5,
    ) -> SubgraphData:
        """Query TigerGraph to retrieve multi-hop subgraph paths around seed entities."""
        logger.info("GraphAgent exploring multi-hop paths for seeds: %s (depth=%d)", seed_entities, max_hops)
        subgraph = self.tg_client.get_entity_subgraph(
            seed_entity_ids=seed_entities,
            max_hops=max_hops,
            min_confidence=min_confidence,
        )
        return subgraph
