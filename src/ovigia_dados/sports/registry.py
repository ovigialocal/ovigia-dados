"""Load the authored sports monitoring registry from OKF Markdown concepts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from okf_parser.parser import parse_document


def _required(frontmatter: dict[str, Any], field: str, path: Path) -> str:
    value = frontmatter.get(field)
    if not isinstance(value, str) or not value.strip():
        msg = f"{path}: sports-monitor requires non-empty {field}"
        raise ValueError(msg)
    return value.strip()


def load_sports_registry(root: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Project sports-monitor concepts into the API-Football collector configuration."""
    registry_root = Path(root)
    regions: list[dict[str, Any]] = []
    leagues: list[dict[str, Any]] = []
    teams: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for path in sorted(registry_root.rglob("*.md")):
        document = parse_document(path)
        metadata = document.frontmatter
        if metadata.get("type") != "sports-monitor":
            continue

        entity_kind = _required(metadata, "entity_kind", path)
        external_id = _required(metadata, "external_id", path)
        identity = (entity_kind, external_id)
        if identity in seen:
            msg = f"duplicate sports-monitor identity: {entity_kind}:{external_id}"
            raise ValueError(msg)
        seen.add(identity)
        name = _required(metadata, "name", path)

        if entity_kind == "region":
            regions.append(
                {
                    "uf": _required(metadata, "uf", path),
                    "municipality_name": name,
                    "municipality_code": _required(metadata, "municipality_code", path),
                }
            )
        elif entity_kind == "competition":
            leagues.append(
                {
                    "league_id": int(external_id),
                    "name": name,
                    "priority": _required(metadata, "priority", path),
                }
            )
        elif entity_kind == "team":
            teams.append(
                {
                    "team_id": int(external_id),
                    "name": name,
                    "city": _required(metadata, "city", path),
                    "uf": _required(metadata, "uf", path),
                    "is_local_focus": metadata.get("is_local_focus", "false") == "true",
                }
            )
        else:
            msg = f"{path}: unsupported sports-monitor entity_kind {entity_kind!r}"
            raise ValueError(msg)

    if not regions or not leagues or not teams:
        msg = "sports registry must contain at least one region, competition and team"
        raise ValueError(msg)

    return {
        "monitored_regions": regions,
        "leagues": leagues,
        "teams": teams,
    }
