#!/usr/bin/env python3
"""Varre contratos PMPV e sinaliza razões monetárias por potências de dez."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from ovigia_dados.connectors.porto_velho import PMPV_API_BASE_URL, PortoVelhoApiClient
from ovigia_dados.detectors.pmpv_monetary_ratio import detect_contract_licitation_ratios


def _probe_licitation(client: PortoVelhoApiClient, processo: str) -> dict[str, Any]:
    """Consulta uma licitação específica antes da varredura global suscetível a rate limit."""
    return {
        "licitation_source_url": f"{PMPV_API_BASE_URL}/licitacoes",
        "licitation_process_filter": processo,
        "licitation_probe": client.list_licitations(
            por_pagina=100,
            filters={"processo": processo},
        ),
    }


def scan_contract_ratios(
    client: PortoVelhoApiClient,
    *,
    por_pagina: int = 100,
) -> dict[str, Any]:
    """Executa a varredura paginada de contratos e detecta sinais de escala."""
    records: list[dict[str, Any]] = []
    pages_scanned = 0
    last_meta: Any = None

    for payload in client.iter_contract_pages(por_pagina=por_pagina):
        pages_scanned += 1
        data = payload.get("data")
        if not isinstance(data, list):
            raise ValueError("PMPV /contratos response data must be a list")
        records.extend(record for record in data if isinstance(record, dict))
        last_meta = payload.get("meta")

    signals = detect_contract_licitation_ratios(records)
    return {
        "status": "completed",
        "observed_at": datetime.now(UTC).isoformat(),
        "contracts_source_url": f"{PMPV_API_BASE_URL}/contratos",
        "pages_scanned": pages_scanned,
        "contracts_scanned": len(records),
        "last_meta": last_meta,
        "signals": [asdict(signal) for signal in signals],
    }


def _request_error_result(*, target: str, exc: requests.RequestException) -> dict[str, Any]:
    response = getattr(exc, "response", None)
    if response is not None and response.status_code == 429:
        code = "http-429"
        detail = "PMPV API returned HTTP 429 Too Many Requests"
    else:
        code = "request-error"
        detail = f"PMPV API request failed before a usable response: {exc}"

    return {
        "status": "blocked_external",
        "observed_at": datetime.now(UTC).isoformat(),
        "contracts_source_url": f"{PMPV_API_BASE_URL}/contratos",
        "failure": {
            "code": code,
            "target": target,
            "detail": detail,
        },
    }


def run_scan(
    client: PortoVelhoApiClient,
    *,
    por_pagina: int = 100,
    processo_licitacao: str | None = None,
) -> dict[str, Any]:
    """Executa probe específica primeiro e preserva-a se a varredura global ficar indisponível."""
    probe: dict[str, Any] = {}
    if processo_licitacao:
        try:
            probe = _probe_licitation(client, processo_licitacao)
        except requests.RequestException as exc:
            result = _request_error_result(target="licitations", exc=exc)
            result["licitation_source_url"] = f"{PMPV_API_BASE_URL}/licitacoes"
            result["licitation_process_filter"] = processo_licitacao
            return result

    try:
        result = scan_contract_ratios(client, por_pagina=por_pagina)
    except requests.RequestException as exc:
        result = _request_error_result(target="contracts", exc=exc)

    result.update(probe)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--por-pagina", type=int, default=100)
    parser.add_argument("--processo-licitacao")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = run_scan(
        PortoVelhoApiClient(),
        por_pagina=args.por_pagina,
        processo_licitacao=args.processo_licitacao,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
