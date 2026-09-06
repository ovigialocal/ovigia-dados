"""Collect public city events from the municipal PVH Mais portal."""

from __future__ import annotations

import html as html_lib
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from ovigia_dados.events.shared import EventObservation, event_content_hash, fetch_text

PVHMAIS_EVENTS_URL = "https://pvhmais.portovelho.ro.gov.br/site/eventos"
_EVENT_PATH_RE = re.compile(r"^/site/eventos/(\d+)$")
_DATE_KEYS = ("start_date", "starts_at", "start_at", "date_start", "begin_at")
_END_DATE_KEYS = ("end_date", "ends_at", "end_at", "date_end", "finish_at")


class PvhMaisParseError(ValueError):
    pass


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parameters: str | None = None
        self.hrefs: list[str] = []
        self.h1: list[str] = []
        self.visible: list[str] = []
        self._in_h1 = False
        self._in_script = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "div" and values.get("id") == "root" and values.get("data-parameters"):
            self.parameters = values["data-parameters"]
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"] or "")
        if tag == "h1":
            self._in_h1 = True
        if tag == "script":
            self._in_script = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._in_h1 = False
        if tag == "script":
            self._in_script = False

    def handle_data(self, data: str) -> None:
        if self._in_script:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        self.visible.append(text)
        if self._in_h1:
            self.h1.append(text)


def canonicalize_event_url(url: str, base_url: str = PVHMAIS_EVENTS_URL) -> str | None:
    parsed = urlparse(urljoin(base_url, html_lib.unescape(url.strip())))
    if parsed.netloc.lower().split(":", 1)[0] != "pvhmais.portovelho.ro.gov.br":
        return None
    path = re.sub(r"/+", "/", parsed.path.rstrip("/"))
    if not _EVENT_PATH_RE.match(path):
        return None
    return urlunparse(("https", "pvhmais.portovelho.ro.gov.br", path, "", "", ""))


def event_id_from_url(url: str) -> str:
    canonical = canonicalize_event_url(url)
    if canonical is None or (match := _EVENT_PATH_RE.match(urlparse(canonical).path)) is None:
        raise PvhMaisParseError(f"URL PVH+ inválida: {url}")
    return f"pvhmais-{match.group(1)}"


def _objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _parameters(parser: _PageParser) -> dict[str, Any]:
    if not parser.parameters:
        return {}
    try:
        value = json.loads(html_lib.unescape(parser.parameters))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _first(obj: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        value = obj.get(name)
        if value not in (None, "", [], {}):
            return value
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        value = _first(value, ("name", "title", "label", "text", "description"))
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


def _event_object(payload: dict[str, Any], numeric_id: int) -> dict[str, Any] | None:
    best: tuple[int, dict[str, Any]] | None = None
    for obj in _objects(payload):
        try:
            same_id = int(obj.get("id")) == numeric_id
        except (TypeError, ValueError):
            same_id = False
        if not same_id:
            continue

        score = 0
        if _first(obj, ("name", "title")):
            score += 3
        if _first(obj, _DATE_KEYS):
            score += 3
        if _first(obj, ("description", "location", "address", "place", "venue")):
            score += 2
        if obj.get("action_object_type") == "Event":
            score -= 3
        if best is None or score > best[0]:
            best = (score, obj)
    return best[1] if best and best[0] >= 3 else None


def _nested_location(obj: dict[str, Any]) -> dict[str, Any]:
    for key in ("location", "place", "venue", "address"):
        value = obj.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _status(value: Any) -> str:
    normalized = str(value or "").casefold()
    if any(token in normalized for token in ("cancel", "canceled", "cancelado")):
        return "cancelled"
    if any(token in normalized for token in ("postpon", "adiado")):
        return "postponed"
    if any(token in normalized for token in ("resched", "remarc")):
        return "rescheduled"
    if any(token in normalized for token in ("complete", "finished", "ended", "encerr")):
        return "completed"
    if normalized:
        return "scheduled"
    return "unknown"


def _address_text(location: dict[str, Any], obj: dict[str, Any]) -> str | None:
    direct = _first(
        location,
        ("formatted_address", "full_address", "address", "street_address", "address_line"),
    )
    if isinstance(direct, str):
        return _text(direct)
    direct = _first(obj, ("formatted_address", "full_address", "address_text"))
    return _text(direct)


def parse_event_page(
    page: str, source_url: str, *, observed_at: datetime | None = None
) -> EventObservation:
    canonical = canonicalize_event_url(source_url)
    if not canonical:
        raise PvhMaisParseError("fonte sem URL canônica")
    numeric_id = int(event_id_from_url(canonical).split("-", 1)[1])
    parser = _PageParser()
    parser.feed(page)
    payload = _parameters(parser)
    event = _event_object(payload, numeric_id)
    observed_at = observed_at or datetime.now(UTC)

    if event:
        location = _nested_location(event)
        title = _text(_first(event, ("name", "title")))
        if not title:
            raise PvhMaisParseError("evento sem título")
        city = _text(_first(location, ("city", "city_name", "address_locality"))) or "Porto Velho"
        state = _text(_first(location, ("state", "state_code", "uf", "address_region"))) or "RO"
        venue_name = _text(_first(location, ("name", "title", "venue_name", "place_name")))
        organizer = _text(
            _first(event, ("organizer", "organizer_name", "producer", "producer_name", "owner"))
        )
        observation = EventObservation(
            event_id=f"pvhmais-{numeric_id}",
            source_platform="pvhmais",
            source_url=canonical,
            title=title,
            starts_at=_dt(_first(event, _DATE_KEYS)),
            ends_at=_dt(_first(event, _END_DATE_KEYS)),
            venue_name=venue_name,
            address=_address_text(location, event),
            city=city,
            state=state,
            organizer=organizer,
            status=_status(_first(event, ("status", "event_status", "state"))),
            observed_at=observed_at,
        )
        observation.content_hash = event_content_hash(observation)
        return observation

    title = _text(parser.h1[0] if parser.h1 else None)
    if not title or title.casefold() in {"porto velho", "eventos"}:
        raise PvhMaisParseError("página pública não expôs objeto de evento verificável")
    visible = " ".join(parser.visible)
    observation = EventObservation(
        event_id=f"pvhmais-{numeric_id}",
        source_platform="pvhmais",
        source_url=canonical,
        title=title,
        city="Porto Velho" if "porto velho" in visible.casefold() else None,
        state="RO" if "porto velho" in visible.casefold() else None,
        status="unknown",
        observed_at=observed_at,
    )
    observation.content_hash = event_content_hash(observation)
    return observation


def discover_promoted_event_ids(page: str) -> list[int]:
    parser = _PageParser()
    parser.feed(page)
    ids: set[int] = set()
    for href in parser.hrefs:
        canonical = canonicalize_event_url(href)
        if canonical:
            ids.add(int(event_id_from_url(canonical).split("-", 1)[1]))
    for obj in _objects(_parameters(parser)):
        if obj.get("action_object_type") != "Event":
            continue
        try:
            ids.add(int(obj["action_object_id"]))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(ids)


def scan_ids_from_listing(
    page: str, *, bootstrap_max: int = 150, lookahead: int = 30
) -> list[int]:
    promoted = discover_promoted_event_ids(page)
    ceiling = max([bootstrap_max, *(event_id + lookahead for event_id in promoted)])
    return list(range(1, ceiling + 1))


def hydrate_event(
    numeric_id: int,
    *,
    session: requests.Session | None = None,
    observed_at: datetime | None = None,
) -> EventObservation:
    url = f"{PVHMAIS_EVENTS_URL}/{numeric_id}"
    return parse_event_page(fetch_text(url, session), url, observed_at=observed_at)
