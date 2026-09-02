from __future__ import annotations

from pathlib import Path

import pytest

from ovigia_dados.wayback.queue import WaybackQueueError, load_wayback_queue


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_unrelated_non_okf_markdown_does_not_invalidate_queue(tmp_path: Path) -> None:
    _write(tmp_path, "README.md", "# ordinary repository documentation\n")
    _write(
        tmp_path,
        "knowledge/wayback/requests/example.md",
        "---\n"
        "type: archive-request\n"
        "source_url: 'https://example.com/'\n"
        "requested_at: '2026-09-02T12:00:00Z'\n"
        "resource_kind: webpage\n"
        "---\n",
    )

    queue = load_wayback_queue(tmp_path)

    assert [item.concept_id for item in queue.pending] == ["knowledge/wayback/requests/example"]


def test_parser_error_inside_wayback_namespace_fails_closed(tmp_path: Path) -> None:
    _write(tmp_path, "README.md", "# ordinary repository documentation\n")
    _write(
        tmp_path,
        "knowledge/wayback/requests/broken.md",
        "type: archive-request\nsource_url: https://example.com/\n",
    )

    with pytest.raises(WaybackQueueError, match="OKF001"):
        load_wayback_queue(tmp_path)
