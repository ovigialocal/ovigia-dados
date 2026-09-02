"""Drain public OKF Wayback requests into terminal archive-result concepts."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ovigia_dados.wayback.queue import ArchiveRequest, load_wayback_queue
from ovigia_dados.wayback.save import WaybackSaveResult, save_to_wayback


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _result_path(request: ArchiveRequest) -> str:
    marker = "/requests/"
    if marker not in request.path or not request.path.endswith(".md"):
        msg = f"archive-request must live below a requests directory: {request.path}"
        raise ValueError(msg)
    return request.path.replace(marker, "/results/", 1)


def _failure_code(result: WaybackSaveResult) -> str:
    if result.http_status is not None:
        return f"http-{result.http_status}"
    return result.status.replace("_", "-")


def _render_result(request: ArchiveRequest, result: WaybackSaveResult) -> str | None:
    if result.status == "infrastructure_error":
        return None
    if result.timestamp is None:
        raise ValueError("terminal Wayback result requires timestamp")

    lines = [
        "---",
        "okf_version: '0.2'",
        "type: archive-result",
        f"request_concept_id: {_quote(request.concept_id)}",
        f"source_url: {_quote(request.source_url)}",
        f"attempted_at: {_quote(result.timestamp)}",
    ]

    if result.status == "verified":
        if result.archive_url is None:
            raise ValueError("verified Wayback result requires archive_url")
        lines.extend(
            [
                "status: archived",
                f"archive_url: {_quote(result.archive_url)}",
            ]
        )
    elif result.archive_failure and result.reached_archive:
        lines.extend(
            [
                "status: failed",
                "failure:",
                f"  code: {_quote(_failure_code(result))}",
                f"  detail: {_quote(result.error_message or 'Wayback preservation failed')}",
            ]
        )
    else:
        return None

    lines.extend(
        [
            "sources:",
            f"  - resource: {_quote(request.concept_id)}",
            "---",
            "",
            "Wayback preservation result.",
            "",
        ]
    )
    return "\n".join(lines)


def drain_wayback_queue(
    bundle_root: Path,
    *,
    save: Callable[[str], WaybackSaveResult] = save_to_wayback,
) -> list[str]:
    """Attempt every pending request and persist only terminal service outcomes."""
    queue = load_wayback_queue(bundle_root)
    written: list[str] = []
    for request in queue.pending:
        result = save(request.source_url)
        rendered = _render_result(request, result)
        if rendered is None:
            continue
        relative = _result_path(request)
        path = bundle_root / relative
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        written.append(relative)
    return written
