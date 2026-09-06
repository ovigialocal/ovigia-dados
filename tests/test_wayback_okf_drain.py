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


def _legacy_failed_result(root: Path, request_id: str, code: str) -> None:
    _write(
        root,
        "knowledge/wayback/results/example.md",
        "---\n"
        "type: archive-result\n"
        f"request_concept_id: '{request_id}'\n"
        "source_url: 'https://example.com/'\n"
        "attempted_at: '2026-09-02T12:01:00Z'\n"
        "status: failed\n"
        "failure:\n"
        f"  code: '{code}'\n"
        "  detail: 'legacy transient response'\n"
        "sources:\n"
        f"  - resource: '{request_id}'\n"
        "---\n",
    )


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


def test_retryable_error_leaves_request_pending_and_writes_no_result(tmp_path: Path) -> None:
    _request(tmp_path)

    def save(_url: str) -> WaybackSaveResult:
        return WaybackSaveResult(
            url="https://example.com/",
            status="retryable_error",
            http_status=429,
            error_message="rate limited",
            timestamp="2026-09-02T12:01:00Z",
            attempted=True,
            reached_archive=True,
            archive_failure=False,
        )

    assert drain_wayback_queue(tmp_path, save=save) == []
    assert not (tmp_path / "knowledge/wayback/results/example.md").exists()


def test_legacy_429_result_is_requeued_and_replaced_by_archived_result(tmp_path: Path) -> None:
    request_id = _request(tmp_path)
    _legacy_failed_result(tmp_path, request_id, "http-429")

    def save(_url: str) -> WaybackSaveResult:
        return WaybackSaveResult(
            url="https://example.com/",
            status="verified",
            archive_url="https://web.archive.org/web/20260906150000/https://example.com/",
            timestamp="2026-09-06T15:00:00Z",
            attempted=True,
            reached_archive=True,
        )

    written = drain_wayback_queue(tmp_path, save=save)

    assert written == ["knowledge/wayback/results/example.md"]
    text = (tmp_path / written[0]).read_text(encoding="utf-8")
    assert "status: archived" in text
    assert "http-429" not in text


def test_legacy_503_result_is_requeued(tmp_path: Path) -> None:
    request_id = _request(tmp_path)
    _legacy_failed_result(tmp_path, request_id, "http-503")
    attempted: list[str] = []

    def save(url: str) -> WaybackSaveResult:
        attempted.append(url)
        return WaybackSaveResult(
            url=url,
            status="retryable_error",
            http_status=503,
            error_message="still unavailable",
            timestamp="2026-09-06T15:00:00Z",
            attempted=True,
            reached_archive=True,
            archive_failure=False,
        )

    assert drain_wayback_queue(tmp_path, save=save) == []
    assert attempted == ["https://example.com/"]
    assert "http-503" in (tmp_path / "knowledge/wayback/results/example.md").read_text(
        encoding="utf-8"
    )


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


def test_request_path_filter_attempts_only_selected_pending_request(tmp_path: Path) -> None:
    _request(tmp_path)
    second = "knowledge/wayback/requests/second"
    _write(
        tmp_path,
        f"{second}.md",
        "---\n"
        "type: archive-request\n"
        "source_url: 'https://example.org/'\n"
        "requested_at: '2026-09-02T12:02:00Z'\n"
        "resource_kind: webpage\n"
        "---\n",
    )
    attempted: list[str] = []

    def save(url: str) -> WaybackSaveResult:
        attempted.append(url)
        return WaybackSaveResult(
            url=url,
            status="infrastructure_error",
            error_message="local timeout",
            timestamp="2026-09-02T12:03:00Z",
            attempted=True,
            reached_archive=False,
            archive_failure=False,
        )

    written = drain_wayback_queue(
        tmp_path,
        save=save,
        request_paths={f"{second}.md"},
    )

    assert written == []
    assert attempted == ["https://example.org/"]
