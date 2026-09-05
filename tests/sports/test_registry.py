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
    assert {league["league_id"] for league in registry["leagues"]} == {662, 73, 74, 598}
    assert {team["team_id"] for team in registry["teams"]} == {
        7780,
        7779,
        7784,
        7781,
        7782,
        7783,
        7785,
    }
    assert {team["team_id"] for team in registry["teams"] if team["city"] == "Porto Velho"} == {
        7780,
        7781,
    }
    assert all(team["is_local_focus"] for team in registry["teams"])
