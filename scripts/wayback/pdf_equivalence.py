# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pypdf==6.16.2",
#     "ovigia-dados",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from ovigia_dados.wayback.pdf_equivalence import ExtractedPdfText, materialize_pdf_text_equivalence


def extract_pdf_text(data: bytes) -> ExtractedPdfText:
    reader = PdfReader(BytesIO(data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return ExtractedPdfText(page_count=len(reader.pages), text=text)


def main() -> None:
    for path in materialize_pdf_text_equivalence(Path.cwd(), extract_pdf_text=extract_pdf_text):
        print(path)


if __name__ == "__main__":
    main()
