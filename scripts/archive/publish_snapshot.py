# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
#     "internetarchive>=4.0.0",
#     "ovigia-dados",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
"""Script CLI para publicação idempotente de snapshots no Internet Archive."""

import argparse
import json
import logging
from pathlib import Path

from ovigia_dados.archive.publisher import publish_snapshot_to_internet_archive
from ovigia_dados.schemas import SnapshotManifest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Publica snapshot no Internet Archive")
    parser.add_argument("--manifest", required=True, help="Caminho para manifest.json")
    parser.add_argument("--parquet", required=True, help="Caminho para arquivo Parquet")
    parser.add_argument("--dictionary", help="Caminho para dictionary.md")
    parser.add_argument("--catalog", help="Caminho para catalog.sql")
    parser.add_argument("--raw", help="Caminho para arquivo bruto (ZIP / CSV)")
    args = parser.parse_args()

    manifest_p = Path(args.manifest)
    manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest = SnapshotManifest(**manifest_data)

    item_id = f"ovigia-dados-{manifest.dataset_id}-{manifest.snapshot_id}"
    files = [Path(args.parquet), manifest_p]
    if args.dictionary and Path(args.dictionary).exists():
        files.append(Path(args.dictionary))
    if args.catalog and Path(args.catalog).exists():
        files.append(Path(args.catalog))
    if args.raw and Path(args.raw).exists():
        files.append(Path(args.raw))

    logger.info(f"Publicando item {item_id} com {len(files)} arquivos...")
    publish_snapshot_to_internet_archive(item_id, files, manifest)


if __name__ == "__main__":
    main()
