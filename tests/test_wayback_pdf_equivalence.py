from __future__ import annotations

import gzip
import json
from pathlib import Path

from ovigia_dados.wayback.pdf_equivalence import (
    ExtractedPdfText,
    decode_pdf_transport,
    materialize_pdf_text_equivalence,
    normalize_pdf_text,
)


def _write(root: Path, relative: str, data: bytes | str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


def _pdf_report(root: Path) -> None:
    _write(root, "raw/wayback/replays/example.pdf", b"archive-pdf")
    _write(
        root,
        "raw/wayback/replays/example.json",
        json.dumps(
            {
                "source_url": "https://example.com/document.pdf",
                "archive_url": "https://web.archive.org/web/20260902/https://example.com/document.pdf",
                "archive_content_type": "application/pdf",
            }
        )
        + "\n",
    )


def test_normalize_pdf_text_ignores_layout_whitespace() -> None:
    assert normalize_pdf_text("A   B\n\n C\tD \n") == "A B\nC D\n"


def test_decode_pdf_transport_unwraps_gzip_and_preserves_plain_pdf() -> None:
    pdf = b"%PDF-1.7\nbody"
    assert decode_pdf_transport(gzip.compress(pdf)) == pdf
    assert decode_pdf_transport(pdf) == pdf


def test_pdf_text_equivalence_persists_archive_text_and_match(tmp_path: Path) -> None:
    _pdf_report(tmp_path)

    def extract(data: bytes) -> ExtractedPdfText:
        if data == b"archive-pdf":
            return ExtractedPdfText(page_count=2, text="A   B\nC")
        return ExtractedPdfText(page_count=2, text="A B\nC")

    written = materialize_pdf_text_equivalence(
        tmp_path,
        extract_pdf_text=extract,
        fetch_bytes=lambda _url: b"source-pdf",
    )

    assert written == [
        "raw/wayback/replays/example.pdf-text.txt",
        "raw/wayback/replays/example.pdf-text.json",
    ]
    sidecar = json.loads((tmp_path / "raw/wayback/replays/example.pdf-text.json").read_text())
    assert sidecar["archive_page_count"] == 2
    assert sidecar["source_page_count"] == 2
    assert sidecar["text_identical_to_source"] is True
    assert (tmp_path / sidecar["archive_text_path"]).read_text() == "A B\nC\n"


def test_pdf_text_equivalence_preserves_explicit_source_unavailability(tmp_path: Path) -> None:
    _pdf_report(tmp_path)

    def unavailable(_url: str) -> bytes:
        raise OSError("network unavailable")

    materialize_pdf_text_equivalence(
        tmp_path,
        extract_pdf_text=lambda _data: ExtractedPdfText(page_count=1, text="Archive"),
        fetch_bytes=unavailable,
    )
    sidecar = json.loads((tmp_path / "raw/wayback/replays/example.pdf-text.json").read_text())
    assert sidecar["source_page_count"] is None
    assert sidecar["source_text_sha256"] is None
    assert sidecar["text_identical_to_source"] is None


def test_existing_pdf_text_sidecar_is_append_only(tmp_path: Path) -> None:
    _pdf_report(tmp_path)
    _write(tmp_path, "raw/wayback/replays/example.pdf-text.json", "{}\n")

    def should_not_extract(_data: bytes) -> ExtractedPdfText:
        raise AssertionError("existing sidecar must not be rewritten")

    assert materialize_pdf_text_equivalence(tmp_path, extract_pdf_text=should_not_extract) == []
