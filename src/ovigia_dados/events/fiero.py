"""Extract future public Porto Velho events from Sistema FIERO news pages."""

from __future__ import annotations

import html as html_lib
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

import requests

from ovigia_dados.events.shared import EventObservation, fetch_text

FIERO_LISTINGS = (
    "https://portal.fiero.org.br/imprensa",
    "https://portal.fiero.org.br/sesi/imprensa",
)
_ARTICLE_RE = re.compile(
    r"^/(?:sesi/)?imprensa/noticia/(?P<year>\d{4})/(?P<month>\d{2})/[^/?#]+/(?P<id>\d+)$",
    re.I,
)
_MONTHS = {
    "janeiro": 1,
    "january": 1,
    "fevereiro": 2,
    "february": 2,
    "marco": 3,
    "march": 3,
    "abril": 4,
    "april": 4,
    "maio": 5,
    "may": 5,
    "junho": 6,
    "june": 6,
    "julho": 7,
    "july": 7,
    "agosto": 8,
    "august": 8,
    "setembro": 9,
    "september": 9,
    "outubro": 10,
    "october": 10,
    "novembro": 11,
    "november": 11,
    "dezembro": 12,
    "december": 12,
}
_PUBLIC_SIGNALS = (
    "aberto ao publico",
    "aberta ao publico",
    "publico em geral",
    "inscricoes",
    "inscricao gratuita",
    "inscricoes gratuitas",
)
_PORTO_VELHO_VENUES = (
    "espaco alternativo",
    "teatro banzeiros",
    "teatro guapore",
    "sesc esplanada",
    "sesi escola",
    "auditorio do edificio sede do tjro",
    "auditorio do tjro",
)


class FieroParseError(ValueError):
    pass


@dataclass(frozen=True)
class _CandidateDate:
    value: date
    priority: int
    start: int
    end: int


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.h1: list[str] = []
        self.visible: list[str] = []
        self._heading = False
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"] or "")
        if tag == "h1":
            self._heading = True
        if tag in {"script", "style"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._heading = False
        if tag in {"script", "style"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        self.visible.append(text)
        if self._heading:
            self.h1.append(text)


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", html_lib.unescape(value))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", plain).casefold().strip()


def canonicalize_article_url(url: str, base_url: str = FIERO_LISTINGS[0]) -> str | None:
    parsed = urlparse(urljoin(base_url, html_lib.unescape(url.strip())))
    if parsed.netloc.lower().split(":", 1)[0] != "portal.fiero.org.br":
        return None
    path = re.sub(r"/+", "/", parsed.path.rstrip("/"))
    if not _ARTICLE_RE.match(path):
        return None
    return urlunparse(("https", "portal.fiero.org.br", path, "", "", ""))


def article_id_from_url(url: str) -> str:
    canonical = canonicalize_article_url(url)
    if canonical is None or (match := _ARTICLE_RE.match(urlparse(canonical).path)) is None:
        raise FieroParseError(f"URL FIERO inválida: {url}")
    return match.group("id")


def extract_article_urls(page: str, base_url: str) -> list[str]:
    parser = _Parser()
    parser.feed(page)
    urls = {url for href in parser.hrefs if (url := canonicalize_article_url(href, base_url))}
    return sorted(urls, key=lambda url: int(article_id_from_url(url)), reverse=True)


def _listing_page(url: str, page_number: int) -> str:
    if page_number <= 1:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}page={page_number}"


def discover_article_urls(
    *,
    session: requests.Session | None = None,
    listings: tuple[str, ...] = FIERO_LISTINGS,
    pages: int = 2,
) -> list[str]:
    client = session or requests.Session()
    urls: set[str] = set()
    for listing in listings:
        for page_number in range(1, max(1, pages) + 1):
            page_url = _listing_page(listing, page_number)
            urls.update(extract_article_urls(fetch_text(page_url, client), page_url))
    return sorted(urls, key=lambda url: int(article_id_from_url(url)), reverse=True)


def _month_number(value: str) -> int | None:
    return _MONTHS.get(_normalized(value))


def _publication_datetime(text: str) -> datetime:
    match = re.search(
        r"\b(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)\s+de\s+(\d{4})\s*-\s*(\d{1,2})h(\d{2})\b",
        text,
        re.I,
    )
    if not match:
        raise FieroParseError("data de publicação não encontrada")
    month = _month_number(match.group(2))
    if month is None:
        raise FieroParseError(f"mês de publicação não reconhecido: {match.group(2)}")
    return datetime(
        int(match.group(3)),
        month,
        int(match.group(1)),
        int(match.group(4)),
        int(match.group(5)),
        tzinfo=UTC,
    )


def _explicit_dates(text: str) -> list[_CandidateDate]:
    candidates: list[_CandidateDate] = []
    for match in re.finditer(
        r"\b(\d{1,2})(?:º)?\s+de\s+([A-Za-zÀ-ÿ]+)\s+de\s+(\d{4})\b",
        text,
        re.I,
    ):
        month = _month_number(match.group(2))
        if month is None:
            continue
        try:
            value = date(int(match.group(3)), month, int(match.group(1)))
        except ValueError:
            continue
        before = _normalized(text[max(0, match.start() - 120) : match.start()])
        priority = 1
        if re.search(r"\bdata\s*:\s*$", before):
            priority = 4
        elif any(
            marker in before
            for marker in (
                "realizacao marcada para",
                "realizacao esta marcada para",
                "marcada para",
                "marcado para",
                "programado para",
                "programada para",
                "acontece em",
                "acontecera em",
                "promove no proximo dia",
                "promove no dia",
                "sera realizado em",
                "sera realizada em",
            )
        ):
            priority = 3
        elif any(marker in before for marker in ("evento", "encontro", "corrida", "seminario")):
            priority = 2
        candidates.append(_CandidateDate(value, priority, match.start(), match.end()))
    return candidates


def _event_date(text: str, published: datetime) -> _CandidateDate:
    candidates = [item for item in _explicit_dates(text) if item.value > published.date()]
    if not candidates:
        raise FieroParseError("matéria sem data futura explícita")
    candidates.sort(key=lambda item: (-item.priority, item.value, item.start))
    return candidates[0]


def _field(values: list[str], label: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(label)}\s*:\s*(.+)$", re.I)
    for value in values:
        if match := pattern.match(value):
            return match.group(1).strip()
    return None


def _public_access(text: str) -> bool:
    normalized = _normalized(text)
    return any(signal in normalized for signal in _PUBLIC_SIGNALS)


def _porto_velho_evidence(text: str, candidate: _CandidateDate, values: list[str]) -> bool:
    for label in ("Endereço", "Endereco", "Local"):
        if (value := _field(values, label)) and (
            "porto velho" in _normalized(value)
            or any(venue in _normalized(value) for venue in _PORTO_VELHO_VENUES)
        ):
            return True
    context = _normalized(text[max(0, candidate.start - 220) : candidate.end + 220])
    if "porto velho" in context:
        return True
    return any(venue in context for venue in _PORTO_VELHO_VENUES)


def _event_title(headline: str, text: str) -> str:
    quote_patterns = (
        r"(?:evento|encontro|conferencia|seminario|forum)\s+[\"“](.+?)[\"”]",
        r"(?:evento|encontro|conferencia|seminario|forum)\s+'(.+?)'",
    )
    normalized_source = unicodedata.normalize("NFKC", text)
    for pattern in quote_patterns:
        if match := re.search(pattern, normalized_source, re.I):
            candidate = re.sub(r"\s+", " ", match.group(1)).strip()
            if 4 <= len(candidate) <= 180:
                return candidate
    title = re.sub(
        r"\s+(?:est[aá]\s+)?(?:confirmad[ao]|marcad[ao]|programad[ao])\b.*$",
        "",
        headline,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", title).strip(" -–—")


def _clock(values: list[str]) -> time | None:
    raw = _field(values, "Horário") or _field(values, "Horario")
    if not raw:
        return None
    match = re.search(r"\b(\d{1,2})(?:h|:)(\d{2})?\b", raw, re.I)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    try:
        return time(hour, minute)
    except ValueError:
        return None


def parse_article(
    page: str,
    source_url: str,
    *,
    observed_at: datetime | None = None,
) -> EventObservation:
    canonical = canonicalize_article_url(source_url)
    if not canonical:
        raise FieroParseError("fonte sem URL canônica")
    parser = _Parser()
    parser.feed(page)
    headline = re.sub(r"\s+", " ", " ".join(parser.h1)).strip()
    if not headline:
        raise FieroParseError("matéria sem título")
    text = "\n".join(parser.visible)
    published = _publication_datetime(text)
    candidate = _event_date(text, published)
    if not _public_access(text):
        raise FieroParseError("matéria sem evidência de acesso público ou inscrições")
    if not _porto_velho_evidence(text, candidate, parser.visible):
        raise FieroParseError("evento sem evidência contextual de Porto Velho")

    event_title = _event_title(headline, text)
    venue = _field(parser.visible, "Local")
    address = _field(parser.visible, "Endereço") or _field(parser.visible, "Endereco")
    event_time = _clock(parser.visible)
    starts_at = (
        datetime.combine(candidate.value, event_time, tzinfo=UTC) if event_time is not None else None
    )
    return EventObservation(
        event_id=f"fiero-{article_id_from_url(canonical)}",
        source_platform="fiero",
        source_url=canonical,
        title=event_title,
        starts_at=starts_at,
        starts_on=None if starts_at else candidate.value,
        venue_name=venue,
        address=address,
        city="Porto Velho",
        state="RO",
        organizer="Sistema FIERO",
        status="scheduled",
        observed_at=observed_at or datetime.now(UTC),
    )


def hydrate_article(
    url: str,
    *,
    session: requests.Session | None = None,
    observed_at: datetime | None = None,
) -> EventObservation:
    canonical = canonicalize_article_url(url)
    if not canonical:
        raise FieroParseError(url)
    return parse_article(fetch_text(canonical, session), canonical, observed_at=observed_at)
