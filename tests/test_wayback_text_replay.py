from __future__ import annotations

import gzip
import json
from pathlib import Path

from ovigia_dados.wayback.text_replay import decode_text_transport, materialize_decoded_text_replays


def _write(root: Path, relative: str, data: bytes | str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


def test_decode_text_transport_unwraps_gzip_and_preserves_plain() -> None:
    html = b"<html><body>evidence</body></html>"
    assert decode_text_transport(gzip.compress(html)) == html
    assert decode_text_transport(html) == html


def test_materialize_decoded_html_keeps_raw_append_only(tmp_path: Path) -> None:
    raw = gzip.compress(b"<html><body>archived</body></html>")
    _write(tmp_path, "raw/wayback/replays/example.html", raw)
    _write(
        tmp_path,
        "raw/wayback/replays/example.json",
        json.dumps(
            {
                "archive_content_type": "text/html",
                "replay_body_path": "raw/wayback/replays/example.html",
            }
        )
        + "\n",
    )

    written = materialize_decoded_text_replays(tmp_path)

    assert written == ["raw/wayback/replays/example.decoded.html"]
    assert (tmp_path / "raw/wayback/replays/example.html").read_bytes() == raw
    assert (tmp_path / written[0]).read_text() == "<html><body>archived</body></html>"


def test_existing_decoded_copy_is_not_rewritten(tmp_path: Path) -> None:
    _write(tmp_path, "raw/wayback/replays/example.html", b"<html>raw</html>")
    _write(tmp_path, "raw/wayback/replays/example.decoded.html", "existing")
    _write(
        tmp_path,
        "raw/wayback/replays/example.json",
        json.dumps(
            {
                "archive_content_type": "text/html",
                "replay_body_path": "raw/wayback/replays/example.html",
            }
        )
        + "\n",
    )

    assert materialize_decoded_text_replays(tmp_path) == []
    assert (tmp_path / "raw/wayback/replays/example.decoded.html").read_text() == "existing"
