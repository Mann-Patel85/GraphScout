"""Corpus ingestion for GraphScout.

``document_to_graph`` is the single definition of how one corpus document becomes
graph records (entities, relations, one text chunk). Both graph backends use it, so the
in-memory engine and Neo4j always hold the same graph.

CLI (run from ``backend/``)::

    python -m src.db.ingest_corpus --all        # every document
    python -m src.db.ingest_corpus --limit 200  # first 200 documents
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from src.agents.state import DocumentChunk, EntityNode, EntityRelation
from src.db.events import event_attributes

logger = logging.getLogger("GraphScout.Ingest")

DEFAULT_CORPUS = "data/documents/corpus.jsonl"
CHUNK_CHARS = 1500


def parse_infobox(text: str) -> Dict[str, str]:
    """Extract key-value pairs from the leading ``[Infobox ...]`` block."""
    info: Dict[str, str] = {}
    in_infobox = False

    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("[Infobox"):
            in_infobox = True
            continue
        if in_infobox:
            if s.startswith("[") and not s.startswith("[Infobox"):
                break
            if ":" in s:
                k, v = s.split(":", 1)
                info[k.strip()] = v.strip()
            elif s == "" and len(info) > 2:
                break  # end of infobox header block

    return info


@dataclass
class GraphRecords:
    """Graph records derived from one document."""
    entities: List[EntityNode] = field(default_factory=list)
    relations: List[EntityRelation] = field(default_factory=list)
    chunk: Optional[DocumentChunk] = None


def document_to_graph(doc: Dict[str, Any]) -> GraphRecords:
    """Turn one corpus document into event / venue / games / gold-medalist nodes, edges and a chunk."""
    doc_id = doc.get("doc_id", "")
    title = doc.get("title", "")
    text = doc.get("text", "")
    info = parse_infobox(text)
    is_event = "event" in info or "gold" in info
    chunk_id = f"chunk_{doc_id}"

    summary = ", ".join(
        f"{k}: {info[k]}" for k in ("games", "venue", "date", "dates", "competitors", "gold") if info.get(k)
    )
    records = GraphRecords()
    records.entities.append(EntityNode(
        entity_id=doc_id,
        canonical_name=title,
        entity_type="OlympicEvent" if is_event else "Document",
        description=summary or text[:300],
        # Structured infobox fields (sport, games, year, competitors, ...) used by find_events.
        metadata=event_attributes(title, info),
    ))

    def link(target_id: str, name: str, etype: str, relation: str) -> None:
        records.entities.append(EntityNode(entity_id=target_id, canonical_name=name, entity_type=etype))
        records.relations.append(EntityRelation(
            source_id=doc_id,
            target_id=target_id,
            relation_type=relation,
            evidence_snippet=f"{title}: {relation} {name}",
            provenance_chunk_id=chunk_id,
        ))

    if info.get("venue"):
        venue = info["venue"]
        link("Venue_" + venue.replace(" ", "_").replace(",", ""), venue, "Venue", "HELD_AT")
    if info.get("games"):
        games = info["games"]
        games_name = games if "olympic" in games.lower() else f"{games} Olympics"
        link("Games_" + games.replace(" ", "_"), games_name, "OlympicGames", "PART_OF_GAMES")
    if info.get("gold"):
        gold = info["gold"]
        link("Athlete_" + gold.replace(" ", "_"), gold, "Athlete", "WON_GOLD")

    records.chunk = DocumentChunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        text_content=text[:CHUNK_CHARS],
        section_header=title,
        # Every entity this document produced; Neo4j stores these as MENTIONS edges.
        associated_entities=[e.entity_id for e in records.entities],
    )
    return records


def resolve_corpus_path(corpus_path: str = DEFAULT_CORPUS) -> Optional[Path]:
    """Find the corpus relative to the cwd, ``backend/`` or the project root."""
    here = Path(__file__).resolve()
    for candidate in (Path(corpus_path), here.parents[2] / corpus_path, here.parents[3] / corpus_path):
        if candidate.exists():
            return candidate
    return None


def iter_corpus(corpus_path: str = DEFAULT_CORPUS, max_docs: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    """Yield corpus documents (all of them unless ``max_docs`` is given)."""
    file_path = resolve_corpus_path(corpus_path)
    if file_path is None:
        logger.error("Corpus file not found at: %s", corpus_path)
        return
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if max_docs is not None and count >= max_docs:
                break
            if line.strip():
                yield json.loads(line)
                count += 1


def ingest_corpus(
    corpus_path: str = DEFAULT_CORPUS,
    max_docs: Optional[int] = None,
    tg_client: Optional[Any] = None,
) -> int:
    """Load corpus documents into a graph client (the configured backend if none is given).

    Re-running is safe: writes are upserts. Returns the number of documents ingested.
    """
    from src.db.graph_client import create_graph_client

    owns_client = tg_client is None
    client = tg_client or create_graph_client(autoload=False)
    try:
        logger.info("Ingesting %s into the %s graph...", corpus_path, client.backend)
        count = client.load_documents(iter_corpus(corpus_path, max_docs))
        logger.info("Ingestion complete: %d documents. Graph now holds %s.", count, client.stats())
        return count
    finally:
        if owns_client:
            client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest the Olympic corpus into the configured GraphScout graph")
    parser.add_argument("--limit", type=int, default=100, help="Number of documents to ingest (default: 100)")
    parser.add_argument("--all", action="store_true", help="Ingest every document in the corpus")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ingest_corpus(max_docs=None if args.all else args.limit)
