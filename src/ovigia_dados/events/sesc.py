"""Collect public Sesc Rondônia event pages relevant to Porto Velho."""

from __future__ import annotations

import html as html_lib
import re
import unicodedata
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

import requests

from ovigia_dados.events.shared import EventObservation, fetch_text

SESC_BASE_URL = "https://sescro.com.br"
SESC_ARCHIVES = (
    "https://sescro.com.br/etn_category/cultura/",
    "https://sescro.com.br/etn_category/assistencia/",
    "https://sescro.com.br/etn-tags/lazer/",
)
_EVENT_PATH_RE = re.compile(r"^/etn/([^/?#]+)/?$", re.I)
_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_PORTO_VELHO_LOCATIONS = (
    "porto velho",
    "sesc esplanada",
    "sesc centro",
    "sesc campestre",
    "audicine do sesc esplanada",
    "teatro guapore",
    "porto velho shopping",
    "complexo madeira mamore",
)


class SescParseError(ValueError):
    pass


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.visible: list[str] = []
        self.headings: list[str] = []
        self._in_script = False
        self._heading = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"] or "")
        if tag in {"script", "style"}:
            self._in_script = True
        if tag in {"h1", "h2"}:
            self._heading = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._in_script = False
        if tag in {"h1", "h2"}:
            self._heading = False

    def handle_data(self, data: str) -> None:
        if self._in_script:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        self.visible.append(text)
        if self._heading:
            self.headings.append(text)


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", html_lib.unescape(value))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", plain).casefold().strip()


def canonicalize_event_url(url: str, base_url: str = SESC_BASE_URL) -> str | None:
    parsed = urlparse(urljoin(base_url, html_lib.unescape(url.strip())))
    if parsed.netloc.lower().split(":", 1)[0] not in {"sescro.com.br", "www.sescro.com.br"}:
        return None
    path = re.sub(r"/+", "/", parsed.path)
    match = _EVENT_PATH_RE.match(path)
    if not match:
        return None
    return urlunparse(("https", "sescro.com.br", f"/etn/{match.group(1)}/", "", "", ""))


def event_id_from_url(url: str) -> str:
    canonical = canonicalize_event_url(url)
    if canonical is None or (match := _EVENT_PATH_RE.match(urlparse(canonical).path)) is None:
        raise SescParseError(f"URL de evento Sesc inválida: {url}")
    return f"sescro-{match.group(1).lower()}"


def extract_event_urls(page: str, base_url: str) -> list[str]:
    parser = _Parser()
    parser.feed(page)
    urls = {url for href in parser.hrefs if (url := canonicalize_event_url(href, base_url))}
    return sorted(urls)


def _archive_page(url: str, page_number: int) -> str:
    if page_number <= 1:
        return url
    return f"{url.rstrip('/')}/page/{page_number}/"


def discover_event_urls(
    *,
    session: requests.Session | None = None,
    archives: tuple[str, ...] = SESC_ARCHIVES,
    pages: int = 3,
) -> list[str]:
    client = session or requests.Session()
    urls: set[str] = set()
    for archive in archives:
        for page_number in range(1, max(1, pages) + 1):
            page_url = _archive_page(archive, page_number)
            urls.update(extract_event_urls(fetch_text(page_url, client), page_url))
    return sorted(urls)


def _manual_fields(page: str) -> tuple[str, str, str]:
    parser = _Parser()
    parser.feed(page)
    visible = "\n".join(parser.visible)
    match = re.search(
        r"(?:^|\n)Evento\s*:\s*(?P<title>.*?)\s*\n?Data\s*:\s*(?P<date>.*?)"
        r"\s*\n?Local\s*:\s*(?P<location>.*?)(?=\n(?:Data|Hor[aá]rio)\s*:|\nAdicionar ao calend[aá]rio|\nNos acompanhe|\Z)",
        visible,
        re.I | re.S,
    )
    if not match:
        raise SescParseError("página sem trio editorial Evento/Data/Local")
    title = re.sub(r"\s+", " ", match.group("title")).strip(" -–—")
    date_text = re.sub(r"\s+", " ", match.group("date")).strip(" -–—")
    location = re.sub(r"\s+", " ", match.group("location")).strip(" -–—")
    if not title or not date_text or not location:
        raise SescParseError("trio editorial incompleto")
    return title, date_text, location


def parse_date_range(value: str) -> tuple[date, date | None]:
    text = _normalized(value)
    slash = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if slash:
        day, month, year = map(int, slash.groups())
        return date(year, month, day), None

    match = re.search(
        r"(?P<days>[0-9,\s\-aet]+?)\s+de\s+(?P<month>[a-z]+)\s+de\s+(?P<year>\d{4})",
        text,
    )
    if not match:
        raise SescParseError(f"data editorial sem ano/formato suportado: {value}")
    month = _MONTHS.get(match.group("month"))
    if month is None:
        raise SescParseError(f"mês não reconhecido: {value}")
    days = [int(item) for item in re.findall(r"\d{1,2}", match.group("days"))]
    if not days:
        raise SescParseError(f"dia não reconhecido: {value}")
    year = int(match.group("year"))
    start = date(year, month, days[0])
    end = date(year, month, days[-1]) if len(days) > 1 else None
    return start, end


def is_porto_velho_location(value: str) -> bool:
    normalized = _normalized(value)
    return any(marker in normalized for marker in _PORTO_VELHO_LOCATIONS)


def parse_event_page(
    page: str,
    source_url: str,
    *,
    observed_at: datetime | None = None,
) -> EventObservation:
    canonical = canonicalize_event_url(source_url)
    if not canonical:
        raise SescParseError("fonte sem URL canônica de evento")
    title, date_text, location = _manual_fields(page)
    if not is_porto_velho_location(location):
        raise SescParseError(f"local não confirmado em Porto Velho: {location}")
    starts_on, ends_on = parse_date_range(date_text)
    return EventObservation(
        event_id=event_id_from_url(canonical),
        source_platform="sescro",
        source_url=canonical,
        title=title,
        starts_on=starts_on,
        ends_on=ends_on,
        venue_name=location,
        city="Porto Velho",
        state="RO",
        status="unknown",
        observed_at=observed_at or datetime.now(UTC),
    )


def hydrate_event(
    url: str,
    *,
    session: requests.Session | None = None,
    observed_at: datetime | None = None,
) -> EventObservation:
    canonical = canonicalize_event_url(url)
    if not canonical:
        raise SescParseError(url)
    return parse_event_page(
        fetch_text(canonical, session),
        canonical,
        observed_at=observed_at,
    )
