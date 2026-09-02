import tempfile
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from ovigia_dados.collectors.contracts import export_contracts_to_parquet, normalize_pncp_contract


def test_normalize_pncp_contract():
    raw = {
        "orgaoEntidade": {"cnpj": "00394452000103", "razaoSocial": "17 BRIGADA DE SELVA"},
        "numeroContratoEmpenho": "10/2026",
        "anoContratacao": 2026,
        "sequencialContrato": 1,
        "valorInicial": 1500000.0,
        "valorGlobal": 1800000.0,
        "dataAssinatura": "2026-08-01",
        "dataVigenciaInicio": "2026-08-01",
        "dataVigenciaFim": "2027-08-01",
        "unidadeOrgao": {"municipioNome": "Porto Velho", "ufSigla": "RO", "codigoIbge": 1100205},
        "niFornecedor": "12345678000199",
        "nomeRazaoSocialFornecedor": "FORNECEDOR TESTE LTDA",
        "objetoContrato": "Construção e reforma",
    }
    rec = normalize_pncp_contract(
        raw, snapshot_id="2026-09", observed_at=datetime(2026, 9, 2, tzinfo=UTC)
    )
    assert rec.contract_id == "PNCP-00394452000103-2026-1"
    assert rec.buyer_name == "17 BRIGADA DE SELVA"
    assert rec.amount_current == 1800000.0
    assert rec.municipality_name == "Porto Velho"
    assert rec.uf == "RO"


def test_export_and_duckdb_query():
    raw = {
        "orgaoEntidade": {"cnpj": "00394452000103", "razaoSocial": "ORGAO TESTE"},
        "numeroContratoEmpenho": "01/2026",
        "anoContratacao": 2026,
        "sequencialContrato": 1,
        "valorInicial": 500000.0,
        "valorGlobal": 500000.0,
        "unidadeOrgao": {"municipioNome": "Porto Velho", "ufSigla": "RO"},
        "niFornecedor": "11111111000111",
        "nomeRazaoSocialFornecedor": "SUPPLIER TEST",
        "objetoContrato": "Serviço",
    }
    rec = normalize_pncp_contract(raw, snapshot_id="2026-09", observed_at=datetime.now(UTC))
    with tempfile.TemporaryDirectory() as tmpdir:
        pq_path = Path(tmpdir) / "test_contracts.parquet"
        count = export_contracts_to_parquet([rec], pq_path)
        assert count == 1
        assert pq_path.exists()

        # Query DuckDB
        con = duckdb.connect(":memory:")
        res = con.execute(
            f"SELECT contract_id, amount_current FROM read_parquet('{pq_path.as_posix()}')"
        ).fetchall()
        assert len(res) == 1
        assert res[0][1] == 500000.0
