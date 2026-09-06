"""Audit OpenFootball as a complementary open-data source for local football."""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Any

import requests
from ovigia_dados.sports.official_sources import DEFAULT_USER_AGENT

SOUTH_AMERICA_BRAZIL_API = (
    "https://api.github.com/repos/openfootball/south-america/contents/brazil?ref=master"
)
SOUTH_AMERICA_RAW = "https://raw.githubusercontent.com/openfootball/south-america/master/brazil"
BRAZIL_CLUBS_URL = (
    "https://raw.githubusercontent.com/openfootball/clubs/master/"
    "south-america/brazil/br.clubs.txt"
)

EXPECTED_BRAZIL_FILES = {
    "serie_a": "{season}_br1.txt",
    "serie_b": "{season}_br2.txt",
    "serie_c": "{season}_br3.txt",
    "serie_d": "{season}_br4.txt",
    "copa_do_brasil": "{season}_brcup.txt",
}

TEAM_FIELDS = ["team_name", "in_club_registry", "in_current_brazil_matches"]
SUMMARY_FIELDS = [
    "season",
    "license",
    "available_competitions",
    "missing_competitions",
    "monitored_teams",
    "teams_in_club_registry",
    "teams_in_current_brazil_matches",
    "local_coverage",
]


def _normalized(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()


def fetch_brazil_filenames(*, timeout: int = 30) -> list[str]:
    response = requests.get(
        SOUTH_AMERICA_BRAZIL_API,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    response.raise_for_status()
    return [item["name"] for item in response.json() if item.get("type") == "file"]


def fetch_text(url: str, *, timeout: int = 30) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": DEFAULT_USER_AGENT})
    response.raise_for_status()
    return response.text


def current_brazil_files(filenames: list[str], season: int) -> dict[str, str]:
    available = set(filenames)
    return {
        competition: filename.format(season=season)
        for competition, filename in EXPECTED_BRAZIL_FILES.items()
        if filename.format(season=season) in available
    }


def _team_mentioned(text: str, team_name: str) -> bool:
    needle = _normalized(team_name)
    haystack = _normalized(text)
    return bool(needle and needle in haystack)


def assess_rondonia_coverage(
    *,
    season: int,
    filenames: list[str],
    clubs_text: str,
    current_match_texts: dict[str, str],
    monitored_teams: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Measure whether OpenFootball can actually serve the local workflow."""
    available = current_brazil_files(filenames, season)
    missing = sorted(set(EXPECTED_BRAZIL_FILES) - set(available))
    combined_matches = "\n".join(current_match_texts.values())

    team_rows: list[dict[str, Any]] = []
    for team_name in sorted(monitored_teams):
        team_rows.append(
            {
                "team_name": team_name,
                "in_club_registry": _team_mentioned(clubs_text, team_name),
                "in_current_brazil_matches": _team_mentioned(combined_matches, team_name),
            }
        )

    club_hits = sum(bool(row["in_club_registry"]) for row in team_rows)
    match_hits = sum(bool(row["in_current_brazil_matches"]) for row in team_rows)
    local_coverage = "usable" if match_hits else "insufficient_for_rondonia"

    summary = {
        "season": season,
        "license": "CC0-1.0/public-domain",
        "available_competitions": ";".join(sorted(available)),
        "missing_competitions": ";".join(missing),
        "monitored_teams": len(team_rows),
        "teams_in_club_registry": club_hits,
        "teams_in_current_brazil_matches": match_hits,
        "local_coverage": local_coverage,
    }
    return summary, team_rows


def fetch_openfootball_inputs(
    *, season: int, timeout: int = 30
) -> tuple[list[str], str, dict[str, str]]:
    filenames = fetch_brazil_filenames(timeout=timeout)
    clubs_text = fetch_text(BRAZIL_CLUBS_URL, timeout=timeout)
    files = current_brazil_files(filenames, season)
    match_texts = {
        competition: fetch_text(f"{SOUTH_AMERICA_RAW}/{filename}", timeout=timeout)
        for competition, filename in files.items()
    }
    return filenames, clubs_text, match_texts


def write_quality_csvs(
    summary: dict[str, Any],
    team_rows: list[dict[str, Any]],
    *,
    summary_path: str | Path,
    teams_path: str | Path,
) -> None:
    summary_destination = Path(summary_path)
    teams_destination = Path(teams_path)
    summary_destination.parent.mkdir(parents=True, exist_ok=True)
    teams_destination.parent.mkdir(parents=True, exist_ok=True)

    with summary_destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerow(summary)

    with teams_destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TEAM_FIELDS)
        writer.writeheader()
        writer.writerows(team_rows)
