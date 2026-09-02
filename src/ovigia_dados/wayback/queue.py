"""Wayback preservation queue derived from parser-owned OKF concepts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from okf_parser import concept, load_bundle, resolve_relations
from okf_parser.models import ConceptRecord

_WAYBACK_PREFIX = "knowledge/wayback/"


class WaybackQueueError(ValueError):
    """Raised when Wayback queue concepts violate the public data contract."""


@dataclass(frozen=True, slots=True)
class ArchiveRequest:
    """Validated pending or terminal preservation request."""

    concept_id: str
    path: str
    source_url: str
    requested_at: str
    resource_kind: str


@dataclass(frozen=True, slots=True)
class ArchiveResult:
    """Validated terminal preservation result."""

    concept_id: str
    path: str
    request_concept_id: str
    source_url: str
    status: str
    archive_url: str | None = None


@dataclass(frozen=True, slots=True)
class WaybackQueue:
    """Projection of requests minus terminal results."""

    pending: tuple[ArchiveRequest, ...]
    archived: tuple[ArchiveResult, ...]
    failed: tuple[ArchiveResult, ...]


def _required_text(meta: dict[str, Any], field: str, *, path: str) -> str:
    value = meta.get(field)
    if not isinstance(value, str) or not value.strip():
        raise WaybackQueueError(f"{path}: {field} must be non-empty text")
    return value.strip()


def _require_wayback_okf_conformance(bundle) -> None:
    violations = [
        item
        for item in bundle.validate()
        if item.path.startswith(_WAYBACK_PREFIX) and item.severity.value == "error"
    ]
    if not violations:
        return
    rendered = "; ".join(
        f"{item.code} {item.path}: {item.message}" for item in violations
    )
    raise WaybackQueueError(f"Wayback OKF namespace is not conformant: {rendered}")


def _request(record: ConceptRecord) -> ArchiveRequest:
    meta = record.frontmatter
    if "request_id" in meta:
        raise WaybackQueueError(
            f"{record.path}: request_id duplicates parser-owned concept identity"
        )
    resource_kind = _required_text(meta, "resource_kind", path=record.path)
    if resource_kind not in {"webpage", "pdf", "attachment", "document"}:
        raise WaybackQueueError(
            f"{record.path}: resource_kind must be webpage, pdf, attachment or document"
        )
    return ArchiveRequest(
        concept_id=record.concept_id,
        path=record.path,
        source_url=_required_text(meta, "source_url", path=record.path),
        requested_at=_required_text(meta, "requested_at", path=record.path),
        resource_kind=resource_kind,
    )


def _result(bundle, record: ConceptRecord, requests: dict[str, ArchiveRequest]) -> ArchiveResult:
    meta = record.frontmatter
    try:
        related = resolve_relations(bundle, record, target_type="archive-request")
    except (KeyError, TypeError, ValueError) as exc:
        raise WaybackQueueError(
            f"{record.path}: archive-result must reference exactly one existing archive-request"
        ) from exc
    if len(related) != 1:
        raise WaybackQueueError(
            f"{record.path}: archive-result must reference exactly one existing archive-request"
        )

    related_request = related[0]
    request_concept_id = _required_text(meta, "request_concept_id", path=record.path)
    if request_concept_id != related_request.concept_id:
        raise WaybackQueueError(
            f"{record.path}: request_concept_id must equal the resolved archive-request concept_id"
        )
    request = requests.get(request_concept_id)
    if request is None:
        raise WaybackQueueError(f"{record.path}: referenced archive-request is not in the queue")

    source_url = _required_text(meta, "source_url", path=record.path)
    if source_url != request.source_url:
        raise WaybackQueueError(
            f"{record.path}: source_url must equal the referenced archive-request source_url"
        )
    _required_text(meta, "attempted_at", path=record.path)
    status = _required_text(meta, "status", path=record.path)

    archive_url: str | None = None
    if status == "archived":
        archive_url = _required_text(meta, "archive_url", path=record.path)
        if not archive_url.startswith("https://web.archive.org/web/"):
            raise WaybackQueueError(
                f"{record.path}: archive_url must be a concrete Wayback snapshot"
            )
        if "failure" in meta:
            raise WaybackQueueError(f"{record.path}: archived result must not contain failure")
    elif status == "failed":
        if "archive_url" in meta:
            raise WaybackQueueError(f"{record.path}: failed result must not contain archive_url")
        failure = meta.get("failure")
        if not isinstance(failure, dict):
            raise WaybackQueueError(f"{record.path}: failed result requires failure mapping")
        _required_text(failure, "code", path=f"{record.path}: failure")
        _required_text(failure, "detail", path=f"{record.path}: failure")
    else:
        raise WaybackQueueError(f"{record.path}: status must be archived or failed")

    return ArchiveResult(
        concept_id=record.concept_id,
        path=record.path,
        request_concept_id=request_concept_id,
        source_url=source_url,
        status=status,
        archive_url=archive_url,
    )


def load_wayback_queue(bundle_root: Path) -> WaybackQueue:
    """Load and validate the public append-only Wayback queue."""
    bundle = load_bundle(bundle_root)
    _require_wayback_okf_conformance(bundle)
    requests: dict[str, ArchiveRequest] = {}
    result_records: list[ConceptRecord] = []

    for row in bundle.concepts.execute().to_dict(orient="records"):
        concept_type = row.get("concept_type")
        if concept_type not in {"archive-request", "archive-result"}:
            continue
        record = concept(bundle, str(row["path"]))
        if concept_type == "archive-request":
            request = _request(record)
            requests[request.concept_id] = request
        else:
            result_records.append(record)

    terminal: dict[str, ArchiveResult] = {}
    for record in result_records:
        result = _result(bundle, record, requests)
        if result.request_concept_id in terminal:
            raise WaybackQueueError(
                f"{record.path}: archive-request already has a terminal archive-result"
            )
        terminal[result.request_concept_id] = result

    pending = tuple(
        requests[concept_id] for concept_id in sorted(requests) if concept_id not in terminal
    )
    archived = tuple(
        terminal[concept_id]
        for concept_id in sorted(terminal)
        if terminal[concept_id].status == "archived"
    )
    failed = tuple(
        terminal[concept_id]
        for concept_id in sorted(terminal)
        if terminal[concept_id].status == "failed"
    )
    return WaybackQueue(pending=pending, archived=archived, failed=failed)
