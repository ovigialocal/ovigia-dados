# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "duckdb>=1.0.0",
#     "pyarrow>=15.0.0",
#     "pydantic>=2.0.0",
#     "internetarchive>=4.0.0",
# ]
# ///
"""Pipeline esportivo para API-Football v3 com extração, normalização e detecção."""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from ovigia_dados.archive.publisher import compute_sha256
from ovigia_dados.schemas import SnapshotManifest
from ovigia_dados.sports.collectors.normalizer import (
    FIXTURES_SCHEMA,
    STANDINGS_SCHEMA,
    TEAMS_SCHEMA,
    normalize_fixture,
    normalize_standing_entry,
    normalize_team,
    write_records_to_parquet,
)
from ovigia_dados.sports.detectors.sports_detectors import (
    LocalTeamImportantResultDetector,
    LocalTeamStandingsMovementDetector,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Executa pipeline de dados esportivos (API-Football)"
    )
    parser.add_argument(
        "--snapshot-id",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Identificador do snapshot (ex: 2026-09-02)",
    )
    parser.add_argument(
        "--output-dir", default="data/output/sports", help="Diretório de saída dos artefatos"
    )
    parser.add_argument(
        "--mock-sample", action="store_true", help="Usa dados simulados para teste local e CI"
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    config_path = Path("datasets/sports/config/monitored_entities.json")
    config = (
        json.loads(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {"teams": [], "leagues": []}
    )
    monitored_team_ids = [t["team_id"] for t in config.get("teams", [])]

    teams_records = []
    fixtures_records = []
    standings_records = []

    logger.info("Executando pipeline esportivo em modo demonstrativo / mock...")
    teams_records = [
        normalize_team(
            {
                "team": {
                    "id": 7780,
                    "name": "Porto Velho EC",
                    "code": "PVO",
                    "country": "Brazil",
                    "founded": 2018,
                },
                "venue": {"id": 1001, "name": "Estádio Aluízio Ferreira", "city": "Porto Velho"},
            },
            uf="RO",
            snapshot_id=args.snapshot_id,
        ),
        normalize_team(
            {
                "team": {
                    "id": 7779,
                    "name": "Ji-Paraná FC",
                    "code": "JIP",
                    "country": "Brazil",
                    "founded": 1991,
                },
                "venue": {"id": 1002, "name": "Estádio Biancão", "city": "Ji-Paraná"},
            },
            uf="RO",
            snapshot_id=args.snapshot_id,
        ),
    ]

    fixtures_records = [
        normalize_fixture(
            {
                "fixture": {
                    "id": 10001,
                    "date": "2026-09-01T20:00:00Z",
                    "status": {"short": "FT", "elapsed": 90},
                    "venue": {"name": "Aluizão", "city": "Porto Velho"},
                },
                "league": {
                    "id": 662,
                    "name": "Rondoniense",
                    "season": 2026,
                    "round": "Final - Ida",
                },
                "teams": {
                    "home": {"id": 7780, "name": "Porto Velho EC"},
                    "away": {"id": 7779, "name": "Ji-Paraná FC"},
                },
                "goals": {"home": 5, "away": 0},
                "score": {"halftime": {"home": 2, "away": 0}},
            },
            snapshot_id=args.snapshot_id,
        )
    ]

    standings_records = [
        normalize_standing_entry(
            {
                "rank": 1,
                "team": {"id": 7780, "name": "Porto Velho EC"},
                "points": 24,
                "goalsDiff": 15,
                "group": "Grupo A",
                "description": "Promotion to Final",
                "all": {"played": 8, "win": 7, "draw": 1, "lose": 0},
            },
            league_id=662,
            season=2026,
            snapshot_id=args.snapshot_id,
        )
    ]

    teams_file = out_dir / "teams.parquet"
    fixtures_file = out_dir / "fixtures.parquet"
    standings_file = out_dir / "standings.parquet"
    manifest_file = out_dir / "manifest.json"
    signals_file = out_dir / "sports-signals.jsonl"

    write_records_to_parquet(teams_records, TEAMS_SCHEMA, teams_file)
    write_records_to_parquet(fixtures_records, FIXTURES_SCHEMA, fixtures_file)
    write_records_to_parquet(standings_records, STANDINGS_SCHEMA, standings_file)

    manifest = SnapshotManifest(
        dataset_id="sports",
        snapshot_id=args.snapshot_id,
        source_url="https://v3.football.api-sports.io",
        observed_at=datetime.now(UTC),
        row_count=len(teams_records) + len(fixtures_records) + len(standings_records),
        sha256_parquet=compute_sha256(fixtures_file),
        schema_version="1.0",
    )
    manifest_file.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    signals = []
    res_det = LocalTeamImportantResultDetector(monitored_team_ids=monitored_team_ids)
    signals.extend(res_det.run(fixtures_file, snapshot_id=args.snapshot_id))

    std_det = LocalTeamStandingsMovementDetector(monitored_team_ids=monitored_team_ids)
    signals.extend(std_det.run(standings_file, snapshot_id=args.snapshot_id))

    with open(signals_file, "w", encoding="utf-8") as f:
        for s in signals:
            f.write(json.dumps(s.__dict__, ensure_ascii=False) + "\n")

    logger.info(f"Pipeline esportivo concluído. {len(signals)} sinais emitidos.")


if __name__ == "__main__":
    main()
