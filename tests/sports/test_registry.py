from pathlib import Path

from ovigia_dados.sports.registry import load_sports_registry


def test_repository_registry_projects_expected_entities():
    registry = load_sports_registry(Path("knowledge/sports/registry"))

    assert registry["monitored_regions"] == [
        {
            "uf": "RO",
            "municipality_name": "Porto Velho",
            "municipality_code": "1100205",
        }
    ]
    # IDs conferidos contra a API-Football em 2026-09-05 (ver PR).
    assert {league["league_id"] for league in registry["leagues"]} == {615, 73, 76, 843}
    assert {team["team_id"] for team in registry["teams"]} == {
        12946,
        10675,
        2219,
        1229,
        12943,
        12947,
        12281,
    }
    assert {team["team_id"] for team in registry["teams"] if team["city"] == "Porto Velho"} == {
        12946,
        1229,
    }
    assert all(team["is_local_focus"] for team in registry["teams"])
