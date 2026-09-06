"""Official, post-match oriented sports sources.

The public federation/confederation page is the authority for schedule/result
state. Club pages are first-party complementary sources and are intentionally
kept out of the parser's conflict-resolution role.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

DEFAULT_USER_AGENT = (
    "OVigiaDados/0.1.0 (+https://github.com/ovigialocal/ovigia-dados; contato@ovigia.local)"
)

_DATE_RE = re.compile(r"^(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:\s+(?P<note>.+))?$")
_TIME_RE = re.compile(r"^(?P<hour>\d{1,2})h(?P<minute>\d{0,2})(?:\s+(?P<note>.+))?$", re.I)
_SCORE_RE = re.compile(r"^(?P<home>\d+)\s*[xX×]\s*(?P<away>\d+)$")
_SCORE_SEPARATOR_RE = re.compile(r"^[xX×]$")

CSV_FIELDS = [
    "match_id",
    "source_name",
    "source_url",
    "competition_name",
    "season",
    "match_number",
    "date_text",
    "time_text",
    "schedule_note",
    "home_team_name",
    "away_team_name",
    "score_home",
    "score_away",
    "status",
    "venue_name",
    "documents_url",
]


@dataclass(frozen=True)
class HtmlCell:
    text: str
    links: tuple[str, ...]


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


class _TableParser(HTMLParser):
    """Capture table rows without depending on CSS classes or presentation markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[HtmlCell]] = []
        self._row: list[HtmlCell] | None = None
        self._cell_parts: list[str] | None = None
        self._cell_links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_parts = []
            self._cell_links = []
        elif tag == "a" and self._cell_parts is not None:
            href = dict(attrs).get("href")
            if href:
                self._cell_links.append(href)

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._row is not None and self._cell_parts is not None:
            self._row.append(
                HtmlCell(
                    text=_clean_text(" ".join(self._cell_parts)),
                    links=tuple(self._cell_links),
                )
            )
            self._cell_parts = None
            self._cell_links = []
        elif tag == "tr" and self._row is not None:
            if any(cell.text for cell in self._row):
                self.rows.append(self._row)
            self._row = None


def fetch_public_html(url: str, *, timeout: int = 30) -> str:
    """Fetch a public source page without credentials."""
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def parse_ffer_fixture_table(
    html: str,
    *,
    source_url: str,
    season: int,
    competition_name: str,
) -> list[dict[str, Any]]:
    """Parse FFER schedule/result tables into source-neutral fixture records.

    FFER keeps the same match row before and after a game: date/time/opponents
    are the agenda, while a numeric ``N X N`` score makes the row post-match.
    Blank presentation cells and embedded images are ignored.
    """
    parser = _TableParser()
    parser.feed(html)
    competition_slug = _slug(competition_name)
    records: list[dict[str, Any]] = []
    seen: set[int] = set()

    for row in parser.rows:
        cells = [cell for cell in row if cell.text]
        if len(cells) < 6 or not re.fullmatch(r"\d+", cells[0].text):
            continue

        match_number = int(cells[0].text)
        date_match = _DATE_RE.fullmatch(cells[1].text)
        time_match = _TIME_RE.fullmatch(cells[2].text)
        if not date_match or not time_match:
            continue

        separator_index: int | None = None
        score: tuple[int, int] | None = None
        for index, cell in enumerate(cells[3:], start=3):
            score_match = _SCORE_RE.fullmatch(cell.text)
            if score_match:
                separator_index = index
                score = (int(score_match.group("home")), int(score_match.group("away")))
                break
            if _SCORE_SEPARATOR_RE.fullmatch(cell.text):
                separator_index = index
                break

        if separator_index is None or separator_index <= 3 or separator_index + 1 >= len(cells):
            continue
        if match_number in seen:
            continue
        seen.add(match_number)

        home_team = cells[3].text
        away_team = cells[separator_index + 1].text
        venue = cells[separator_index + 2].text if separator_index + 2 < len(cells) else ""

        documents_url = ""
        for cell in cells[separator_index + 3 :]:
            if cell.links:
                documents_url = urljoin(source_url, cell.links[0])
                break

        notes = [date_match.group("note"), time_match.group("note")]
        schedule_note = "; ".join(note for note in notes if note)
        score_home = score[0] if score else None
        score_away = score[1] if score else None

        records.append(
            {
                "match_id": f"ffer:{competition_slug}:{season}:{match_number:03d}",
                "source_name": "FFER",
                "source_url": source_url,
                "competition_name": competition_name,
                "season": season,
                "match_number": match_number,
                "date_text": cells[1].text,
                "time_text": cells[2].text,
                "schedule_note": schedule_note,
                "home_team_name": home_team,
                "away_team_name": away_team,
                "score_home": score_home,
                "score_away": score_away,
                "status": "finished" if score else "scheduled",
                "venue_name": venue,
                "documents_url": documents_url,
            }
        )

    return sorted(records, key=lambda record: int(record["match_number"]))


def read_fixture_csv(path: str | Path) -> dict[str, dict[str, str]]:
    source = Path(path)
    if not source.exists():
        return {}
    with source.open(encoding="utf-8", newline="") as handle:
        return {row["match_id"]: row for row in csv.DictReader(handle)}


def write_fixture_csv(records: list[dict[str, Any]], path: str | Path) -> None:
    """Write the current projection deterministically; observation time stays outside it."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow({field: "" if record.get(field) is None else record.get(field) for field in CSV_FIELDS})


def finished_transitions(
    previous: dict[str, dict[str, str]],
    current: list[dict[str, Any]],
    *,
    snapshot_id: str,
    observed_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Emit leads only when a previously known scheduled match becomes finished.

    An initial import deliberately emits no historical backlog.
    """
    if not previous:
        return []
    if observed_at is None:
        observed_at = datetime.now(UTC)

    signals: list[dict[str, Any]] = []
    for record in current:
        before = previous.get(str(record["match_id"]))
        if not before or before.get("status") == "finished" or record.get("status") != "finished":
            continue
        signals.append(
            {
                "signal_id": f"OFFICIAL-FINAL-{record['match_id']}",
                "detector_id": "official-match-finished-v1",
                "observed_at": observed_at.isoformat(),
                "entity_type": "fixture",
                "entity_id": str(record["match_id"]),
                "fixture_id": str(record["match_id"]),
                "league_id": _slug(str(record["competition_name"])),
                "season": str(record["season"]),
                "reason_codes": ["official_match_finished"],
                "source_snapshot": snapshot_id,
                "source_endpoint": str(record["source_url"]),
                "metrics": {
                    "home_team": record["home_team_name"],
                    "away_team": record["away_team_name"],
                    "score_home": record["score_home"],
                    "score_away": record["score_away"],
                    "venue": record["venue_name"],
                    "documents_url": record["documents_url"],
                },
            }
        )
    return signals
