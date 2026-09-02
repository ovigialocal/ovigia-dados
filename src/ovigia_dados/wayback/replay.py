"""Materialize auditable evidence from concrete Wayback archive-result locators."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ovigia_dados.wayback.queue import ArchiveResult, load_wayback_queue

_MAX_TEXT_BYTES = 5 * 1024 * 1024


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
    request = urllib.request.Request(url, headers={"User-Agent": "O Vigia/1.0 (+https://ovigia.local)"})
    digest = hashlib.sha256()
    body_parts: list[bytes] = []
    size = 0
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        content_type = response.headers.get_content_type()
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
            if keep_text_body and size <= _MAX_TEXT_BYTES:
                body_parts.append(chunk)
    body = b"".join(body_parts) if keep_text_body and size <= _MAX_TEXT_BYTES else None
    return FetchEvidence(
        url=url,
        content_type=content_type,
        size=size,
        sha256=digest.hexdigest(),
        body=body,
    )


def _evidence_stem(result: ArchiveResult) -> str:
    return Path(result.path).stem


def materialize_replay_evidence(
    bundle_root: Path,
    *,
    fetch: Callable[..., FetchEvidence] = _fetch,
    result_paths: set[str] | None = None,
) -> list[str]:
    """Fetch archived replay bytes and persist audit evidence for archived results.

    HTML/text replays are retained verbatim when bounded. Binary resources are not duplicated in Git;
    their replay digest is compared with a fresh fetch of the canonical public source when possible.
    A replay that is temporarily unreachable remains without evidence instead of poisoning another
    archived result or fabricating editorial equivalence.
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
            continue

        try:
            replay = fetch(_identity_replay_url(result.archive_url), keep_text_body=True)
        except OSError:
            continue

        body_relative: str | None = None
        if replay.body is not None and replay.content_type.startswith("text/"):
            body_path = evidence_dir / f"{stem}.html"
            body_path.write_bytes(replay.body)
            body_relative = body_path.relative_to(bundle_root).as_posix()
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
