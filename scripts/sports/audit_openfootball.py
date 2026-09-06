#!/usr/bin/env python3
"""Audit OpenFootball coverage quality for monitored Rondônia teams."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from ovigia_dados.sports.openfootball import (
    assess_rondonia_coverage,
    fetch_openfootball_inputs,
    write_quality_csvs,
)
from ovigia_dados.sports.registry import load_sports_registry


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mede cobertura real do OpenFootball para clubes monitorados de Rondônia"
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--registry-dir", default="knowledge/sports/registry")
    parser.add_argument(
        "--summary-output",
        default="datasets/sports/quality/openfootball-rondonia.csv",
    )
    parser.add_argument(
        "--teams-output",
        default="datasets/sports/quality/openfootball-rondonia-teams.csv",
    )
    args = parser.parse_args()

    registry = load_sports_registry(args.registry_dir)
    monitored_teams = [team["name"] for team in registry["teams"]]
    filenames, clubs_text, current_match_texts = fetch_openfootball_inputs(season=args.season)
    summary, team_rows = assess_rondonia_coverage(
        season=args.season,
        filenames=filenames,
        clubs_text=clubs_text,
        current_match_texts=current_match_texts,
        monitored_teams=monitored_teams,
    )
    write_quality_csvs(
        summary,
        team_rows,
        summary_path=args.summary_output,
        teams_path=args.teams_output,
    )

    print(
        "openfootball coverage: "
        f"season={summary['season']} "
        f"competitions={summary['available_competitions'] or 'none'} "
        f"club_registry={summary['teams_in_club_registry']}/{summary['monitored_teams']} "
        f"current_matches={summary['teams_in_current_brazil_matches']}/{summary['monitored_teams']} "
        f"assessment={summary['local_coverage']}"
    )


if __name__ == "__main__":
    main()
