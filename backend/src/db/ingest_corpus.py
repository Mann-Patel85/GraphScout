"""Corpus Ingestion Pipeline for GraphScout.

Parses data/documents/corpus.jsonl, extracts structured event entities,
venues, dates, medalists, and dense text chunks, and upserts them into TigerGraph.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from tqdm import tqdm

from src.agents.state import DocumentChunk, EntityNode, EntityRelation
from src.db.tigergraph_client import TigerGraphClient
from src.utils.llm_client import LLMClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("GraphScout.Ingest")


def parse_infobox(text: str) -> Dict[str, str]:
    """Extract key-value pairs from [Infobox Olympic event]."""
    info: Dict[str, str] = {}
    lines = text.split("\n")
    in_infobox = False

    for line in lines:
        s = line.strip()
        if s.startswith("[Infobox"):
            in_infobox = True
            continue
        if in_infobox:
            if s.startswith("[") and not s.startswith("[Infobox"):
                break
            if ":" in s:
                parts = s.split(":", 1)
                k = parts[0].strip()
                v = parts[1].strip()
                info[k] = v
            elif s == "":
                # End of infobox header block
                if len(info) > 2:
                    break

    return info


def ingest_corpus(
    corpus_path: str = "data/documents/corpus.jsonl",
    max_docs: Optional[int] = None,
    generate_embeddings: bool = False,
) -> None:
    """Ingest documents from corpus.jsonl into TigerGraph and vector index."""
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
        logger.error("Corpus file not found at: %s", corpus_path)
        return

    tg_client = TigerGraphClient()
    llm_client = LLMClient() if generate_embeddings else None

    logger.info("Starting ingestion from %s...", corpus_path)
    count = 0
    entities_count = 0
    relations_count = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Ingesting Documents"):
            if max_docs and count >= max_docs:
                break

            doc = json.loads(line)
            doc_id = doc.get("doc_id")
            title = doc.get("title", "")
            text = doc.get("text", "")
            infobox = parse_infobox(text)

            # 1. Create Event/Document Entity
            event_node = EntityNode(
                entity_id=doc_id,
                canonical_name=title,
                entity_type="OlympicEvent",
                description=f"{infobox.get('event', title)} ({infobox.get('games', '')}) at {infobox.get('venue', '')}",
                metadata=infobox,
            )
            tg_client.upsert_entity(event_node)
            entities_count += 1

            # 2. Extract Venue Entity & Relation
            venue_name = infobox.get("venue")
            if venue_name:
                venue_id = "Venue_" + venue_name.replace(" ", "_").replace(",", "")
                tg_client.upsert_entity(
                    EntityNode(
                        entity_id=venue_id,
                        canonical_name=venue_name,
                        entity_type="Venue",
                    )
                )
                tg_client.upsert_relation(
                    EntityRelation(
                        source_id=doc_id,
                        target_id=venue_id,
                        relation_type="HELD_AT",
                        confidence=1.0,
                    )
                )
                entities_count += 1
                relations_count += 1

            # 3. Extract Gold Medalist Entity & Relation
            gold_winner = infobox.get("gold")
            if gold_winner:
                gold_id = "Athlete_" + gold_winner.replace(" ", "_")
                tg_client.upsert_entity(
                    EntityNode(
                        entity_id=gold_id,
                        canonical_name=gold_winner,
                        entity_type="Athlete",
                    )
                )
                tg_client.upsert_relation(
                    EntityRelation(
                        source_id=doc_id,
                        target_id=gold_id,
                        relation_type="WON_GOLD",
                        confidence=1.0,
                    )
                )
                entities_count += 1
                relations_count += 1

            # 4. Create Document Chunk
            embedding = llm_client.get_embedding(text[:1000]) if llm_client else None
            chunk = DocumentChunk(
                chunk_id=f"chunk_{doc_id}",
                doc_id=doc_id,
                text_content=text[:1500],
                section_header="Event Summary",
                associated_entities=[doc_id] + ([venue_name] if venue_name else []),
            )
            tg_client.upsert_chunk(chunk, embedding=embedding)

            count += 1

    logger.info(
        "Ingestion completed! Processed %d documents (%d entities, %d relations).",
        count,
        entities_count,
        relations_count,
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest Olympic corpus into GraphScout")
    parser.add_argument("--limit", type=int, default=100, help="Number of documents to ingest (default: 100)")
    parser.add_argument("--all", action="store_true", help="Ingest all 2,951 documents")
    parser.add_argument("--embed", action="store_true", help="Generate dense vector embeddings")
    args = parser.parse_args()

    limit = None if args.all else args.limit
    ingest_corpus(max_docs=limit, generate_embeddings=args.embed)
