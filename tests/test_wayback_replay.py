from __future__ import annotations

import json
from pathlib import Path

from ovigia_dados.wayback.replay import FetchEvidence, materialize_replay_evidence


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _archived_bundle(root: Path, *, source_url: str = "https://example.com/page") -> str:
    _write(root, "index.md", "# bundle\n")
    request_id = "knowledge/wayback/requests/example"
    result_id = "knowledge/wayback/results/example"
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
        "archive_url: 'https://web.archive.org/web/20260902220100/https://example.com/page'\n"
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


def test_binary_replay_records_digest_without_committing_body(tmp_path: Path) -> None:
    result_path = _archived_bundle(
        tmp_path,
        source_url="https://example.com/document.pdf",
    )

    def fetch(url: str, *, keep_text_body: bool = False) -> FetchEvidence:
        return FetchEvidence(
            url=url,
            content_type="application/pdf",
            size=1234,
            sha256="pdf-digest",
            body=b"%PDF" if keep_text_body else None,
        )

    written = materialize_replay_evidence(tmp_path, fetch=fetch, result_paths={result_path})
    report = json.loads((tmp_path / "raw/wayback/replays/example.json").read_text())

    assert written == ["raw/wayback/replays/example.json"]
    assert report["archive_content_type"] == "application/pdf"
    assert report["byte_identical_to_source"] is True
    assert report["replay_body_path"] is None


def test_existing_replay_report_is_append_only_and_not_refetched(tmp_path: Path) -> None:
    result_path = _archived_bundle(tmp_path)
    _write(tmp_path, "raw/wayback/replays/example.json", "{}\n")

    def should_not_fetch(_url: str, *, keep_text_body: bool = False) -> FetchEvidence:
        raise AssertionError("existing replay evidence must not be rewritten")

    assert materialize_replay_evidence(tmp_path, fetch=should_not_fetch, result_paths={result_path}) == []
