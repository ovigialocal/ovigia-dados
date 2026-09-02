"""Pipeline diário de aquisição, normalização e detecção de contratos federais."""

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from ovigia_dados.archive.publisher import compute_sha256
from ovigia_dados.collectors.contracts import export_contracts_to_parquet, normalize_pncp_contract
from ovigia_dados.detectors.large_local_contract import LargeLocalContractDetector
from ovigia_dados.schemas import SnapshotManifest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Executa pipeline de contratos federais")
    parser.add_argument(
        "--snapshot-id",
        default=datetime.now(UTC).strftime("%Y-%m"),
        help="Identificador do snapshot (ex: 2026-09)",
    )
    parser.add_argument(
        "--output-dir", default="data/output/contracts", help="Diretório de saída dos artefatos"
    )
    parser.add_argument(
        "--sample-data", help="Caminho para arquivo JSON de amostra para testes locais"
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    parquet_file = out_dir / "contracts.parquet"
    manifest_file = out_dir / "manifest.json"
    signals_file = out_dir / "signals.jsonl"

    raw_records = []
    if args.sample_data and Path(args.sample_data).exists():
        logger.info(f"Carregando amostra local de: {args.sample_data}")
        raw_records = json.loads(Path(args.sample_data).read_text(encoding="utf-8"))
    else:
        logger.info("Executando simulação de dados amostrais para Porto Velho / RO")
        # Amostra mínima de teste determinístico
        raw_records = [
            {
                "orgaoEntidade": {
                    "cnpj": "00394452000103",
                    "razaoSocial": "COMANDO DO EXERCITO - 17 BRIGADA DE INFANTARIA DE SELVA",
                },
                "numeroContratoEmpenho": "12/2026",
                "anoContratacao": 2026,
                "sequencialContrato": 1,
                "valorInicial": 18500000.0,
                "valorGlobal": 18500000.0,
                "dataAssinatura": "2026-08-15",
                "dataVigenciaInicio": "2026-08-15",
                "dataVigenciaFim": "2027-08-15",
                "unidadeOrgao": {
                    "municipioNome": "Porto Velho",
                    "ufSigla": "RO",
                    "codigoIbge": 1100205,
                },
                "niFornecedor": "12345678000199",
                "nomeRazaoSocialFornecedor": "CONSTRUTORA AMAZONIA FORTE LTDA",
                "objetoContrato": "Construção de instalações logísticas e operacionais em Porto Velho/RO",
            },
            {
                "orgaoEntidade": {
                    "cnpj": "34415524000181",
                    "razaoSocial": "UNIVERSIDADE FEDERAL DE RONDONIA",
                },
                "numeroContratoEmpenho": "05/2026",
                "anoContratacao": 2026,
                "sequencialContrato": 2,
                "valorInicial": 450000.0,
                "valorGlobal": 450000.0,
                "dataAssinatura": "2026-08-10",
                "dataVigenciaInicio": "2026-08-10",
                "dataVigenciaFim": "2027-08-10",
                "unidadeOrgao": {
                    "municipioNome": "Porto Velho",
                    "ufSigla": "RO",
                    "codigoIbge": 1100205,
                },
                "niFornecedor": "98765432000188",
                "nomeRazaoSocialFornecedor": "SERVICOS E TECNOLOGIA NORTE LTDA",
                "objetoContrato": "Prestação de serviços de suporte de TI no campus de Porto Velho",
            },
            {
                "orgaoEntidade": {
                    "cnpj": "00394452000103",
                    "razaoSocial": "SUPERINTENDENCIA REGIONAL POLICIA FEDERAL RO",
                },
                "numeroContratoEmpenho": "02/2026",
                "anoContratacao": 2026,
                "sequencialContrato": 3,
                "valorInicial": 120000.0,
                "valorGlobal": 120000.0,
                "dataAssinatura": "2026-08-01",
                "dataVigenciaInicio": "2026-08-01",
                "dataVigenciaFim": "2027-08-01",
                "unidadeOrgao": {
                    "municipioNome": "Porto Velho",
                    "ufSigla": "RO",
                    "codigoIbge": 1100205,
                },
                "niFornecedor": "11223344000155",
                "nomeRazaoSocialFornecedor": "LIMPEZA E MANUTENCAO RONDONIA EIRELI",
                "objetoContrato": "Serviços continuados de limpeza e conservação predial",
            },
        ]

    normalized = [normalize_pncp_contract(r, snapshot_id=args.snapshot_id) for r in raw_records]
    export_contracts_to_parquet(normalized, parquet_file)

    # Gera manifesto
    manifest = SnapshotManifest(
        dataset_id="contracts",
        snapshot_id=args.snapshot_id,
        source_url="https://pncp.gov.br",
        observed_at=datetime.now(UTC),
        row_count=len(normalized),
        sha256_parquet=compute_sha256(parquet_file),
        schema_version="1.0",
    )
    manifest_file.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"Manifesto gravado: {manifest_file}")

    # Executa detector
    logger.info("Executando detector large-local-contract-v1...")
    detector = LargeLocalContractDetector(
        min_amount=1_000_000.0,
        percentile_threshold=90.0,
        target_municipality="Porto Velho",
        target_uf="RO",
    )
    signals = detector.run(parquet_file)

    with open(signals_file, "w", encoding="utf-8") as f:
        for s in signals:
            f.write(json.dumps(s.__dict__, ensure_ascii=False) + "\n")

    logger.info(f"Pipeline concluído com sucesso. {len(signals)} sinais emitidos.")


if __name__ == "__main__":
    main()
