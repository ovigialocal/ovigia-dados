"""Shared public surface for city-event collectors."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from ovigia_dados.events.sympla import (
    CdxSnapshot,
    event_content_hash,
    fetch_text,
    is_porto_velho,
    query_cdx,
)
from ovigia_dados.events.sympla import (
    EventObservation as _BaseEventObservation,
)


class EventObservation(_BaseEventObservation):
    """Source observation with explicit support for date-only schedules."""

    starts_on: date | None = None
    ends_on: date | None = None


def _latest_hashes(root: Path) -> dict[str, str]:
    latest: dict[str, tuple[str, str]] = {}
    paths = root.rglob("*.md") if root.exists() else []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        event = re.search(r'^event_id:\s*["\']?([^"\'\n]+)', text, re.M)
        digest = re.search(r'^content_hash:\s*["\']?([^"\'\n]+)', text, re.M)
        if (
            event
            and digest
            and (event.group(1) not in latest or path.name > latest[event.group(1)][0])
        ):
            latest[event.group(1)] = (path.name, digest.group(1))
    return {key: value[1] for key, value in latest.items()}


def _line(key: str, value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        value = value.isoformat()
    return f"{key}: {json.dumps(str(value), ensure_ascii=False)}"


def materialize_observations(
    events: Iterable[_BaseEventObservation],
    *,
    identities_root: str | Path,
    observations_root: str | Path,
) -> list[Path]:
    """Persist source identities and append-only observations.

    This mirrors the original Sympla materializer while adding optional `starts_on` and
    `ends_on` fields. Existing collectors remain wire-compatible.
    """

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
            identity.write_text("\n".join(line for line in lines if line), encoding="utf-8")
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
            ("starts_on", getattr(event, "starts_on", None)),
            ("ends_on", getattr(event, "ends_on", None)),
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


__all__ = [
    "CdxSnapshot",
    "EventObservation",
    "event_content_hash",
    "fetch_text",
    "is_porto_velho",
    "materialize_observations",
    "query_cdx",
]
