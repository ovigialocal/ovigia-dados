"""Detectores determinísticos esportivos para clubes locais e regionais."""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)


@dataclass
class SportsSignal:
    signal_id: str
    detector: str
    observed_at: str
    entity_type: str  # "team", "player", "fixture", "league"
    entity_id: int
    league_id: int
    season: int
    reason_codes: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    fixture_id: int | None = None
    source_snapshot: str = ""
    source_endpoint: str = ""


class LocalTeamImportantResultDetector:
    """Detecta resultados esportivos materialmente excepcionais para clubes locais."""

    def __init__(self, monitored_team_ids: list[int]):
        self.monitored_team_ids = set(monitored_team_ids)

    def run(self, fixtures_parquet: Path, snapshot_id: str = "") -> list[SportsSignal]:
        con = duckdb.connect(":memory:")
        con.execute(
            f"CREATE TABLE fixtures AS SELECT * FROM read_parquet('{fixtures_parquet.as_posix()}')"
        )

        query = """
        SELECT
            fixture_id,
            league_id,
            season,
            home_team_id,
            home_team_name,
            away_team_id,
            away_team_name,
            score_home,
            score_away,
            status_short
        FROM fixtures
        WHERE status_short IN ('FT', 'AET', 'PEN')
          AND (score_home IS NOT NULL AND score_away IS NOT NULL)
        """
        rows = con.execute(query).fetchall()
        signals: list[SportsSignal] = []

        for r in rows:
            (fix_id, l_id, season, h_id, h_name, a_id, a_name, s_h, s_a, status) = r
            diff = abs(s_h - s_a)

            monitored_involved = []
            if h_id in self.monitored_team_ids:
                monitored_involved.append((h_id, h_name, "home", s_h > s_a, s_h < s_a))
            if a_id in self.monitored_team_ids:
                monitored_involved.append((a_id, a_name, "away", s_a > s_h, s_a < s_h))

            for t_id, _t_name, loc, won, lost in monitored_involved:
                reasons = []
                if diff >= 4:
                    if won:
                        reasons.append("high_margin_victory")
                    elif lost:
                        reasons.append("high_margin_defeat")

                if (s_h + s_a) >= 6:
                    reasons.append("high_scoring_match")

                if reasons:
                    sig = SportsSignal(
                        signal_id=f"RES-{fix_id}-{t_id}",
                        detector="local-team-important-result-v1",
                        observed_at=datetime.now(UTC).isoformat(),
                        entity_type="team",
                        entity_id=t_id,
                        fixture_id=fix_id,
                        league_id=l_id,
                        season=season,
                        reason_codes=reasons,
                        metrics={
                            "home_team": h_name,
                            "away_team": a_name,
                            "score_home": s_h,
                            "score_away": s_a,
                            "goal_difference": diff,
                            "total_goals": s_h + s_a,
                            "team_role": loc,
                        },
                        source_snapshot=snapshot_id,
                        source_endpoint="fixtures",
                    )
                    signals.append(sig)

        return signals


class LocalTeamStandingsMovementDetector:
    """Detecta mudanças materiais na tabela de classificação de clubes monitorados."""

    def __init__(self, monitored_team_ids: list[int]):
        self.monitored_team_ids = set(monitored_team_ids)

    def run(self, standings_parquet: Path, snapshot_id: str = "") -> list[SportsSignal]:
        con = duckdb.connect(":memory:")
        con.execute(
            f"CREATE TABLE standings AS SELECT * FROM read_parquet('{standings_parquet.as_posix()}')"
        )

        query = """
        SELECT
            league_id,
            season,
            rank,
            team_id,
            team_name,
            points,
            goals_diff,
            description,
            all_played
        FROM standings
        """
        rows = con.execute(query).fetchall()
        signals: list[SportsSignal] = []

        for r in rows:
            l_id, season, rank, t_id, t_name, pts, gd, desc, played = r
            if t_id not in self.monitored_team_ids:
                continue

            reasons = []
            if rank == 1 and played > 0:
                reasons.append("league_leader")

            if desc:
                d_lower = desc.lower()
                if (
                    "promotion" in d_lower
                    or "next round" in d_lower
                    or "semi-finals" in d_lower
                    or "final" in d_lower
                ):
                    reasons.append("qualification_zone")
                elif "relegation" in d_lower:
                    reasons.append("relegation_zone")

            if reasons:
                sig = SportsSignal(
                    signal_id=f"STD-{l_id}-{season}-{t_id}",
                    detector="local-team-standings-movement-v1",
                    observed_at=datetime.now(UTC).isoformat(),
                    entity_type="team",
                    entity_id=t_id,
                    league_id=l_id,
                    season=season,
                    reason_codes=reasons,
                    metrics={
                        "team_name": t_name,
                        "rank": rank,
                        "points": pts,
                        "goals_diff": gd,
                        "status_description": desc,
                        "matches_played": played,
                    },
                    source_snapshot=snapshot_id,
                    source_endpoint="standings",
                )
                signals.append(sig)

        return signals
