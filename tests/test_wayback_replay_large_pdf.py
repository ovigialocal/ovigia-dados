from __future__ import annotations

from dataclasses import dataclass

from ovigia_dados.wayback import replay


@dataclass
class _Headers:
    def get_content_type(self) -> str:
        return "application/pdf"


class _Response:
    def __init__(self, body: bytes) -> None:
        self.headers = _Headers()
        self._body = body
        self._offset = 0

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        chunk = self._body[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def test_fetch_retains_six_mib_pdf_for_editorial_replay(monkeypatch) -> None:
    body = b"%PDF" + (b"x" * (6 * 1024 * 1024))

    monkeypatch.setattr(
        replay.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(body),
    )

    evidence = replay._fetch("https://example.com/document.pdf", keep_text_body=True)

    assert evidence.content_type == "application/pdf"
    assert evidence.size == len(body)
    assert evidence.body == body
