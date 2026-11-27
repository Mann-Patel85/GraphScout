"""Structured Olympic-event attributes and the ``find_events`` filter.

Each event document's infobox (sport, Games, venue, date, competitors, nations, gold
medallist) is stored on its graph entity, so questions like "which 2008 athletics event had
the most competitors" or "how many biathlon events in 2018 had more than 73 competitors"
are answered from all matching events, not from whichever passages a search returns.

Backends return *candidate* events (they may pre-filter coarsely); ``apply_event_filter``
applies the exact rules, so both backends give identical results.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

_GAMES_RE = re.compile(r"(\d{4})\s+(Summer|Winter)", re.IGNORECASE)
_INT_RE = re.compile(r"\d[\d,]*")
_SPACE_RE = re.compile(r"\s+")


def normalize(text: Optional[str]) -> str:
    """Lower-case, unify quotes and dashes, collapse whitespace (used on both sides of a match)."""
    if not text:
        return ""
    text = text.lower().replace("’", "'").replace("‘", "'").replace("`", "'")
    text = re.sub(r"[‐-―−]", "-", text)
    return _SPACE_RE.sub(" ", text).strip()


def _first_int(value: Optional[str]) -> Optional[int]:
    m = _INT_RE.search(value or "")
    return int(m.group().replace(",", "")) if m else None


def event_attributes(title: str, info: Dict[str, str]) -> Dict[str, Any]:
    """Structured attributes for an event document (empty dict if it is not an Olympic event)."""
    if " at the " not in title or not ("event" in info or "gold" in info):
        return {}
    games_m = _GAMES_RE.search(info.get("games", "")) or _GAMES_RE.search(title)
    return {
        "sport": title.split(" at the ")[0].strip(),
        "event": title.split("–", 1)[-1].strip() if "–" in title else info.get("event", ""),
        "games": f"{games_m.group(1)} {games_m.group(2).title()}" if games_m else info.get("games", ""),
        "year": int(games_m.group(1)) if games_m else None,
        "season": games_m.group(2).title() if games_m else None,
        "venue": info.get("venue", ""),
        "date": " / ".join(v for v in (info.get("date"), info.get("dates")) if v),
        "competitors": _first_int(info.get("competitors")),
        "nations": _first_int(info.get("nations")),
        "gold": info.get("gold", ""),
        "gold_noc": info.get("goldNOC", ""),
    }


class EventFilter(BaseModel):
    """Filters for ``find_events``. Every field is optional; text fields match case-insensitively."""

    sport: Optional[str] = Field(default=None, description="Sport as in titles, e.g. 'Athletics', 'Alpine skiing', 'Biathlon'")
    event: Optional[str] = Field(default=None, description="Words of the event name, e.g. \"men's 20 kilometres walk\", \"women's 57 kg\"")
    year: Optional[int] = Field(default=None, description="Games year, e.g. 2008")
    season: Optional[Literal["Summer", "Winter"]] = None
    year_before: Optional[int] = Field(default=None, description="Only Games strictly before this year")
    venue: Optional[str] = Field(default=None, description="Venue text, copied from the question")
    date: Optional[str] = Field(default=None, description="Date text copied from the question, e.g. '14 February' or '6 to 8 August'")
    min_competitors: Optional[int] = Field(default=None, description="Strictly more than this many competitors")
    max_competitors: Optional[int] = Field(default=None, description="Strictly fewer than this many competitors")
    sort_by: Optional[Literal["competitors", "nations", "year"]] = None
    descending: bool = True
    limit: int = Field(default=15, ge=1, le=60, description="Rows to show (the total match count is always reported)")

    def is_empty(self) -> bool:
        return not any(
            getattr(self, k) is not None
            for k in ("sport", "event", "year", "season", "year_before", "venue", "date", "min_competitors", "max_competitors")
        )

    def describe(self) -> str:
        parts = [f"{k}={v!r}" for k, v in self.model_dump(exclude_none=True).items() if k not in ("descending", "limit")]
        if self.sort_by:
            parts.append("desc" if self.descending else "asc")
        return ", ".join(parts) or "no filters"


def _word_match(needle: str, haystack: str) -> bool:
    """``needle`` occurs in ``haystack`` as whole words: "men's" does not match "women's",
    and "August 1" does not match "August 14"."""
    return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", haystack) is not None


def _date_match(query: str, event_date: str) -> bool:
    q, d = normalize(query), normalize(event_date)
    if not q or not d:
        return False
    if _word_match(q, d):
        return True
    # The question may append the year ("4 August 2012") to an infobox date without one ("4 August").
    return any(len(part) >= 5 and _word_match(part, q) for part in (p.strip() for p in d.split(" / ")))


def matches(row: Dict[str, Any], f: EventFilter, exact_sport: bool = True) -> bool:
    if f.sport:
        sport, want = normalize(row.get("sport")), normalize(f.sport)
        if (sport != want) if exact_sport else (want not in sport):
            return False
    if f.event and not _word_match(normalize(f.event), normalize(row.get("title"))):
        return False
    if f.year is not None and row.get("year") != f.year:
        return False
    if f.season and row.get("season") != f.season:
        return False
    if f.year_before is not None and not (row.get("year") is not None and row["year"] < f.year_before):
        return False
    if f.venue and normalize(f.venue) not in normalize(row.get("venue")):
        return False
    if f.date and not _date_match(f.date, row.get("date", "")):
        return False
    comp = row.get("competitors")
    if f.min_competitors is not None and not (comp is not None and comp > f.min_competitors):
        return False
    if f.max_competitors is not None and not (comp is not None and comp < f.max_competitors):
        return False
    return True


def apply_event_filter(candidates: Iterable[Dict[str, Any]], f: EventFilter) -> Tuple[int, List[Dict[str, Any]]]:
    """Exact filtering, sorting and limiting. Returns (total matches, shown rows).

    Sport matches exactly ("Speed skating" is not "Short-track speed skating"); only if that
    finds nothing does it fall back to a substring match (e.g. "skiing").
    """
    rows = list(candidates)
    hits = [r for r in rows if matches(r, f, exact_sport=True)]
    if not hits and f.sport:
        hits = [r for r in rows if matches(r, f, exact_sport=False)]

    if f.sort_by:
        key = f.sort_by
        present = [r for r in hits if r.get(key) is not None]
        missing = [r for r in hits if r.get(key) is None]
        present.sort(key=lambda r: (r[key], r.get("title", "")), reverse=f.descending)
        hits = present + missing
    else:
        hits.sort(key=lambda r: (r.get("year") or 0, r.get("title", "")))
    return len(hits), hits[: f.limit]


def format_event_table(f: EventFilter, total: int, rows: List[Dict[str, Any]]) -> str:
    """Compact text table for LLM prompts."""
    head = f"find_events({f.describe()}): {total} matching event(s)"
    if total > len(rows):
        head += f", showing {len(rows)}" + (f" sorted by {f.sort_by} {'desc' if f.descending else 'asc'}" if f.sort_by else "")
    lines = [head]
    for r in rows:
        lines.append(
            f"- [chunk_{r['entity_id']}] {r.get('title')} | games: {r.get('games') or '?'} | venue: {r.get('venue') or '?'}"
            f" | date: {r.get('date') or '?'} | competitors: {r.get('competitors') if r.get('competitors') is not None else '?'}"
            f" | nations: {r.get('nations') if r.get('nations') is not None else '?'} | gold: {r.get('gold') or '?'}"
        )
    return "\n".join(lines)
