"""Normalização de respostas da API-Football para esquemas analíticos Apache Parquet."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

TEAMS_SCHEMA = pa.schema(
    [
        ("team_id", pa.int32()),
        ("name", pa.string()),
        ("code", pa.string()),
        ("country", pa.string()),
        ("founded", pa.int32()),
        ("national", pa.bool_()),
        ("logo", pa.string()),
        ("venue_id", pa.int32()),
        ("venue_name", pa.string()),
        ("venue_city", pa.string()),
        ("uf", pa.string()),
        ("observed_at", pa.timestamp("us")),
        ("snapshot_id", pa.string()),
    ]
)

FIXTURES_SCHEMA = pa.schema(
    [
        ("fixture_id", pa.int32()),
        ("date", pa.timestamp("us")),
        ("status_short", pa.string()),
        ("elapsed", pa.int32()),
        ("league_id", pa.int32()),
        ("league_name", pa.string()),
        ("season", pa.int32()),
        ("round", pa.string()),
        ("home_team_id", pa.int32()),
        ("home_team_name", pa.string()),
        ("away_team_id", pa.int32()),
        ("away_team_name", pa.string()),
        ("score_home", pa.int32()),
        ("score_away", pa.int32()),
        ("score_halftime_home", pa.int32()),
        ("score_halftime_away", pa.int32()),
        ("venue_name", pa.string()),
        ("venue_city", pa.string()),
        ("observed_at", pa.timestamp("us")),
        ("snapshot_id", pa.string()),
    ]
)

STANDINGS_SCHEMA = pa.schema(
    [
        ("league_id", pa.int32()),
        ("season", pa.int32()),
        ("rank", pa.int32()),
        ("team_id", pa.int32()),
        ("team_name", pa.string()),
        ("points", pa.int32()),
        ("goals_diff", pa.int32()),
        ("group_name", pa.string()),
        ("description", pa.string()),
        ("all_played", pa.int32()),
        ("all_win", pa.int32()),
        ("all_draw", pa.int32()),
        ("all_lose", pa.int32()),
        ("observed_at", pa.timestamp("us")),
        ("snapshot_id", pa.string()),
    ]
)


def normalize_team(
    raw: dict[str, Any], uf: str | None, snapshot_id: str, observed_at: datetime | None = None
) -> dict[str, Any]:
    if observed_at is None:
        observed_at = datetime.now(UTC)
    t = raw.get("team", {})
    v = raw.get("venue", {})
    return {
        "team_id": t.get("id"),
        "name": t.get("name"),
        "code": t.get("code"),
        "country": t.get("country"),
        "founded": t.get("founded"),
        "national": t.get("national", False),
        "logo": t.get("logo"),
        "venue_id": v.get("id"),
        "venue_name": v.get("name"),
        "venue_city": v.get("city"),
        "uf": uf,
        "observed_at": observed_at,
        "snapshot_id": snapshot_id,
    }


def normalize_fixture(
    raw: dict[str, Any], snapshot_id: str, observed_at: datetime | None = None
) -> dict[str, Any]:
    if observed_at is None:
        observed_at = datetime.now(UTC)
    f = raw.get("fixture", {})
    league = raw.get("league", {})
    teams = raw.get("teams", {})
    goals = raw.get("goals", {})
    score = raw.get("score", {})

    dt_str = f.get("date")
    fixture_dt = None
    if dt_str:
        try:
            fixture_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            pass

    return {
        "fixture_id": f.get("id"),
        "date": fixture_dt or observed_at,
        "status_short": f.get("status", {}).get("short", "NS"),
        "elapsed": f.get("status", {}).get("elapsed"),
        "league_id": league.get("id"),
        "league_name": league.get("name", ""),
        "season": league.get("season", 0),
        "round": league.get("round"),
        "home_team_id": teams.get("home", {}).get("id"),
        "home_team_name": teams.get("home", {}).get("name", ""),
        "away_team_id": teams.get("away", {}).get("id"),
        "away_team_name": teams.get("away", {}).get("name", ""),
        "score_home": goals.get("home"),
        "score_away": goals.get("away"),
        "score_halftime_home": score.get("halftime", {}).get("home"),
        "score_halftime_away": score.get("halftime", {}).get("away"),
        "venue_name": f.get("venue", {}).get("name"),
        "venue_city": f.get("venue", {}).get("city"),
        "observed_at": observed_at,
        "snapshot_id": snapshot_id,
    }


def normalize_standing_entry(
    raw: dict[str, Any],
    league_id: int,
    season: int,
    snapshot_id: str,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    if observed_at is None:
        observed_at = datetime.now(UTC)
    t = raw.get("team", {})
    all_stats = raw.get("all", {})
    return {
        "league_id": league_id,
        "season": season,
        "rank": raw.get("rank"),
        "team_id": t.get("id"),
        "team_name": t.get("name", ""),
        "points": raw.get("points", 0),
        "goals_diff": raw.get("goalsDiff", 0),
        "group_name": raw.get("group"),
        "description": raw.get("description"),
        "all_played": all_stats.get("played", 0),
        "all_win": all_stats.get("win", 0),
        "all_draw": all_stats.get("draw", 0),
        "all_lose": all_stats.get("lose", 0),
        "observed_at": observed_at,
        "snapshot_id": snapshot_id,
    }


def write_records_to_parquet(
    records: list[dict[str, Any]], schema: pa.Schema, output_path: Path
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        empty_table = pa.Table.from_batches([], schema=schema)
        pq.write_table(empty_table, str(output_path), compression="snappy")
        return 0
    pydict = {field.name: [r.get(field.name) for r in records] for field in schema}
    table = pa.Table.from_pydict(pydict, schema=schema)
    pq.write_table(table, str(output_path), compression="snappy")
    return len(records)
