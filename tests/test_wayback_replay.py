from __future__ import annotations

import json
from pathlib import Path

from ovigia_dados.wayback.replay import (
    FetchEvidence,
    materialize_replay_evidence,
    select_replay_result_paths,
)


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _archived_bundle(
    root: Path,
    *,
    source_url: str = "https://example.com/page",
    stem: str = "example",
    capture_timestamp: str = "20260902220100",
) -> str:
    _write(root, "index.md", "# bundle\n")
    request_id = f"knowledge/wayback/requests/{stem}"
    result_id = f"knowledge/wayback/results/{stem}"
    _write(
        root,
        f"{request_id}.md",
        "---\n"
        "type: archive-request\n"
        f"source_url: '{source_url}'\n"
        "requested_at: '2026-09-02T22:00:00Z'\n"
        "resource_kind: webpage\n"
        "---\n",
    )
    _write(
        root,
        f"{result_id}.md",
        "---\n"
        "type: archive-result\n"
        f"request_concept_id: '{request_id}'\n"
        f"source_url: '{source_url}'\n"
        "attempted_at: '2026-09-02T22:01:00Z'\n"
        "status: archived\n"
        f"archive_url: 'https://web.archive.org/web/{capture_timestamp}/{source_url}'\n"
        "sources:\n"
        f"  - resource: '{request_id}'\n"
        "---\n",
    )
    return f"{result_id}.md"


def test_replay_evidence_persists_html_and_exact_digest_comparison(tmp_path: Path) -> None:
    result_path = _archived_bundle(tmp_path)
    calls: list[str] = []
    body = b"<html><body>material evidence</body></html>"

    def fetch(url: str, *, keep_text_body: bool = False) -> FetchEvidence:
        calls.append(url)
        return FetchEvidence(
            url=url,
            content_type="text/html",
            size=len(body),
            sha256="same-digest",
            body=body if keep_text_body else None,
        )

    written = materialize_replay_evidence(tmp_path, fetch=fetch, result_paths={result_path})

    assert "raw/wayback/replays/example.html" in written
    assert "raw/wayback/replays/example.json" in written
    assert calls[0].startswith("https://web.archive.org/web/20260902220100id_/")
    report = json.loads((tmp_path / "raw/wayback/replays/example.json").read_text())
    assert report["byte_identical_to_source"] is True
    assert report["replay_body_path"] == "raw/wayback/replays/example.html"
    assert (tmp_path / report["replay_body_path"]).read_bytes() == body


def test_pdf_replay_persists_bounded_exact_body(tmp_path: Path) -> None:
    result_path = _archived_bundle(
        tmp_path,
        source_url="https://example.com/document.pdf",
    )
    body = b"%PDF-exact-replay"

    def fetch(url: str, *, keep_text_body: bool = False) -> FetchEvidence:
        return FetchEvidence(
            url=url,
            content_type="application/pdf",
            size=len(body),
            sha256="pdf-digest",
            body=body if keep_text_body else None,
        )

    written = materialize_replay_evidence(tmp_path, fetch=fetch, result_paths={result_path})
    report = json.loads((tmp_path / "raw/wayback/replays/example.json").read_text())

    assert written == [
        "raw/wayback/replays/example.pdf",
        "raw/wayback/replays/example.json",
    ]
    assert report["archive_content_type"] == "application/pdf"
    assert report["byte_identical_to_source"] is True
    assert report["replay_body_path"] == "raw/wayback/replays/example.pdf"
    assert (tmp_path / report["replay_body_path"]).read_bytes() == body


def test_existing_replay_report_can_backfill_matching_pdf_without_rewrite(tmp_path: Path) -> None:
    result_path = _archived_bundle(tmp_path, source_url="https://example.com/document.pdf")
    report_path = tmp_path / "raw/wayback/replays/example.json"
    report = {
        "archive_content_type": "application/pdf",
        "archive_sha256": "pdf-digest",
    }
    _write(tmp_path, "raw/wayback/replays/example.json", json.dumps(report) + "\n")
    original_report = report_path.read_bytes()
    body = b"%PDF-exact-replay"

    def fetch(url: str, *, keep_text_body: bool = False) -> FetchEvidence:
        return FetchEvidence(
            url=url,
            content_type="application/pdf",
            size=len(body),
            sha256="pdf-digest",
            body=body if keep_text_body else None,
        )

    written = materialize_replay_evidence(tmp_path, fetch=fetch, result_paths={result_path})

    assert written == ["raw/wayback/replays/example.pdf"]
    assert report_path.read_bytes() == original_report
    assert (tmp_path / "raw/wayback/replays/example.pdf").read_bytes() == body


def test_existing_replay_report_rejects_body_with_different_digest(tmp_path: Path) -> None:
    result_path = _archived_bundle(tmp_path, source_url="https://example.com/document.pdf")
    _write(
        tmp_path,
        "raw/wayback/replays/example.json",
        json.dumps(
            {
                "archive_content_type": "application/pdf",
                "archive_sha256": "expected-digest",
            }
        )
        + "\n",
    )

    def fetch(url: str, *, keep_text_body: bool = False) -> FetchEvidence:
        return FetchEvidence(
            url=url,
            content_type="application/pdf",
            size=4,
            sha256="different-digest",
            body=b"%PDF" if keep_text_body else None,
        )

    assert materialize_replay_evidence(tmp_path, fetch=fetch, result_paths={result_path}) == []
    assert not (tmp_path / "raw/wayback/replays/example.pdf").exists()


def test_existing_unknown_replay_report_is_append_only_and_not_refetched(tmp_path: Path) -> None:
    result_path = _archived_bundle(tmp_path)
    _write(tmp_path, "raw/wayback/replays/example.json", "{}\n")

    def should_not_fetch(_url: str, *, keep_text_body: bool = False) -> FetchEvidence:
        raise AssertionError("existing replay evidence must not be rewritten")

    assert (
        materialize_replay_evidence(tmp_path, fetch=should_not_fetch, result_paths={result_path})
        == []
    )


def test_replay_selection_prioritizes_new_results_and_bounds_backfill(tmp_path: Path) -> None:
    fresh = _archived_bundle(
        tmp_path,
        stem="fresh",
        source_url="https://example.com/fresh",
        capture_timestamp="20260902220300",
    )
    old_a = _archived_bundle(
        tmp_path,
        stem="old-a",
        source_url="https://example.com/old-a",
        capture_timestamp="20260902220200",
    )
    _archived_bundle(
        tmp_path,
        stem="old-b",
        source_url="https://example.com/old-b",
        capture_timestamp="20260902220100",
    )

    selected = select_replay_result_paths(
        tmp_path,
        preferred_paths=[fresh],
        backfill_limit=1,
    )

    assert fresh in selected
    assert old_a in selected
    assert len(selected) == 2


def test_replay_backfill_prefers_most_recent_incomplete_capture(tmp_path: Path) -> None:
    older = _archived_bundle(
        tmp_path,
        stem="aaa-older",
        source_url="https://example.com/older",
        capture_timestamp="20260902220100",
    )
    newest = _archived_bundle(
        tmp_path,
        stem="zzz-newest",
        source_url="https://example.com/newest",
        capture_timestamp="20260902220500",
    )

    selected = select_replay_result_paths(tmp_path, backfill_limit=1)

    assert selected == {newest}
    assert older not in selected


def test_replay_selection_skips_archived_result_with_complete_evidence(tmp_path: Path) -> None:
    complete = _archived_bundle(tmp_path, stem="complete")
    waiting = _archived_bundle(tmp_path, stem="waiting", source_url="https://example.com/waiting")
    _write(
        tmp_path,
        "raw/wayback/replays/complete.json",
        json.dumps({"archive_content_type": "text/html"}) + "\n",
    )
    _write(tmp_path, "raw/wayback/replays/complete.html", "complete")

    selected = select_replay_result_paths(tmp_path, backfill_limit=1)

    assert complete not in selected
    assert selected == {waiting}
