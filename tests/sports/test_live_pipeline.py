import pytest

from ovigia_dados.sports.client import ApiFootballPlanError
from scripts.sports import run_sports_pipeline as module

MONITORED_TEAM = 12946
OTHER_TEAM = 1229
UNRELATED_TEAM = 33


def _fixture(fixture_id, home_id, away_id):
    return {
        "fixture": {
            "id": fixture_id,
            "date": "2026-09-04T20:00:00Z",
            "status": {"short": "FT"},
        },
        "league": {"id": 615, "name": "Rondoniense", "season": 2026},
        "teams": {
            "home": {"id": home_id, "name": f"Time {home_id}"},
            "away": {"id": away_id, "name": f"Time {away_id}"},
        },
        "goals": {"home": 1, "away": 0},
        "score": {"halftime": {"home": 0, "away": 0}},
    }


class FakeClient:
    """Responde como a API-Football v3, registrando cada chamada recebida."""

    def __init__(self, standings_error: Exception | None = None):
        self.calls: list[tuple[str, dict | None]] = []
        self._standings_error = standings_error

    def get(self, endpoint, params=None):
        self.calls.append((endpoint, params))
        if endpoint == "teams":
            return {
                "response": [
                    {
                        "team": {"id": params["id"], "name": "Porto Velho", "country": "Brazil"},
                        "venue": {"id": 1, "name": "Aluizão", "city": "Porto Velho"},
                    }
                ]
            }
        if endpoint == "fixtures":
            team = params["team"]
            offset = 1 if "last" in params else 2
            return {"response": [_fixture(team * 10 + offset, team, OTHER_TEAM)]}
        if endpoint == "leagues":
            return {
                "response": [
                    {
                        "seasons": [
                            {"year": 2026, "coverage": {"standings": True}},
                            {"year": 2024, "coverage": {"standings": True}},
                        ]
                    }
                ]
            }
        if endpoint == "standings":
            if self._standings_error is not None:
                raise self._standings_error
            return {
                "response": [
                    {
                        "league": {
                            "standings": [
                                [
                                    {
                                        "rank": 1,
                                        "team": {"id": MONITORED_TEAM, "name": "Porto Velho"},
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


CONFIG = {
    "teams": [{"team_id": MONITORED_TEAM, "uf": "RO"}],
    "leagues": [{"league_id": 615}],
}


def test_fixtures_sao_pedidos_por_time_sem_season():
    client = FakeClient()

    module.collect_live_records(client, CONFIG, "2026-09-05")

    fixture_calls = [params for endpoint, params in client.calls if endpoint == "fixtures"]
    assert fixture_calls == [
        {"team": MONITORED_TEAM, "last": module.RECENT_FIXTURES_PER_TEAM},
        {"team": MONITORED_TEAM, "next": module.UPCOMING_FIXTURES_PER_TEAM},
    ]
    assert not any("season" in params or "date" in params for params in fixture_calls)


def test_uma_requisicao_por_time_e_nao_uma_varredura_do_dia():
    client = FakeClient()
    config = {
        "teams": [{"team_id": MONITORED_TEAM, "uf": "RO"}, {"team_id": OTHER_TEAM, "uf": "RO"}],
        "leagues": [{"league_id": 615}],
    }

    _, fixtures, _ = module.collect_live_records(client, config, "2026-09-05")

    fixture_calls = [params for endpoint, params in client.calls if endpoint == "fixtures"]
    assert len(fixture_calls) == 4
    assert {params["team"] for params in fixture_calls} == {MONITORED_TEAM, OTHER_TEAM}
    assert len(fixtures) == 4


def test_jogo_repetido_entre_dois_times_monitorados_conta_uma_vez():
    class Derby(FakeClient):
        def get(self, endpoint, params=None):
            if endpoint == "fixtures":
                self.calls.append((endpoint, params))
                return {"response": [_fixture(777, MONITORED_TEAM, OTHER_TEAM)]}
            return super().get(endpoint, params)

    config = {
        "teams": [{"team_id": MONITORED_TEAM, "uf": "RO"}, {"team_id": OTHER_TEAM, "uf": "RO"}],
        "leagues": [{"league_id": 615}],
    }

    _, fixtures, _ = module.collect_live_records(Derby(), config, "2026-09-05")

    assert [row["fixture_id"] for row in fixtures] == [777]


def test_cobertura_da_liga_e_consultada_sem_season():
    client = FakeClient()

    module.collect_live_records(client, CONFIG, "2026-09-05")

    assert ("leagues", {"id": 615}) in client.calls
    assert ("standings", {"league": 615, "season": 2026}) in client.calls


def test_standings_bloqueado_pelo_plano_nao_derruba_a_coleta():
    refusal = ApiFootballPlanError("standings", {"plan": "Free plans do not have access"})
    client = FakeClient(standings_error=refusal)

    _, fixtures, standings = module.collect_live_records(client, CONFIG, "2026-09-05")

    assert standings == []
    assert fixtures, "a recusa de standings não pode zerar os fixtures já coletados"


def test_chave_recusada_continua_derrubando_a_coleta():
    from ovigia_dados.sports.client import ApiFootballAuthError

    client = FakeClient(standings_error=ApiFootballAuthError("chave recusada"))

    with pytest.raises(ApiFootballAuthError):
        module.collect_live_records(client, CONFIG, "2026-09-05")
