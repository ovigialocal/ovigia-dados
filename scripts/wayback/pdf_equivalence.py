# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pypdf==6.16.2",
#     "ovigia-dados",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
import gzip
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from ovigia_dados.wayback.pdf_equivalence import ExtractedPdfText, materialize_pdf_text_equivalence


def _decode_pdf_transport(data: bytes) -> bytes:
    """Decode HTTP content-coding retained verbatim in replay evidence."""
    if data.startswith(b"\x1f\x8b"):
        return gzip.decompress(data)
    return data


def extract_pdf_text(data: bytes) -> ExtractedPdfText:
    reader = PdfReader(BytesIO(_decode_pdf_transport(data)))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return ExtractedPdfText(page_count=len(reader.pages), text=text)


def main() -> None:
    for path in materialize_pdf_text_equivalence(Path.cwd(), extract_pdf_text=extract_pdf_text):
        print(path)


if __name__ == "__main__":
    main()
