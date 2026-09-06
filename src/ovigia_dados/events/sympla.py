"""Coleta pública de eventos Sympla e histórico Wayback para Porto Velho."""

from __future__ import annotations

import hashlib
import html as html_lib
import json
import logging
import re
import unicodedata
from collections.abc import Iterable
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote, urljoin, urlparse, urlunparse

from pydantic import BaseModel, Field
import requests

logger = logging.getLogger(__name__)
SYMPLA_LISTING_URL = "https://www.sympla.com.br/eventos/porto-velho-ro/para-voce"
CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
_EVENT_RE = re.compile(r"^/evento/(?:[^/?#]+/)+(\d+)$")
_MONTHS = {
    "jan": 1,
    "fev": 2,
    "mar": 3,
    "abr": 4,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "out": 10,
    "nov": 11,
    "dez": 12,
}


class SymplaParseError(ValueError):
    pass


class CdxSnapshot(BaseModel):
    timestamp: str
    original: str
    statuscode: str = "200"
    digest: str | None = None
    mimetype: str | None = None

    @property
    def replay_url(self) -> str:
        return f"https://web.archive.org/web/{self.timestamp}id_/{self.original}"


class EventObservation(BaseModel):
    event_id: str
    source_platform: str = "sympla"
    source_url: str
    title: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    venue_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    organizer: str | None = None
    status: Literal[
        "scheduled", "cancelled", "postponed", "rescheduled", "completed", "unknown"
    ] = "scheduled"
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    observation_origin: Literal["live", "wayback"] = "live"
    archive_timestamp: str | None = None
    content_hash: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.content_hash:
            self.content_hash = event_content_hash(self)


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.json_ld: list[str] = []
        self.h1: list[str] = []
        self.visible: list[str] = []
        self._script = False
        self._json = False
        self._h1 = False
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"] or "")
        if tag == "script":
            self._script = True
            self._json = (values.get("type") or "").lower() == "application/ld+json"
            self._buf = []
        if tag == "h1":
            self._h1 = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            if self._json and self._buf:
                self.json_ld.append("".join(self._buf))
            self._script = self._json = False
        if tag == "h1":
            self._h1 = False

    def handle_data(self, data: str) -> None:
        if self._json:
            self._buf.append(data)
            return
        text = data.strip()
        if self._script or not text:
            return
        self.visible.append(text)
        if self._h1:
            self.h1.append(text)


def canonicalize_event_url(url: str, base_url: str = SYMPLA_LISTING_URL) -> str | None:
    absolute = urljoin(base_url, html_lib.unescape(url.strip()))
    parsed = urlparse(absolute)
    if parsed.netloc.lower() == "web.archive.org":
        match = re.match(r"^/web/[^/]+/(https?://.+)$", unquote(parsed.path))
        return canonicalize_event_url(match.group(1), base_url) if match else None
    if parsed.netloc.lower().split(":", 1)[0] not in {"sympla.com.br", "www.sympla.com.br"}:
        return None
    path = re.sub(r"/+", "/", parsed.path.rstrip("/"))
    if not _EVENT_RE.match(path):
        return None
    return urlunparse(("https", "www.sympla.com.br", path, "", "", ""))


def event_id_from_url(url: str) -> str:
    canonical = canonicalize_event_url(url)
    if canonical is None or (match := _EVENT_RE.match(urlparse(canonical).path)) is None:
        raise SymplaParseError(f"URL Sympla inválida: {url}")
    return f"sympla-{match.group(1)}"


def extract_event_urls(page: str, base_url: str = SYMPLA_LISTING_URL) -> list[str]:
    parser = _Parser()
    parser.feed(page)
    urls = {u for href in parser.hrefs if (u := canonicalize_event_url(href, base_url))}
    return sorted(urls, key=lambda u: int(event_id_from_url(u).split("-", 1)[1]))


def _objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("name")
    if value is None:
        return None
    return re.sub(r"\s+", " ", str(value)).strip() or None


def _dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _status(value: Any) -> str:
    text = str(value or "").lower()
    for needle, status in (
        ("cancel", "cancelled"),
        ("postpon", "postponed"),
        ("resched", "rescheduled"),
        ("complete", "completed"),
    ):
        if needle in text:
            return status
    return "scheduled" if value else "unknown"


def _fallback_dates(text: str) -> tuple[datetime | None, datetime | None]:
    pattern = re.compile(
        r"(\d{1,2})\s+([a-zç]{3})\s*-\s*(\d{4})\s*[•·]\s*(\d{2}:\d{2})"
        r"(?:\s*>\s*(\d{1,2})\s+([a-zç]{3})\s*-\s*(\d{4})\s*[•·]\s*(\d{2}:\d{2}))?",
        re.I,
    )
    match = pattern.search(text)
    if not match:
        return None, None

    def build(day: str, month: str, year: str, clock: str) -> datetime | None:
        number = _MONTHS.get(month.lower())
        if not number:
            return None
        hour, minute = map(int, clock.split(":"))
        return datetime(int(year), number, int(day), hour, minute)

    start = build(*match.group(1, 2, 3, 4))
    end = build(*match.group(5, 6, 7, 8)) if match.group(5) else None
    return start, end


def parse_event_page(
    page: str,
    source_url: str,
    *,
    observed_at: datetime | None = None,
    observation_origin: Literal["live", "wayback"] = "live",
    archive_timestamp: str | None = None,
) -> EventObservation:
    source_url = canonicalize_event_url(source_url) or ""
    if not source_url:
        raise SymplaParseError("fonte sem URL canônica")
    parser = _Parser()
    parser.feed(page)
    event: dict[str, Any] | None = None
    for raw in parser.json_ld:
        try:
            payload = json.loads(html_lib.unescape(raw))
        except json.JSONDecodeError:
            continue
        event = next(
            (
                obj
                for obj in _objects(payload)
                if "event"
                in {
                    str(t).lower()
                    for t in (
                        obj.get("@type")
                        if isinstance(obj.get("@type"), list)
                        else [obj.get("@type")]
                    )
                    if t
                }
            ),
            None,
        )
        if event:
            break

    observed_at = observed_at or datetime.now(UTC)
    if event:
        location = event.get("location") if isinstance(event.get("location"), dict) else {}
        raw_address = location.get("address")
        address = raw_address if isinstance(raw_address, dict) else {}
        street = _text(address.get("streetAddress")) if address else _text(raw_address)
        title = _text(event.get("name"))
        if not title:
            raise SymplaParseError("evento JSON-LD sem título")
        return EventObservation(
            event_id=event_id_from_url(source_url),
            source_url=source_url,
            title=title,
            starts_at=_dt(event.get("startDate")),
            ends_at=_dt(event.get("endDate")),
            venue_name=_text(location.get("name")),
            address=street,
            city=_text(address.get("addressLocality")),
            state=_text(address.get("addressRegion")),
            organizer=_text(event.get("organizer")),
            status=_status(event.get("eventStatus")),
            observed_at=observed_at,
            observation_origin=observation_origin,
            archive_timestamp=archive_timestamp,
        )

    visible = " ".join(parser.visible)
    title = _text(parser.h1[0] if parser.h1 else None)
    if not title:
        raise SymplaParseError("evento sem JSON-LD e sem H1")
    starts_at, ends_at = _fallback_dates(visible)
    normalized = _normalized(visible)
    city = "Porto Velho" if "porto velho" in normalized else None
    state = "RO" if city and re.search(r"porto velho\s*[-,]\s*ro\b", normalized) else None
    status = (
        "cancelled"
        if "evento cancelado" in normalized
        else "completed"
        if "evento encerrado" in normalized
        else "unknown"
    )
    return EventObservation(
        event_id=event_id_from_url(source_url),
        source_url=source_url,
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
        city=city,
        state=state,
        status=status,
        observed_at=observed_at,
        observation_origin=observation_origin,
        archive_timestamp=archive_timestamp,
    )


def event_content_hash(event: EventObservation) -> str:
    data = event.model_dump(
        mode="json",
        exclude={"observed_at", "content_hash", "archive_timestamp", "observation_origin"},
    )
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _normalized(value: str | None) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().strip()


def is_porto_velho(event: EventObservation) -> bool:
    return _normalized(event.city) == "porto velho" and _normalized(event.state) in {
        "",
        "ro",
        "rondonia",
    }


def fetch_text(url: str, session: requests.Session | None = None) -> str:
    client = session or requests.Session()
    response = client.get(url, timeout=30, headers={"User-Agent": "ovigia-dados/0.1"})
    response.raise_for_status()
    return response.text


def query_cdx(
    url: str, *, session: requests.Session | None = None, limit: int = 100
) -> list[CdxSnapshot]:
    client = session or requests.Session()
    response = client.get(
        CDX_ENDPOINT,
        params={
            "url": url,
            "output": "json",
            "fl": "timestamp,original,statuscode,digest,mimetype",
            "filter": "statuscode:200",
            "collapse": "digest",
            "limit": max(1, limit),
        },
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        return []
    header, *records = rows
    return [
        CdxSnapshot.model_validate(dict(zip(header, row, strict=True)))
        for row in records
        if len(row) == len(header)
    ]


def discover_live_event_urls(
    session: requests.Session | None = None, listing_url: str = SYMPLA_LISTING_URL
) -> list[str]:
    return extract_event_urls(fetch_text(listing_url, session), listing_url)


def discover_historical_event_urls(
    *,
    session: requests.Session | None = None,
    listing_url: str = SYMPLA_LISTING_URL,
    snapshot_limit: int = 8,
) -> list[str]:
    client = session or requests.Session()
    urls: set[str] = set()
    for snapshot in query_cdx(listing_url, session=client)[-max(snapshot_limit, 0) :]:
        try:
            urls.update(extract_event_urls(fetch_text(snapshot.replay_url, client), listing_url))
        except requests.RequestException as exc:
            logger.warning("snapshot Wayback indisponível: %s", exc)
    return sorted(urls)


def hydrate_live_event(
    url: str,
    *,
    session: requests.Session | None = None,
    observed_at: datetime | None = None,
) -> EventObservation:
    canonical = canonicalize_event_url(url)
    if not canonical:
        raise SymplaParseError(url)
    return parse_event_page(fetch_text(canonical, session), canonical, observed_at=observed_at)


def hydrate_latest_archived_event(
    url: str, *, session: requests.Session | None = None
) -> EventObservation | None:
    client = session or requests.Session()
    canonical = canonicalize_event_url(url)
    if not canonical:
        raise SymplaParseError(url)
    snapshots = query_cdx(canonical, session=client)
    if not snapshots:
        return None
    snapshot = snapshots[-1]
    try:
        observed_at = datetime.strptime(snapshot.timestamp, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    except ValueError:
        observed_at = datetime.now(UTC)
    return parse_event_page(
        fetch_text(snapshot.replay_url, client),
        canonical,
        observed_at=observed_at,
        observation_origin="wayback",
        archive_timestamp=snapshot.timestamp,
    )


def _latest_hashes(root: Path) -> dict[str, str]:
    latest: dict[str, tuple[str, str]] = {}
    paths = root.rglob("*.md") if root.exists() else []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        event = re.search(r'^event_id:\s*["\']?([^"\'\n]+)', text, re.M)
        digest = re.search(r'^content_hash:\s*["\']?([^"\'\n]+)', text, re.M)
        if event and digest and (
            event.group(1) not in latest or path.name > latest[event.group(1)][0]
        ):
            latest[event.group(1)] = (path.name, digest.group(1))
    return {key: value[1] for key, value in latest.items()}


def _line(key: str, value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.isoformat()
    return f"{key}: {json.dumps(str(value), ensure_ascii=False)}"


def materialize_observations(
    events: Iterable[EventObservation],
    *,
    identities_root: str | Path,
    observations_root: str | Path,
) -> list[Path]:
    identities, observations = Path(identities_root), Path(observations_root)
    identities.mkdir(parents=True, exist_ok=True)
    observations.mkdir(parents=True, exist_ok=True)
    hashes = _latest_hashes(observations)
    created: list[Path] = []

    for event in events:
        identity = identities / f"{event.event_id}.md"
        if not identity.exists():
            lines = [
                "---",
                'okf_version: "0.2"',
                'type: "city-event"',
                _line("event_id", event.event_id),
                _line("source_platform", event.source_platform),
                _line("source_url", event.source_url),
                _line("first_seen_at", event.observed_at),
                "---",
                "",
                f"# {event.title}",
                "",
                "Identidade estável de evento público.",
                "",
            ]
            identity.write_text(
                "\n".join(line for line in lines if line), encoding="utf-8"
            )
            created.append(identity)

        if hashes.get(event.event_id) == event.content_hash:
            continue
        stamp = event.observed_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        event_dir = observations / event.event_id
        event_dir.mkdir(parents=True, exist_ok=True)
        path = event_dir / f"{stamp}-{event.observation_origin}.md"
        fields = [
            ("event_id", event.event_id),
            ("source_platform", event.source_platform),
            ("source_url", event.source_url),
            ("observed_at", event.observed_at),
            ("observation_origin", event.observation_origin),
            ("archive_timestamp", event.archive_timestamp),
            ("content_hash", event.content_hash),
            ("title", event.title),
            ("starts_at", event.starts_at),
            ("ends_at", event.ends_at),
            ("venue_name", event.venue_name),
            ("address", event.address),
            ("city", event.city),
            ("state", event.state),
            ("organizer", event.organizer),
            ("status", event.status),
        ]
        lines = ["---", 'okf_version: "0.2"', 'type: "event-observation"']
        lines.extend(line for key, value in fields if (line := _line(key, value)))
        lines.extend(
            [
                "---",
                "",
                f"# Observação — {event.title}",
                "",
                "Estado público normalizado da fonte indicada.",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        hashes[event.event_id] = event.content_hash
        created.append(path)
    return created
