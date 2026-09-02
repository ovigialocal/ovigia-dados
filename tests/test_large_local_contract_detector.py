import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ovigia_dados.collectors.contracts import export_contracts_to_parquet, normalize_pncp_contract
from ovigia_dados.detectors.large_local_contract import LargeLocalContractDetector


def test_large_local_contract_detector():
    records = [
        normalize_pncp_contract(
            {
                "orgaoEntidade": {"cnpj": "00394452000103", "razaoSocial": "ORGAO 1"},
                "numeroContratoEmpenho": "01/2026",
                "anoContratacao": 2026,
                "sequencialContrato": 1,
                "valorInicial": 10000000.0,
                "valorGlobal": 10000000.0,
                "unidadeOrgao": {"municipioNome": "Porto Velho", "ufSigla": "RO"},
                "niFornecedor": "11111111000111",
                "nomeRazaoSocialFornecedor": "BIG SUPPLIER",
                "objetoContrato": "Obra de grande porte",
            },
            snapshot_id="2026-09",
            observed_at=datetime.now(UTC),
        ),
        normalize_pncp_contract(
            {
                "orgaoEntidade": {"cnpj": "00394452000103", "razaoSocial": "ORGAO 2"},
                "numeroContratoEmpenho": "02/2026",
                "anoContratacao": 2026,
                "sequencialContrato": 2,
                "valorInicial": 50000.0,
                "valorGlobal": 50000.0,
                "unidadeOrgao": {"municipioNome": "Porto Velho", "ufSigla": "RO"},
                "niFornecedor": "22222222000122",
                "nomeRazaoSocialFornecedor": "SMALL SUPPLIER",
                "objetoContrato": "Material de consumo",
            },
            snapshot_id="2026-09",
            observed_at=datetime.now(UTC),
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        pq_path = Path(tmpdir) / "contracts.parquet"
        export_contracts_to_parquet(records, pq_path)

        detector = LargeLocalContractDetector(
            min_amount=1_000_000.0,
            percentile_threshold=90.0,
            target_municipality="Porto Velho",
            target_uf="RO",
        )
        signals = detector.run(pq_path)

        assert len(signals) == 1
        sig = signals[0]
        assert sig.contract_id == "PNCP-00394452000103-2026-1"
        assert sig.amount == 10000000.0
        assert sig.municipality_name == "Porto Velho"
        assert "amount_above_absolute_threshold" in sig.reason_codes
