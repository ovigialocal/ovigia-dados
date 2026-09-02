import tempfile
from pathlib import Path

from ovigia_dados.sports.collectors.normalizer import (
    FIXTURES_SCHEMA,
    STANDINGS_SCHEMA,
    normalize_fixture,
    normalize_standing_entry,
    write_records_to_parquet,
)
from ovigia_dados.sports.detectors.sports_detectors import (
    LocalTeamImportantResultDetector,
    LocalTeamStandingsMovementDetector,
)


def test_sports_result_detector_high_margin():
    raw_fixture = {
        "fixture": {
            "id": 555,
            "date": "2026-09-01T19:00:00Z",
            "status": {"short": "FT", "elapsed": 90},
        },
        "league": {"id": 662, "name": "Rondoniense", "season": 2026, "round": "Rodada 1"},
        "teams": {
            "home": {"id": 7780, "name": "Porto Velho EC"},
            "away": {"id": 7779, "name": "Ji-Paraná FC"},
        },
        "goals": {"home": 5, "away": 0},
        "score": {"halftime": {"home": 2, "away": 0}},
    }
    rec = normalize_fixture(raw_fixture, snapshot_id="2026-09-02")
    with tempfile.TemporaryDirectory() as tmpdir:
        pq_path = Path(tmpdir) / "fixtures.parquet"
        write_records_to_parquet([rec], FIXTURES_SCHEMA, pq_path)

        detector = LocalTeamImportantResultDetector(monitored_team_ids=[7780, 7779])
        signals = detector.run(pq_path, snapshot_id="2026-09-02")

        assert len(signals) == 2  # 1 para Porto Velho (vitória), 1 para Ji-Paraná (derrota)
        pvo_sig = next(s for s in signals if s.entity_id == 7780)
        assert "high_margin_victory" in pvo_sig.reason_codes
        assert pvo_sig.metrics["goal_difference"] == 5


def test_sports_standings_movement_detector():
    raw_standing = {
        "rank": 1,
        "team": {"id": 7780, "name": "Porto Velho EC"},
        "points": 18,
        "goalsDiff": 12,
        "group": "Grupo Único",
        "description": "Promotion to Semifinals",
        "all": {"played": 6, "win": 6, "draw": 0, "lose": 0},
    }
    rec = normalize_standing_entry(
        raw_standing, league_id=662, season=2026, snapshot_id="2026-09-02"
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        pq_path = Path(tmpdir) / "standings.parquet"
        write_records_to_parquet([rec], STANDINGS_SCHEMA, pq_path)

        detector = LocalTeamStandingsMovementDetector(monitored_team_ids=[7780])
        signals = detector.run(pq_path, snapshot_id="2026-09-02")

        assert len(signals) == 1
        sig = signals[0]
        assert sig.entity_id == 7780
        assert "league_leader" in sig.reason_codes
        assert "qualification_zone" in sig.reason_codes
