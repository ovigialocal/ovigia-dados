# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "duckdb>=1.0.0",
#     "pyarrow>=15.0.0",
#     "pydantic>=2.0.0",
#     "internetarchive>=4.0.0",
#     "okf-parser==0.45.2",
# ]
# ///
"""Pipeline esportivo para API-Football v3 com extração, normalização e detecção."""

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from ovigia_dados.archive.publisher import compute_sha256
from ovigia_dados.schemas import SnapshotManifest
from ovigia_dados.sports.client import ApiFootballClient
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
from ovigia_dados.sports.leads import materialize_signal_concepts
from ovigia_dados.sports.registry import load_sports_registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _season_from_snapshot(snapshot_id: str) -> int:
    try:
        return int(snapshot_id[:4])
    except (TypeError, ValueError):
        return datetime.now(UTC).year


def _flatten_standings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for response_item in payload.get("response", []):
        league = response_item.get("league", {})
        for group in league.get("standings", []) or []:
            rows.extend(group)
    return rows


def collect_live_records(
    client: ApiFootballClient,
    config: dict[str, Any],
    snapshot_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect current API-Football data only for configured entities."""
    season = _season_from_snapshot(snapshot_id)
    team_configs = config.get("teams", [])
    league_configs = config.get("leagues", [])

    teams_records: list[dict[str, Any]] = []
    fixtures_by_id: dict[int, dict[str, Any]] = {}
    standings_records: list[dict[str, Any]] = []

    for team_cfg in team_configs:
        team_id = int(team_cfg["team_id"])
        team_payload = client.get("teams", {"id": team_id})
        for raw in team_payload.get("response", []):
            teams_records.append(
                normalize_team(raw, uf=team_cfg.get("uf"), snapshot_id=snapshot_id)
            )

        fixture_payload = client.get("fixtures", {"team": team_id, "season": season})
        for raw in fixture_payload.get("response", []):
            normalized = normalize_fixture(raw, snapshot_id=snapshot_id)
            fixture_id = normalized.get("fixture_id")
            if fixture_id is not None:
                fixtures_by_id[int(fixture_id)] = normalized

    for league_cfg in league_configs:
        league_id = int(league_cfg["league_id"])
        coverage_payload = client.get("leagues", {"id": league_id, "season": season})
        has_standings = False
        for response_item in coverage_payload.get("response", []):
            for season_info in response_item.get("seasons", []) or []:
                if int(season_info.get("year", -1)) == season:
                    coverage = season_info.get("coverage", {}) or {}
                    fixtures_coverage = coverage.get("fixtures", {}) or {}
                    has_standings = bool(coverage.get("standings"))
                    logger.info(
                        "Coverage league=%s season=%s fixtures=%s standings=%s",
                        league_id,
                        season,
                        bool(fixtures_coverage),
                        has_standings,
                    )

        if not has_standings:
            continue

        standings_payload = client.get("standings", {"league": league_id, "season": season})
        for raw in _flatten_standings(standings_payload):
            standings_records.append(
                normalize_standing_entry(
                    raw,
                    league_id=league_id,
                    season=season,
                    snapshot_id=snapshot_id,
                )
            )

    return teams_records, list(fixtures_by_id.values()), standings_records


def mock_records(snapshot_id: str):
    teams_records = [
        normalize_team(
            {
                "team": {"id": 7780, "name": "Porto Velho EC", "code": "PVO", "country": "Brazil", "founded": 2018},
                "venue": {"id": 1001, "name": "Estádio Aluízio Ferreira", "city": "Porto Velho"},
            },
            uf="RO",
            snapshot_id=snapshot_id,
        ),
        normalize_team(
            {
                "team": {"id": 7779, "name": "Ji-Paraná FC", "code": "JIP", "country": "Brazil", "founded": 1991},
                "venue": {"id": 1002, "name": "Estádio Biancão", "city": "Ji-Paraná"},
            },
            uf="RO",
            snapshot_id=snapshot_id,
        ),
    ]
    fixtures_records = [
        normalize_fixture(
            {
                "fixture": {"id": 10001, "date": "2026-09-01T20:00:00Z", "status": {"short": "FT", "elapsed": 90}, "venue": {"name": "Aluizão", "city": "Porto Velho"}},
                "league": {"id": 662, "name": "Rondoniense", "season": 2026, "round": "Final - Ida"},
                "teams": {"home": {"id": 7780, "name": "Porto Velho EC"}, "away": {"id": 7779, "name": "Ji-Paraná FC"}},
                "goals": {"home": 5, "away": 0},
                "score": {"halftime": {"home": 2, "away": 0}},
            },
            snapshot_id=snapshot_id,
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
            snapshot_id=snapshot_id,
        )
    ]
    return teams_records, fixtures_records, standings_records


def main():
    parser = argparse.ArgumentParser(description="Executa pipeline de dados esportivos (API-Football)")
    parser.add_argument("--snapshot-id", default=datetime.now(UTC).strftime("%Y-%m-%d"), help="Identificador do snapshot (ex: 2026-09-02)")
    parser.add_argument("--output-dir", default="data/output/sports", help="Diretório de saída dos artefatos")
    parser.add_argument("--registry-dir", default="knowledge/sports/registry", help="Bundle OKF que define regiões, competições e equipes monitoradas")
    parser.add_argument("--leads-dir", default="knowledge/sports/leads", help="Bundle OKF persistente de sinais editoriais")
    parser.add_argument("--mock-sample", action="store_true", help="Usa dados simulados para teste local e CI")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = load_sports_registry(args.registry_dir)
    monitored_team_ids = [int(t["team_id"]) for t in config.get("teams", [])]

    if args.mock_sample:
        logger.info("Executando pipeline esportivo com fixture mock explícita.")
        teams_records, fixtures_records, standings_records = mock_records(args.snapshot_id)
    else:
        logger.info("Executando coleta real da API-Football para entidades monitoradas em OKF.")
        teams_records, fixtures_records, standings_records = collect_live_records(ApiFootballClient(), config, args.snapshot_id)

    teams_file = out_dir / "teams.parquet"
    fixtures_file = out_dir / "fixtures.parquet"
    standings_file = out_dir / "standings.parquet"
    manifest_file = out_dir / "manifest.json"

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
    signals.extend(LocalTeamImportantResultDetector(monitored_team_ids=monitored_team_ids).run(fixtures_file, snapshot_id=args.snapshot_id))
    signals.extend(LocalTeamStandingsMovementDetector(monitored_team_ids=monitored_team_ids).run(standings_file, snapshot_id=args.snapshot_id))

    signal_records = [signal.__dict__ for signal in signals]
    created = materialize_signal_concepts(signal_records, args.leads_dir)

    logger.info(
        "Pipeline esportivo concluído: teams=%s fixtures=%s standings=%s signals=%s new_leads=%s",
        len(teams_records), len(fixtures_records), len(standings_records), len(signals), len(created),
    )


if __name__ == "__main__":
    main()
