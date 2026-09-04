"""Materialize auditable evidence from concrete Wayback archive-result locators."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from ovigia_dados.wayback.queue import ArchiveResult, load_wayback_queue

# Government documents and public CSV extracts can exceed 16 MiB. Keep replay
# evidence bounded, but leave enough headroom for ordinary signed PDFs and
# monthly public-data files so provenance can inspect the exact archived bytes
# instead of getting stuck with locator/hash-only evidence.
_MAX_REPLAY_BODY_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class FetchEvidence:
    """Bounded replay/origin fetch used to support editorial verification."""

    url: str
    content_type: str
    size: int
    sha256: str
    body: bytes | None


@dataclass(frozen=True, slots=True)
class ReplayEvidence:
    """Public reproducible evidence for one archived result."""

    result_concept_id: str
    source_url: str
    archive_url: str
    verified_at: str
    archive_content_type: str
    archive_size: int
    archive_sha256: str
    source_content_type: str | None
    source_size: int | None
    source_sha256: str | None
    byte_identical_to_source: bool | None
    replay_body_path: str | None


def _identity_replay_url(archive_url: str) -> str:
    marker = "/web/"
    prefix, suffix = archive_url.split(marker, 1)
    timestamp, source = suffix.split("/", 1)
    if timestamp.endswith("id_"):
        return archive_url
    return f"{prefix}{marker}{timestamp}id_/{source}"


def _fetch(url: str, *, keep_text_body: bool = False, timeout: float = 60.0) -> FetchEvidence:
    request = urllib.request.Request(
        url, headers={"User-Agent": "O Vigia/1.0 (+https://ovigia.local)"}
    )
    digest = hashlib.sha256()
    body_parts: list[bytes] = []
    size = 0
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        content_type = response.headers.get_content_type()
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
            if keep_text_body and size <= _MAX_REPLAY_BODY_BYTES:
                body_parts.append(chunk)
    body = b"".join(body_parts) if keep_text_body and size <= _MAX_REPLAY_BODY_BYTES else None
    return FetchEvidence(
        url=url,
        content_type=content_type,
        size=size,
        sha256=digest.hexdigest(),
        body=body,
    )


def _evidence_stem(result: ArchiveResult) -> str:
    return Path(result.path).stem


def _body_suffix(content_type: str, source_url: str = "") -> str | None:
    source_path = urlparse(source_url).path.lower()
    if content_type in {"text/csv", "application/csv"} or (
        content_type == "application/octet-stream" and source_path.endswith(".csv")
    ):
        return ".csv"
    if content_type.startswith("text/"):
        return ".html"
    if content_type == "application/pdf":
        return ".pdf"
    return None


def _needs_replay_evidence(bundle_root: Path, result: ArchiveResult) -> bool:
    evidence_dir = bundle_root / "raw/wayback/replays"
    stem = _evidence_stem(result)
    report_path = evidence_dir / f"{stem}.json"
    if not report_path.exists():
        return True
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    suffix = _body_suffix(str(report.get("archive_content_type", "")), result.source_url)
    return suffix is not None and not (evidence_dir / f"{stem}{suffix}").exists()


def _replay_backfill_key(result: ArchiveResult) -> tuple[str, str]:
    """Sort incomplete replay evidence by newest Wayback capture first."""
    return (result.archive_url or "", result.path)


def select_replay_result_paths(
    bundle_root: Path,
    *,
    preferred_paths: Iterable[str] = (),
    backfill_limit: int = 1,
) -> set[str]:
    """Prioritize fresh terminal results while bounding historical replay retries.

    Fresh archived results should get replay evidence in the same worker that created them.
    Archived results whose replay fetch previously failed remain eligible. Backfill retries
    the most recent incomplete captures first, so a newly archived newsroom source does not
    fall behind an alphabetical historical tail after one transient replay failure.
    """
    if backfill_limit < 0:
        raise ValueError("backfill_limit must be non-negative")

    queue = load_wayback_queue(bundle_root)
    archived_by_path = {result.path: result for result in queue.archived}
    selected = {path for path in preferred_paths if path in archived_by_path}

    candidates = sorted(
        (
            result
            for result in queue.archived
            if result.path not in selected and _needs_replay_evidence(bundle_root, result)
        ),
        key=_replay_backfill_key,
        reverse=True,
    )
    selected.update(result.path for result in candidates[:backfill_limit])
    return selected


def _persist_replay_body(
    evidence_dir: Path,
    stem: str,
    replay: FetchEvidence,
    bundle_root: Path,
    *,
    source_url: str,
) -> str | None:
    if replay.body is None:
        return None
    suffix = _body_suffix(replay.content_type, source_url)
    if suffix is None:
        return None
    body_path = evidence_dir / f"{stem}{suffix}"
    if not body_path.exists():
        body_path.write_bytes(replay.body)
    return body_path.relative_to(bundle_root).as_posix()


def materialize_replay_evidence(
    bundle_root: Path,
    *,
    fetch: Callable[..., FetchEvidence] = _fetch,
    result_paths: set[str] | None = None,
) -> list[str]:
    """Fetch archived replay bytes and persist audit evidence for archived results.

    Bounded HTML/text, CSV and PDF replays are retained verbatim. Other binaries keep digest
    evidence only. Existing JSON reports remain append-only; a later run may backfill the exact
    bounded replay body only when its SHA-256 still matches the report already committed. A
    temporarily unreachable replay is skipped instead of poisoning another result or fabricating
    editorial equivalence.
    """
    queue = load_wayback_queue(bundle_root)
    written: list[str] = []
    evidence_dir = bundle_root / "raw/wayback/replays"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    for result in queue.archived:
        if result_paths is not None and result.path not in result_paths:
            continue
        if result.archive_url is None:
            continue
        stem = _evidence_stem(result)
        report_path = evidence_dir / f"{stem}.json"

        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            suffix = _body_suffix(str(report.get("archive_content_type", "")), result.source_url)
            if suffix is None or (evidence_dir / f"{stem}{suffix}").exists():
                continue
            try:
                replay = fetch(_identity_replay_url(result.archive_url), keep_text_body=True)
            except OSError:
                continue
            if replay.sha256 != report.get("archive_sha256"):
                continue
            body_relative = _persist_replay_body(
                evidence_dir,
                stem,
                replay,
                bundle_root,
                source_url=result.source_url,
            )
            if body_relative is not None:
                written.append(body_relative)
            continue

        try:
            replay = fetch(_identity_replay_url(result.archive_url), keep_text_body=True)
        except OSError:
            continue

        body_relative = _persist_replay_body(
            evidence_dir,
            stem,
            replay,
            bundle_root,
            source_url=result.source_url,
        )
        if body_relative is not None:
            written.append(body_relative)

        source: FetchEvidence | None
        try:
            source = fetch(result.source_url, keep_text_body=False)
        except OSError:
            source = None

        report = ReplayEvidence(
            result_concept_id=result.concept_id,
            source_url=result.source_url,
            archive_url=result.archive_url,
            verified_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            archive_content_type=replay.content_type,
            archive_size=replay.size,
            archive_sha256=replay.sha256,
            source_content_type=source.content_type if source else None,
            source_size=source.size if source else None,
            source_sha256=source.sha256 if source else None,
            byte_identical_to_source=(replay.sha256 == source.sha256) if source else None,
            replay_body_path=body_relative,
        )
        report_path.write_text(
            json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(report_path.relative_to(bundle_root).as_posix())

    return written
