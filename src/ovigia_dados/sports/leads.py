"""Persist public sports detector signals as authored-looking OKF concepts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def _yaml_json(value: object) -> str:
    """Render JSON syntax, which is also valid YAML, without ambiguous scalars."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def signal_concept_path(output_root: Path, signal: dict[str, Any]) -> Path:
    snapshot = str(signal["source_snapshot"])
    signal_id = str(signal["signal_id"]).lower()
    safe_id = "".join(char if char.isalnum() or char in "-_" else "-" for char in signal_id)
    return output_root / snapshot / f"{safe_id}.md"


def render_signal_concept(signal: dict[str, Any]) -> str:
    detector_id = signal.get("detector_id") or signal.get("detector")
    fields = {
        "okf_version": "0.2",
        "type": "signal",
        "signal_id": str(signal["signal_id"]),
        "detector_id": str(detector_id),
        "domain": "sports",
        "observed_at": str(signal["observed_at"]),
        "entity_type": str(signal["entity_type"]),
        "entity_id": str(signal["entity_id"]),
        "league_id": str(signal["league_id"]),
        "season": str(signal["season"]),
        "reason_codes": list(signal.get("reason_codes", [])),
        "source_snapshot": str(signal["source_snapshot"]),
        "source_endpoint": str(signal.get("source_endpoint", "")),
        "metrics": signal.get("metrics", {}),
    }
    if signal.get("fixture_id") is not None:
        fields["fixture_id"] = str(signal["fixture_id"])

    frontmatter = "\n".join(f"{key}: {_yaml_json(value)}" for key, value in fields.items())
    title = f"Sinal esportivo {fields['signal_id']}"
    reasons = ", ".join(fields["reason_codes"])
    return (
        f"---\n{frontmatter}\n---\n\n"
        f"# {title}\n\n"
        f"Detector `{fields['detector_id']}` emitiu este sinal a partir do snapshot "
        f"`{fields['source_snapshot']}`. Reason codes: {reasons}.\n"
    )


def materialize_signal_concepts(
    signals: Iterable[dict[str, Any]], output_root: str | Path
) -> list[Path]:
    """Create new signal concepts; never rewrite a previously persisted observation."""
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for signal in signals:
        destination = signal_concept_path(root, signal)
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_signal_concept(signal), encoding="utf-8")
        created.append(destination)
    return created
