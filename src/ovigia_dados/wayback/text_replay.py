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


def _decode_text_payload(data: bytes, content_type: str) -> str | None:
    """Decode verified text payloads without turning arbitrary binary into text.

    UTF-8 remains the default. Some archived HTML pages are legacy-encoded even
    though Wayback reports only ``text/html``. For HTML-shaped payloads, accept
    Windows-1252 as the HTML-compatible legacy fallback. The structural guard
    keeps mislabeled binary resources raw and auditable instead of manufacturing
    a text projection from arbitrary bytes.
    """
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass

    if content_type.split(";", 1)[0].strip().lower() != "text/html":
        return None

    head = data[:4096].lstrip().lower()
    if not (
        head.startswith(b"<!doctype html")
        or head.startswith(b"<html")
        or b"<html" in head
        or b"<head" in head
        or b"<body" in head
    ):
        return None

    try:
        return data.decode("windows-1252")
    except UnicodeDecodeError:
        return None


def materialize_decoded_text_replays(bundle_root: Path) -> list[str]:
    """Write append-only decoded copies only for replay bytes verified as text.

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
        content_type = str(report.get("archive_content_type", ""))
        if not content_type.startswith("text/"):
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
        text = _decode_text_payload(decoded, content_type)
        if text is None:
            continue
        decoded_path.write_text(text, encoding="utf-8")
        written.append(decoded_path.relative_to(bundle_root).as_posix())

    return written
