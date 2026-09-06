"""Payloads brutos da API-Football versionados no repositório.

Time e competição são entidades estáveis: nome, fundação, estádio e cidade
não mudam de um dia para o outro. Pagá-los todo dia é gastar cota para
reconfirmar constante.

O payload fica em `raw/`, versionado, e não em cache de runner. Cache de
Actions é evictável — sete dias sem uso e ele some, e o miss vira uma
requisição silenciosa contra a mesma cota que se queria proteger. Um arquivo
commitado é reproduzível fora do CI, aparece no diff quando a fonte muda e
serve de evidência de proveniência, que é o contrato dos outros datasets
deste repositório.

Transcrever esses campos para o frontmatter do registry seria pior que as
duas opções: o registry é autoria editorial, e misturar nele dado copiado da
fonte cria divergência silenciosa no dia em que a fonte mudar.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_RAW_ROOT = Path("raw/sports/api-football")


def cache_path(root: str | Path, endpoint: str, entity_id: int | str) -> Path:
    """Caminho determinístico do payload de uma entidade."""
    return Path(root) / endpoint / f"{entity_id}.json"


def read_cached(root: str | Path, endpoint: str, entity_id: int | str) -> dict[str, Any] | None:
    """Devolve o payload guardado, ou None quando não há.

    Ausência não é erro: é o primeiro run, ou uma entidade nova no registry.
    Quem chama decide buscar na API, e é essa decisão que gasta cota.
    """
    path = cache_path(root, endpoint, entity_id)
    if not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as damaged:
        # Arquivo corrompido vale menos que uma requisição: avisa e deixa
        # quem chama buscar de novo, em vez de derrubar a coleta inteira.
        logger.warning("Payload bruto ilegível em %s: %s", path, damaged)
        return None

    if not isinstance(payload, dict):
        logger.warning("Payload bruto em %s não é um objeto JSON.", path)
        return None

    return payload


def write_cached(
    root: str | Path, endpoint: str, entity_id: int | str, payload: dict[str, Any]
) -> Path:
    """Grava o payload como veio, sem normalizar.

    O valor do arquivo é ser a resposta da fonte: normalizar aqui apagaria
    justamente o que faz dele evidência.
    """
    path = cache_path(root, endpoint, entity_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
