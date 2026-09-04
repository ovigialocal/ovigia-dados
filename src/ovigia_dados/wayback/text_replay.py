"""Decode bounded text replay transport bytes into auditable text files."""

from __future__ import annotations

import gzip
import json
from pathlib import Path


def decode_text_transport(data: bytes) -> bytes:
    """Decode gzip content-coding while preserving already-decoded bytes."""
    if data.startswith(b"\x1f\x8b"):
        return gzip.decompress(data)
    return data


def materialize_decoded_text_replays(bundle_root: Path) -> list[str]:
    """Write append-only decoded copies only when replay bytes are valid UTF-8 text.

    The raw replay remains untouched and its digest remains authoritative. Wayback can
    report a text-like replay content type while returning a binary resource (for
    example an XLSX). Such evidence must remain raw instead of aborting the whole
    preservation transaction while trying to manufacture a text projection.
    """
    evidence_dir = bundle_root / "raw/wayback/replays"
    written: list[str] = []

    for report_path in sorted(evidence_dir.glob("*.json")):
        if report_path.name.endswith(".pdf-text.json"):
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not str(report.get("archive_content_type", "")).startswith("text/"):
            continue
        body_relative = report.get("replay_body_path")
        if not body_relative:
            continue
        raw_path = bundle_root / str(body_relative)
        if not raw_path.exists():
            continue
        decoded_path = raw_path.with_name(f"{raw_path.stem}.decoded{raw_path.suffix}")
        if decoded_path.exists():
            continue
        decoded = decode_text_transport(raw_path.read_bytes())
        try:
            decoded.decode("utf-8")
        except UnicodeDecodeError:
            continue
        decoded_path.write_bytes(decoded)
        written.append(decoded_path.relative_to(bundle_root).as_posix())

    return written
