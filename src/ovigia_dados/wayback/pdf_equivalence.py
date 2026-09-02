"""Text-level equivalence evidence for bounded Wayback PDF replays."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExtractedPdfText:
    page_count: int
    text: str


@dataclass(frozen=True, slots=True)
class PdfTextEquivalence:
    source_url: str
    archive_url: str
    archive_pdf_path: str
    archive_page_count: int
    archive_text_sha256: str
    source_page_count: int | None
    source_text_sha256: str | None
    text_identical_to_source: bool | None
    archive_text_path: str


def normalize_pdf_text(text: str) -> str:
    """Normalize layout-only whitespace while preserving textual content and order."""
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip()).strip() + "\n"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fetch_bytes(url: str, *, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "O Vigia/1.0 (+https://ovigia.local)"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def materialize_pdf_text_equivalence(
    bundle_root: Path,
    *,
    extract_pdf_text: Callable[[bytes], ExtractedPdfText],
    fetch_bytes: Callable[[str], bytes] = _fetch_bytes,
) -> list[str]:
    """Persist normalized archive PDF text and compare it with the current public source.

    This is supplemental evidence only. A true textual match can support material-equivalence review;
    a mismatch or unavailable live source must remain explicit and never becomes automatic approval.
    Existing sidecars are append-only.
    """
    evidence_dir = bundle_root / "raw/wayback/replays"
    written: list[str] = []

    for report_path in sorted(evidence_dir.glob("*.json")):
        if report_path.name.endswith(".pdf-text.json"):
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("archive_content_type") != "application/pdf":
            continue

        stem = report_path.stem
        pdf_path = evidence_dir / f"{stem}.pdf"
        sidecar_path = evidence_dir / f"{stem}.pdf-text.json"
        archive_text_path = evidence_dir / f"{stem}.pdf-text.txt"
        if sidecar_path.exists() or not pdf_path.exists():
            continue

        archive_extracted = extract_pdf_text(pdf_path.read_bytes())
        archive_text = normalize_pdf_text(archive_extracted.text)
        archive_text_path.write_text(archive_text, encoding="utf-8")
        written.append(archive_text_path.relative_to(bundle_root).as_posix())

        source_extracted: ExtractedPdfText | None = None
        try:
            source_bytes = fetch_bytes(str(report["source_url"]))
            source_extracted = extract_pdf_text(source_bytes)
        except OSError:
            source_extracted = None

        source_text = normalize_pdf_text(source_extracted.text) if source_extracted else None
        evidence = PdfTextEquivalence(
            source_url=str(report["source_url"]),
            archive_url=str(report["archive_url"]),
            archive_pdf_path=pdf_path.relative_to(bundle_root).as_posix(),
            archive_page_count=archive_extracted.page_count,
            archive_text_sha256=_sha256_text(archive_text),
            source_page_count=source_extracted.page_count if source_extracted else None,
            source_text_sha256=_sha256_text(source_text) if source_text is not None else None,
            text_identical_to_source=(archive_text == source_text) if source_text is not None else None,
            archive_text_path=archive_text_path.relative_to(bundle_root).as_posix(),
        )
        sidecar_path.write_text(
            json.dumps(asdict(evidence), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(sidecar_path.relative_to(bundle_root).as_posix())

    return written
