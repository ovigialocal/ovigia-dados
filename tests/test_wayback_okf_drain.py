from __future__ import annotations

from pathlib import Path

from ovigia_dados.wayback.drain import drain_wayback_queue
from ovigia_dados.wayback.save import WaybackSaveResult


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _request(root: Path) -> str:
    _write(root, "index.md", "# bundle\n")
    concept_id = "knowledge/wayback/requests/example"
    _write(
        root,
        f"{concept_id}.md",
        "---\n"
        "type: archive-request\n"
        "source_url: 'https://example.com/'\n"
        "requested_at: '2026-09-02T12:00:00Z'\n"
        "resource_kind: webpage\n"
        "---\n",
    )
    return concept_id


def test_verified_save_writes_archive_result_with_request_concept_id(tmp_path: Path) -> None:
    request_id = _request(tmp_path)

    def save(_url: str) -> WaybackSaveResult:
        return WaybackSaveResult(
            url="https://example.com/",
            status="verified",
            archive_url="https://web.archive.org/web/20260902120100/https://example.com/",
            timestamp="2026-09-02T12:01:00Z",
            attempted=True,
            reached_archive=True,
        )

    written = drain_wayback_queue(tmp_path, save=save)

    assert written == ["knowledge/wayback/results/example.md"]
    text = (tmp_path / written[0]).read_text(encoding="utf-8")
    assert f"request_concept_id: '{request_id}'" in text
    assert f"- resource: '{request_id}'" in text
    assert "status: archived" in text


def test_real_archive_refusal_writes_failed_result(tmp_path: Path) -> None:
    _request(tmp_path)

    def save(_url: str) -> WaybackSaveResult:
        return WaybackSaveResult(
            url="https://example.com/",
            status="terminal_failure",
            http_status=403,
            error_message="Save Page Now returned HTTP 403",
            timestamp="2026-09-02T12:01:00Z",
            attempted=True,
            reached_archive=True,
            archive_failure=True,
        )

    written = drain_wayback_queue(tmp_path, save=save)
    text = (tmp_path / written[0]).read_text(encoding="utf-8")

    assert "status: failed" in text
    assert "code: 'http-403'" in text
    assert "archive_url:" not in text


def test_infrastructure_error_leaves_request_pending_and_writes_no_result(tmp_path: Path) -> None:
    _request(tmp_path)

    def save(_url: str) -> WaybackSaveResult:
        return WaybackSaveResult(
            url="https://example.com/",
            status="infrastructure_error",
            error_message="dns failure",
            timestamp="2026-09-02T12:01:00Z",
            attempted=True,
            reached_archive=False,
            archive_failure=False,
        )

    written = drain_wayback_queue(tmp_path, save=save)

    assert written == []
    assert not (tmp_path / "knowledge/wayback/results/example.md").exists()


def test_terminal_request_is_idempotently_skipped(tmp_path: Path) -> None:
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

    def should_not_run(_url: str) -> WaybackSaveResult:
        raise AssertionError("terminal request must not be retried")

    assert drain_wayback_queue(tmp_path, save=should_not_run) == []
