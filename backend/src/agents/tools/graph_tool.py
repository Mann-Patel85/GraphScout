"""Graph Tool and Sub-Agent for TigerGraph GSQL operations."""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple
from pydantic import BaseModel, Field

from src.agents.state import EntityNode, SubgraphData
from src.db.tigergraph_client import TigerGraphClient
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.GraphTool")


class EntityExtractionResult(BaseModel):
    """Structured entity linking output."""
    extracted_entities: List[str] = Field(default_factory=list)
    reasoning: str = ""


class GraphTool:
    """Specialized tool for TigerGraph entity linking and multi-hop GSQL queries."""

    def __init__(self, tg_client: TigerGraphClient, llm_client: LLMClient):
        self.tg_client = tg_client
        self.llm = llm_client

    def link_entities(self, text: str) -> Tuple[List[str], Dict[str, int]]:
        """Extract and link key named entities from raw text for graph seeding."""
        system_prompt = (
            "You are an expert Graph Entity Extractor for TigerGraph. Extract key named entities, "
            "organizations, concepts, and identifiers from the input text suitable for graph traversal."
        )
        user_prompt = f"Extract graph entity seeds from:\n\n{text}"
        result, usage = self.llm.generate_json(system_prompt, user_prompt, EntityExtractionResult)
        return result.extracted_entities, usage

    def traverse_subgraph(
        self,
        seed_entities: List[str],
        max_hops: int = 2,
        min_confidence: float = 0.5,
    ) -> SubgraphData:
        """Query TigerGraph to retrieve multi-hop subgraph paths around seed entities."""
        logger.info("GraphTool traversing multi-hop paths for seeds: %s (depth=%d)", seed_entities, max_hops)
        return self.tg_client.get_entity_subgraph(
            seed_entity_ids=seed_entities,
            max_hops=max_hops,
            min_confidence=min_confidence,
        )
