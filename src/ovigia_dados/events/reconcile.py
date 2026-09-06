"""Reconcile source-specific city events into canonical event entities."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

import yaml

from ovigia_dados.events.shared import EventObservation

_STOPWORDS = {
    "a",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "por",
}


@dataclass(frozen=True)
class EventReconciliation:
    reconciliation_id: str
    left_event_id: str
    right_event_id: str
    decision: Literal["equivalent", "review"]
    score: float
    title_similarity: float
    same_local_date: bool
    venue_similarity: float
    organizer_similarity: float
    evaluated_at: datetime
    left_content_hash: str
    right_content_hash: str


def _normalized_tokens(value: str | None) -> list[str]:
    decomposed = unicodedata.normalize("NFKD", value or "")
    plain = "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()
    tokens = re.findall(r"[a-z0-9]+", plain)
    return [token for token in tokens if token not in _STOPWORDS]


def text_similarity(left: str | None, right: str | None) -> float:
    left_tokens = _normalized_tokens(left)
    right_tokens = _normalized_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    left_text = " ".join(left_tokens)
    right_text = " ".join(right_tokens)
    sequence = SequenceMatcher(None, left_text, right_text).ratio()
    left_set, right_set = set(left_tokens), set(right_tokens)
    union = left_set | right_set
    jaccard = len(left_set & right_set) / len(union) if union else 0.0
    return round((sequence * 0.6) + (jaccard * 0.4), 6)


def _pair_id(left: EventObservation, right: EventObservation) -> str:
    event_ids = sorted((left.event_id, right.event_id))
    hashes = {left.event_id: left.content_hash, right.event_id: right.content_hash}
    raw = "|".join([*event_ids, *(hashes[event_id] for event_id in event_ids)])
    return f"reconciliation-{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def _start_date(event: EventObservation) -> date | None:
    if event.starts_at:
        return event.starts_at.date()
    return event.starts_on


def evaluate_pair(
    left: EventObservation,
    right: EventObservation,
    *,
    evaluated_at: datetime | None = None,
) -> EventReconciliation | None:
    if left.event_id == right.event_id or left.source_platform == right.source_platform:
        return None

    title = text_similarity(left.title, right.title)
    venue = text_similarity(left.venue_name, right.venue_name)
    organizer = text_similarity(left.organizer, right.organizer)
    left_date = _start_date(left)
    right_date = _start_date(right)
    same_date = bool(left_date and right_date and left_date == right_date)

    decision: Literal["equivalent", "review"] | None = None
    if same_date:
        score = (0.68 * title) + 0.22 + (0.07 * venue) + (0.03 * organizer)
        strong_title = title >= 0.84 and score >= 0.80
        title_and_venue = title >= 0.72 and venue >= 0.75 and score >= 0.79
        if strong_title or title_and_venue:
            decision = "equivalent"
        elif title >= 0.62 and score >= 0.68:
            decision = "review"
    elif left_date is None or right_date is None:
        score = (0.8 * title) + (0.15 * venue) + (0.05 * organizer)
        if title >= 0.88 and score >= 0.84:
            decision = "review"
    else:
        score = (0.82 * title) + (0.13 * venue) + (0.05 * organizer)
        if title >= 0.94 and venue >= 0.70 and score >= 0.88:
            decision = "review"

    if decision is None:
        return None

    ordered = sorted((left, right), key=lambda item: item.event_id)
    return EventReconciliation(
        reconciliation_id=_pair_id(left, right),
        left_event_id=ordered[0].event_id,
        right_event_id=ordered[1].event_id,
        decision=decision,
        score=round(score, 6),
        title_similarity=title,
        same_local_date=same_date,
        venue_similarity=venue,
        organizer_similarity=organizer,
        evaluated_at=evaluated_at or datetime.now(UTC),
        left_content_hash=ordered[0].content_hash,
        right_content_hash=ordered[1].content_hash,
    )


def reconcile_observations(
    observations: Iterable[EventObservation], *, evaluated_at: datetime | None = None
) -> list[EventReconciliation]:
    items = sorted(observations, key=lambda item: item.event_id)
    results: list[EventReconciliation] = []
    for index, left in enumerate(items):
        for right in items[index + 1 :]:
            match = evaluate_pair(left, right, evaluated_at=evaluated_at)
            if match is not None:
                results.append(match)
    return results


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\n|\Z)", text, re.S)
    if not match:
        return {}
    try:
        payload = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_latest_observations(root: str | Path) -> list[EventObservation]:
    base = Path(root)
    latest: dict[str, EventObservation] = {}
    if not base.exists():
        return []
    for path in base.rglob("*.md"):
        payload = _frontmatter(path)
        if payload.get("type") != "event-observation":
            continue
        data = {key: value for key, value in payload.items() if key not in {"type", "okf_version"}}
        try:
            observation = EventObservation.model_validate(data)
        except ValueError:
            continue
        previous = latest.get(observation.event_id)
        if previous is None or observation.observed_at > previous.observed_at:
            latest[observation.event_id] = observation
    return sorted(latest.values(), key=lambda item: item.event_id)


def _json_line(key: str, value: object) -> str:
    return f"{key}: {json.dumps(value, ensure_ascii=False)}"


def materialize_reconciliations(
    reconciliations: Iterable[EventReconciliation], root: str | Path
) -> list[Path]:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for item in reconciliations:
        path = base / f"{item.reconciliation_id}.md"
        if path.exists():
            continue
        lines = [
            "---",
            'okf_version: "0.2"',
            'type: "event-reconciliation"',
            _json_line("reconciliation_id", item.reconciliation_id),
            _json_line("left_event_id", item.left_event_id),
            _json_line("right_event_id", item.right_event_id),
            _json_line("decision", item.decision),
            f"score: {item.score}",
            f"title_similarity: {item.title_similarity}",
            f"same_local_date: {'true' if item.same_local_date else 'false'}",
            f"venue_similarity: {item.venue_similarity}",
            f"organizer_similarity: {item.organizer_similarity}",
            _json_line("left_content_hash", item.left_content_hash),
            _json_line("right_content_hash", item.right_content_hash),
            _json_line("evaluated_at", item.evaluated_at.isoformat()),
            "---",
            "",
            f"# Reconciliação — {item.left_event_id} × {item.right_event_id}",
            "",
            "Evidência determinística de reconciliação entre identidades de fontes distintas.",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        created.append(path)
    return created


def _load_entities(root: Path) -> dict[str, dict[str, object]]:
    entities: dict[str, dict[str, object]] = {}
    if not root.exists():
        return entities
    for path in root.glob("*.md"):
        payload = _frontmatter(path)
        if payload.get("type") != "event-entity":
            continue
        canonical_id = payload.get("canonical_event_id")
        members = payload.get("member_event_ids")
        if isinstance(canonical_id, str) and isinstance(members, list):
            entities[canonical_id] = {
                "path": path,
                "members": {str(member) for member in members},
                "created_at": str(payload.get("created_at") or ""),
            }
    return entities


def _components(reconciliations: Iterable[EventReconciliation]) -> list[set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for item in reconciliations:
        if item.decision != "equivalent":
            continue
        adjacency[item.left_event_id].add(item.right_event_id)
        adjacency[item.right_event_id].add(item.left_event_id)

    components: list[set[str]] = []
    seen: set[str] = set()
    for start in sorted(adjacency):
        if start in seen:
            continue
        stack = [start]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.add(current)
            stack.extend(adjacency[current] - seen)
        if len(component) >= 2:
            components.append(component)
    return components


def _canonical_id(members: set[str]) -> str:
    raw = "|".join(sorted(members)).encode()
    return f"event-{hashlib.sha256(raw).hexdigest()[:12]}"


def materialize_entities(
    reconciliations: Iterable[EventReconciliation],
    root: str | Path,
    *,
    materialized_at: datetime | None = None,
) -> list[Path]:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    now = materialized_at or datetime.now(UTC)
    entities = _load_entities(base)
    member_to_entity = {
        member: canonical_id
        for canonical_id, data in entities.items()
        for member in data["members"]
        if isinstance(member, str)
    }
    changed: list[Path] = []

    for component in _components(reconciliations):
        existing_ids = {
            member_to_entity[member] for member in component if member in member_to_entity
        }
        if len(existing_ids) > 1:
            continue
        canonical_id = next(iter(existing_ids), _canonical_id(component))
        existing = entities.get(canonical_id)
        members = set(component)
        if existing:
            existing_members = existing["members"]
            if isinstance(existing_members, set):
                members |= {str(member) for member in existing_members}
            if members == existing_members:
                continue
            created_at = str(existing["created_at"])
            path = existing["path"]
            if not isinstance(path, Path):
                continue
        else:
            created_at = now.isoformat()
            path = base / f"{canonical_id}.md"

        lines = [
            "---",
            'okf_version: "0.2"',
            'type: "event-entity"',
            _json_line("canonical_event_id", canonical_id),
            "member_event_ids:",
            *[f"  - {json.dumps(member, ensure_ascii=False)}" for member in sorted(members)],
            _json_line("created_at", created_at),
            _json_line("updated_at", now.isoformat()),
            "---",
            "",
            f"# Evento consolidado — {canonical_id}",
            "",
            "Identidade canônica derivada de reconciliações equivalentes entre fontes públicas.",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        changed.append(path)
        entities[canonical_id] = {"path": path, "members": members, "created_at": created_at}
        for member in members:
            member_to_entity[member] = canonical_id

    return changed
