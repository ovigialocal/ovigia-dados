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
            # O endpoint por data devolve o mundo inteiro; o recorte é nosso.
            return {
                "response": [
                    _fixture(int(params["date"].replace("-", "")), MONITORED_TEAM, OTHER_TEAM),
                    _fixture(90000, UNRELATED_TEAM, 34),
                ]
            }
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


def test_fixtures_sao_coletados_por_data_e_nao_por_season():
    client = FakeClient()

    module.collect_live_records(client, CONFIG, "2026-09-05")

    fixture_calls = [params for endpoint, params in client.calls if endpoint == "fixtures"]
    assert [params["date"] for params in fixture_calls] == [
        "2026-09-04",
        "2026-09-05",
        "2026-09-06",
    ]
    assert not any("season" in params for params in fixture_calls)


def test_coleta_por_data_descarta_jogos_de_times_nao_monitorados():
    client = FakeClient()

    _, fixtures, _ = module.collect_live_records(client, CONFIG, "2026-09-05")

    assert {row["fixture_id"] for row in fixtures} == {20260904, 20260905, 20260906}
    assert all(MONITORED_TEAM in (row["home_team_id"], row["away_team_id"]) for row in fixtures)


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
