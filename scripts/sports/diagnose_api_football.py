# /// script
# requires-python = ">=3.12"
# ///
"""Sonda descartável: descobre plano, cobertura e IDs reais na API-Football."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from ovigia_dados.sports.client import ApiFootballClient

TEAM_NAMES = [
    "Porto Velho",
    "Ji-Parana",
    "Genus",
    "Guajara",
    "Real Ariquemes",
    "Uniao Cacoalense",
    "Vilhenense",
]


def show(label: str, payload: dict) -> None:
    print(f"\n=== {label}")
    print(f"results={payload.get('results')} errors={payload.get('errors')}")


def main() -> None:
    client = ApiFootballClient()

    status = client.get("status")
    print("=== status")
    print(json.dumps(status.get("response", {}), ensure_ascii=False, indent=2))

    leagues = client.get("leagues", {"country": "Brazil", "search": "Rondoniense"})
    show("leagues search=Rondoniense", leagues)
    for item in leagues.get("response", []):
        league = item.get("league", {})
        seasons = [s.get("year") for s in item.get("seasons", []) or []]
        print(f"league_id={league.get('id')} name={league.get('name')} seasons={seasons}")

    for name in TEAM_NAMES:
        payload = client.get("teams", {"search": name})
        show(f"teams search={name}", payload)
        for item in payload.get("response", []):
            team = item.get("team", {})
            venue = item.get("venue", {})
            print(
                f"team_id={team.get('id')} name={team.get('name')} "
                f"country={team.get('country')} city={venue.get('city')}"
            )


if __name__ == "__main__":
    main()
