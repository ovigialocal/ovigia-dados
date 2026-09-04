from importlib import util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sports" / "run_sports_pipeline.py"
spec = util.spec_from_file_location("run_sports_pipeline", SCRIPT)
module = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class FakeClient:
    def __init__(self):
        self.calls = []

    def get(self, endpoint, params=None):
        self.calls.append((endpoint, params))
        if endpoint == "teams":
            team_id = params["id"]
            return {
                "response": [
                    {
                        "team": {
                            "id": team_id,
                            "name": "Porto Velho EC",
                            "country": "Brazil",
                        },
                        "venue": {"id": 1, "name": "Aluizão", "city": "Porto Velho"},
                    }
                ]
            }
        if endpoint == "fixtures":
            team_id = params["team"]
            return {
                "response": [
                    {
                        "fixture": {
                            "id": 99,
                            "date": "2026-09-01T20:00:00Z",
                            "status": {"short": "FT"},
                        },
                        "league": {"id": 662, "name": "Rondoniense", "season": 2026},
                        "teams": {
                            "home": {"id": team_id, "name": "Porto Velho EC"},
                            "away": {"id": 2, "name": "Adversário"},
                        },
                        "goals": {"home": 1, "away": 0},
                        "score": {"halftime": {"home": 0, "away": 0}},
                    }
                ]
            }
        if endpoint == "leagues":
            return {
                "response": [
                    {
                        "seasons": [
                            {
                                "year": 2026,
                                "coverage": {
                                    "fixtures": {"events": True},
                                    "standings": True,
                                },
                            }
                        ]
                    }
                ]
            }
        if endpoint == "standings":
            return {
                "response": [
                    {
                        "league": {
                            "standings": [
                                [
                                    {
                                        "rank": 1,
                                        "team": {"id": 7780, "name": "Porto Velho EC"},
                                        "points": 3,
                                        "goalsDiff": 1,
                                        "all": {"played": 1, "win": 1, "draw": 0, "lose": 0},
                                    }
                                ]
                            ]
                        }
                    }
                ]
            }
        raise AssertionError(endpoint)


def test_live_collection_uses_api_and_coverage():
    client = FakeClient()
    config = {
        "teams": [{"team_id": 7780, "uf": "RO"}],
        "leagues": [{"league_id": 662}],
    }

    teams, fixtures, standings = module.collect_live_records(client, config, "2026-09-04")

    assert [row["team_id"] for row in teams] == [7780]
    assert [row["fixture_id"] for row in fixtures] == [99]
    assert [row["team_id"] for row in standings] == [7780]
    assert ("teams", {"id": 7780}) in client.calls
    assert ("fixtures", {"team": 7780, "season": 2026}) in client.calls
    assert ("leagues", {"id": 662, "season": 2026}) in client.calls
    assert ("standings", {"league": 662, "season": 2026}) in client.calls
