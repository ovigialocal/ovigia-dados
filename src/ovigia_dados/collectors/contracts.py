"""Coletor e normalizador de compras e contratos públicos federais."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from ovigia_dados.schemas import ContractRecord

logger = logging.getLogger(__name__)

CONTRACTS_PYARROW_SCHEMA = pa.schema(
    [
        ("contract_id", pa.string()),
        ("source_system", pa.string()),
        ("source_url", pa.string()),
        ("contract_number", pa.string()),
        ("buyer_name", pa.string()),
        ("buyer_document", pa.string()),
        ("supplier_name", pa.string()),
        ("supplier_document", pa.string()),
        ("object", pa.string()),
        ("amount_initial", pa.float64()),
        ("amount_current", pa.float64()),
        ("signed_at", pa.date32()),
        ("starts_at", pa.date32()),
        ("ends_at", pa.date32()),
        ("municipality_code", pa.string()),
        ("municipality_name", pa.string()),
        ("uf", pa.string()),
        ("observed_at", pa.timestamp("us")),
        ("snapshot_id", pa.string()),
    ]
)


def normalize_pncp_contract(
    raw: dict[str, Any], snapshot_id: str, observed_at: datetime | None = None
) -> ContractRecord:
    """Normaliza um registro retornado pelo PNCP para o schema padronizado."""
    if observed_at is None:
        observed_at = datetime.now(UTC)

    # Identificadores
    orgao_cnpj = raw.get("orgaoEntidade", {}).get("cnpj", "")
    numero = raw.get("numeroContratoEmpenho", "")
    ano = raw.get("anoContratacao", "")
    seq = raw.get("sequencialContrato", "")

    contract_id = f"PNCP-{orgao_cnpj}-{ano}-{seq or numero}"

    # Parse datas
    def parse_date(d_str):
        if not d_str:
            return None
        try:
            return datetime.fromisoformat(d_str.replace("Z", "+00:00")).date()
        except Exception:
            try:
                return datetime.strptime(d_str[:10], "%Y-%m-%d").date()
            except Exception:
                return None

    valor_inicial = raw.get("valorInicial")
    valor_global = raw.get("valorGlobal") or valor_inicial or 0.0

    unidade = raw.get("unidadeOrgao", {})
    mun_nome = unidade.get("municipioNome")
    mun_uf = unidade.get("ufSigla")
    mun_cod = str(unidade.get("codigoIbge", "")) if unidade.get("codigoIbge") else None

    fornecedor_doc = raw.get("niFornecedor", "")
    fornecedor_nome = raw.get("nomeRazaoSocialFornecedor", "")

    return ContractRecord(
        contract_id=contract_id,
        source_system="PNCP",
        source_url=raw.get("urlContrato")
        or f"https://pncp.gov.br/app/contratos/{orgao_cnpj}/{ano}/{seq}",
        contract_number=str(numero) if numero else None,
        buyer_name=raw.get("orgaoEntidade", {}).get("razaoSocial", "Órgão Não Informado"),
        buyer_document=orgao_cnpj or None,
        supplier_name=fornecedor_nome or "Fornecedor Não Informado",
        supplier_document=fornecedor_doc or None,
        object=raw.get("objetoContrato"),
        amount_initial=float(valor_inicial) if valor_inicial is not None else None,
        amount_current=float(valor_global),
        signed_at=parse_date(raw.get("dataAssinatura")),
        starts_at=parse_date(raw.get("dataVigenciaInicio")),
        ends_at=parse_date(raw.get("dataVigenciaFim")),
        municipality_code=mun_cod,
        municipality_name=mun_nome,
        uf=mun_uf,
        observed_at=observed_at,
        snapshot_id=snapshot_id,
    )


def export_contracts_to_parquet(records: list[ContractRecord], output_path: Path) -> int:
    """Converte uma lista de registros normalizados em arquivo Apache Parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "contract_id": [r.contract_id for r in records],
        "source_system": [r.source_system for r in records],
        "source_url": [r.source_url for r in records],
        "contract_number": [r.contract_number for r in records],
        "buyer_name": [r.buyer_name for r in records],
        "buyer_document": [r.buyer_document for r in records],
        "supplier_name": [r.supplier_name for r in records],
        "supplier_document": [r.supplier_document for r in records],
        "object": [r.object for r in records],
        "amount_initial": [r.amount_initial for r in records],
        "amount_current": [r.amount_current for r in records],
        "signed_at": [r.signed_at for r in records],
        "starts_at": [r.starts_at for r in records],
        "ends_at": [r.ends_at for r in records],
        "municipality_code": [r.municipality_code for r in records],
        "municipality_name": [r.municipality_name for r in records],
        "uf": [r.uf for r in records],
        "observed_at": [r.observed_at for r in records],
        "snapshot_id": [r.snapshot_id for r in records],
    }

    table = pa.Table.from_pydict(data, schema=CONTRACTS_PYARROW_SCHEMA)
    pq.write_table(table, str(output_path), compression="snappy")
    logger.info(f"Parquet gravado com sucesso: {output_path} ({len(records)} linhas)")
    return len(records)
