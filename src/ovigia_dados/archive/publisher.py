"""Publicador e validador de snapshots no Internet Archive."""

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from internetarchive import upload

from ovigia_dados.schemas import SnapshotManifest

logger = logging.getLogger(__name__)


def compute_sha256(file_path: Path) -> str:
    """Calcula hash SHA-256 de um arquivo local."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def publish_snapshot_to_internet_archive(
    item_id: str,
    files: list[Path],
    manifest: SnapshotManifest,
    metadata: dict[str, Any] | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
) -> bool:
    """Publica os artefatos de um snapshot no Internet Archive de forma idempotente."""
    ak = access_key or os.environ.get("IA_ACCESS_KEY")
    sk = secret_key or os.environ.get("IA_SECRET_KEY")

    if not ak or not sk:
        logger.warning(
            "Credenciais do Internet Archive (IA_ACCESS_KEY / IA_SECRET_KEY) não encontradas. Simulação de upload local."
        )
        return False

    item_meta = {
        "mediatype": "data",
        "creator": "O Vigia",
        "collection": "opensource_dataset",
        "description": f"Dataset público do O Vigia: {manifest.dataset_id} (competência {manifest.snapshot_id})",
        "subject": ["brazil", "open-data", "government-spending", manifest.dataset_id],
    }
    if metadata:
        item_meta.update(metadata)

    # Converte caminhos para strings
    file_paths_str = [str(p) for p in files]

    logger.info(f"Iniciando upload para item do Internet Archive: {item_id}")
    try:
        upload(
            identifier=item_id,
            files=file_paths_str,
            metadata=item_meta,
            access_key=ak,
            secret_key=sk,
            retries=5,
            verify=True,
            verbose=True,
        )
        logger.info(f"Upload concluído com sucesso para: https://archive.org/details/{item_id}")
        return True
    except Exception as e:
        logger.error(f"Falha no upload para o Internet Archive ({item_id}): {e}")
        raise
