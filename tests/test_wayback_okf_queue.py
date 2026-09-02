from __future__ import annotations

from pathlib import Path

import pytest

from ovigia_dados.wayback.queue import WaybackQueueError, load_wayback_queue


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _bundle(root: Path) -> None:
    _write(root, "index.md", "# test bundle\n")


def _request(root: Path, name: str = "example", url: str = "https://example.com/") -> str:
    concept_id = f"knowledge/wayback/requests/{name}"
    _write(
        root,
        f"{concept_id}.md",
        "---\n"
        "okf_version: '0.2'\n"
        "type: archive-request\n"
        f"source_url: '{url}'\n"
        "requested_at: '2026-09-02T12:00:00Z'\n"
        "resource_kind: webpage\n"
        "---\n",
    )
    return concept_id


def test_pending_identity_is_parser_owned_concept_id(tmp_path: Path) -> None:
    _bundle(tmp_path)
    request_id = _request(tmp_path)

    queue = load_wayback_queue(tmp_path)

    assert [item.concept_id for item in queue.pending] == [request_id]


def test_request_must_not_duplicate_its_own_identity(tmp_path: Path) -> None:
    _bundle(tmp_path)
    _write(
        tmp_path,
        "knowledge/wayback/requests/example.md",
        "---\n"
        "type: archive-request\n"
        "request_id: duplicate\n"
        "source_url: 'https://example.com/'\n"
        "requested_at: '2026-09-02T12:00:00Z'\n"
        "resource_kind: webpage\n"
        "---\n",
    )

    with pytest.raises(WaybackQueueError, match="request_id"):
        load_wayback_queue(tmp_path)


def test_result_mentions_request_concept_id_and_okf_relation(tmp_path: Path) -> None:
    _bundle(tmp_path)
    request_id = _request(tmp_path)
    _write(
        tmp_path,
        "knowledge/wayback/results/example.md",
        "---\n"
        "type: archive-result\n"
        f"request_concept_id: '{request_id}'\n"
        "source_url: 'https://example.com/'\n"
        "attempted_at: '2026-09-02T12:01:00Z'\n"
        "status: archived\n"
        "archive_url: 'https://web.archive.org/web/20260902120100/https://example.com/'\n"
        "sources:\n"
        f"  - resource: '{request_id}'\n"
        "---\n",
    )

    queue = load_wayback_queue(tmp_path)

    assert queue.pending == ()
    assert [item.request_concept_id for item in queue.archived] == [request_id]


def test_result_foreign_key_must_match_resolved_relation(tmp_path: Path) -> None:
    _bundle(tmp_path)
    request_id = _request(tmp_path)
    _write(
        tmp_path,
        "knowledge/wayback/results/example.md",
        "---\n"
        "type: archive-result\n"
        "request_concept_id: 'knowledge/wayback/requests/other'\n"
        "source_url: 'https://example.com/'\n"
        "attempted_at: '2026-09-02T12:01:00Z'\n"
        "status: archived\n"
        "archive_url: 'https://web.archive.org/web/20260902120100/https://example.com/'\n"
        "sources:\n"
        f"  - resource: '{request_id}'\n"
        "---\n",
    )

    with pytest.raises(WaybackQueueError, match="request_concept_id"):
        load_wayback_queue(tmp_path)


def test_infrastructure_result_is_not_terminal_archive_failure(tmp_path: Path) -> None:
    _bundle(tmp_path)
    request_id = _request(tmp_path)
    _write(
        tmp_path,
        "knowledge/wayback/results/example.md",
        "---\n"
        "type: archive-result\n"
        f"request_concept_id: '{request_id}'\n"
        "source_url: 'https://example.com/'\n"
        "attempted_at: '2026-09-02T12:01:00Z'\n"
        "status: infrastructure-error\n"
        "failure:\n"
        "  code: transport\n"
        "  detail: dns unavailable\n"
        "sources:\n"
        f"  - resource: '{request_id}'\n"
        "---\n",
    )

    with pytest.raises(WaybackQueueError, match="archived or failed"):
        load_wayback_queue(tmp_path)


def test_failed_result_requires_failure_and_never_archive_url(tmp_path: Path) -> None:
    _bundle(tmp_path)
    request_id = _request(tmp_path)
    _write(
        tmp_path,
        "knowledge/wayback/results/example.md",
        "---\n"
        "type: archive-result\n"
        f"request_concept_id: '{request_id}'\n"
        "source_url: 'https://example.com/'\n"
        "attempted_at: '2026-09-02T12:01:00Z'\n"
        "status: failed\n"
        "archive_url: 'https://web.archive.org/web/20260902120100/https://example.com/'\n"
        "sources:\n"
        f"  - resource: '{request_id}'\n"
        "---\n",
    )

    with pytest.raises(WaybackQueueError, match="failed result"):
        load_wayback_queue(tmp_path)
