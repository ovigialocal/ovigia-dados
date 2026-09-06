import io
import json
import urllib.error

import pytest

from ovigia_dados.sports.client import (
    RAPIDAPI_BASE_URL,
    RAPIDAPI_HOST,
    ApiFootballAuthError,
    ApiFootballClient,
    ApiFootballPlanError,
    ApiFootballQuotaError,
    detect_channel,
)


def test_client_rotation():
    client = ApiFootballClient(api_keys=["key1", "key2", "key3"])
    assert client.get_current_key() == "key1"
    client.rotate_key()
    assert client.get_current_key() == "key2"
    client.rotate_key()
    assert client.get_current_key() == "key3"
    client.rotate_key()
    assert client.get_current_key() == "key1"


class _FakeResponse(io.BytesIO):
    """Minimal stand-in for the object urlopen yields as a context manager."""

    def __init__(self, payload: dict):
        super().__init__(json.dumps(payload).encode("utf-8"))
        self.headers: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False


def _client_answering(monkeypatch, payload: dict) -> ApiFootballClient:
    client = ApiFootballClient(api_keys=["key1"], requests_per_minute=6000)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None: _FakeResponse(payload),
    )
    return client


def test_rejected_key_raises_instead_of_reporting_no_data(monkeypatch):
    """API-Sports answers HTTP 200 with errors.token when the key is refused.

    Treating that as an empty result is what let run 33989389927 report
    success while collecting nothing at all.
    """
    payload = {
        "response": [],
        "results": 0,
        "errors": {
            "token": "Error/Missing application key.",
        },
    }
    client = _client_answering(monkeypatch, payload)

    with pytest.raises(ApiFootballAuthError):
        client.get("teams", {"id": 7780})


def test_payload_error_raises_instead_of_reporting_no_data(monkeypatch):
    """Any other errors payload is a failed request, not an empty answer."""
    payload = {
        "response": [],
        "results": 0,
        "errors": {"plan": "Free plans do not have access to this season."},
    }
    client = _client_answering(monkeypatch, payload)

    with pytest.raises(RuntimeError):
        client.get("standings", {"league": 662, "season": 2026})


def test_genuinely_empty_answer_is_returned(monkeypatch):
    """An unknown entity answers with no errors, and that is a real result."""
    payload = {"response": [], "results": 0, "errors": []}
    client = _client_answering(monkeypatch, payload)

    assert client.get("teams", {"id": 999999}) == payload


def test_http_401_raises_the_same_auth_error_as_a_refused_payload(monkeypatch):
    """A refused key is one condition, so it gets one exception type.

    API-Sports signals refusal both ways: HTTP 200 with errors.token, and a
    bare 401/403. Callers that catch the specific error should not miss half
    of them.
    """
    client = ApiFootballClient(api_keys=["key1"], requests_per_minute=6000)

    def _refuse(request, timeout=None):
        raise urllib.error.HTTPError(
            url="https://v3.football.api-sports.io/status",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("urllib.request.urlopen", _refuse)

    with pytest.raises(ApiFootballAuthError):
        client.get("status")


def test_http_403_is_not_retried(monkeypatch):
    """Repeating a refused request cannot change the answer."""
    client = ApiFootballClient(api_keys=["key1"], requests_per_minute=6000)
    attempts = []

    def _refuse(request, timeout=None):
        attempts.append(1)
        raise urllib.error.HTTPError(
            url="https://v3.football.api-sports.io/status",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("urllib.request.urlopen", _refuse)

    with pytest.raises(ApiFootballAuthError):
        client.get("status")

    assert len(attempts) == 1


def test_errors_plan_levanta_plan_error_com_atributos(monkeypatch):
    client = _client_answering(
        monkeypatch,
        {"errors": {"plan": "Free plans do not have access to this season"}, "response": []},
    )

    with pytest.raises(ApiFootballPlanError) as refusal:
        client.get("standings", {"league": 615, "season": 2026})

    assert refusal.value.endpoint == "standings"
    assert "Free plans" in refusal.value.detail


def test_detect_channel_pelo_formato_da_chave():
    """O canal é decidível localmente, sem gastar requisição para descobrir."""
    assert detect_channel("a" * 32) == "apisports"
    assert detect_channel("0123456789abcdef0123456789abcdef") == "apisports"
    assert detect_channel("d7" + "x" * 48) == "rapidapi"
    assert detect_channel("") == "rapidapi"


def test_chave_rapidapi_usa_host_e_header_do_canal_certo(monkeypatch):
    """Apresentar chave da RapidAPI ao host direto é recusa garantida.

    Era o defeito que fazia a chave parecer suspensa: todo request do cron
    caía em errors.token porque ia ao canal que não a emitiu.
    """
    client = ApiFootballClient(api_keys=["k" * 50], requests_per_minute=6000)
    assert client.channel == "rapidapi"
    assert client.base_url == RAPIDAPI_BASE_URL

    seen = {}

    def _capture(request, timeout=None):
        seen["url"] = request.full_url
        seen["headers"] = dict(request.headers)
        return _FakeResponse({"response": [], "errors": []})

    monkeypatch.setattr("urllib.request.urlopen", _capture)
    client.get("teams", {"id": 12946})

    assert seen["url"].startswith("https://api-football-v1.p.rapidapi.com/v3/teams")
    assert seen["headers"]["X-rapidapi-key"] == "k" * 50
    assert seen["headers"]["X-rapidapi-host"] == RAPIDAPI_HOST
    assert "X-apisports-key" not in seen["headers"]


def test_chave_apisports_mantem_canal_direto(monkeypatch):
    client = ApiFootballClient(api_keys=["a" * 32], requests_per_minute=6000)
    assert client.channel == "apisports"

    seen = {}

    def _capture(request, timeout=None):
        seen["headers"] = dict(request.headers)
        return _FakeResponse({"response": [], "errors": []})

    monkeypatch.setattr("urllib.request.urlopen", _capture)
    client.get("status")

    assert seen["headers"]["X-apisports-key"] == "a" * 32
    assert "X-rapidapi-key" not in seen["headers"]


def test_cota_diaria_esgotada_nao_e_repetida(monkeypatch):
    """429 com reset em horas é cota do dia: insistir só atrai bloqueio."""
    client = ApiFootballClient(api_keys=["a" * 32], requests_per_minute=6000)
    attempts = []

    def _refuse(request, timeout=None):
        attempts.append(1)
        raise urllib.error.HTTPError(
            url="https://v3.football.api-sports.io/teams",
            code=429,
            msg="Too Many Requests",
            hdrs={"x-ratelimit-requests-reset": "29829"},
            fp=None,
        )

    monkeypatch.setattr("urllib.request.urlopen", _refuse)

    with pytest.raises(ApiFootballQuotaError) as esgotada:
        client.get("teams", {"id": 12946})

    assert len(attempts) == 1
    assert esgotada.value.reset_seconds == 29829


def test_teto_por_execucao_impede_gastar_a_cota_do_dia(monkeypatch):
    """Nenhuma execução isolada pode consumir o orçamento diário inteiro."""
    client = ApiFootballClient(api_keys=["a" * 32], requests_per_minute=6000, run_budget=2)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None: _FakeResponse({"response": [], "errors": []}),
    )

    client.get("teams", {"id": 1})
    client.get("teams", {"id": 2})

    with pytest.raises(ApiFootballQuotaError):
        client.get("teams", {"id": 3})


def test_headers_de_cota_ficam_visiveis_para_quem_chama(monkeypatch):
    """Saber quanto resta é o que permite decidir sem apanhar da API."""
    client = ApiFootballClient(api_keys=["a" * 32], requests_per_minute=6000)

    def _answer(request, timeout=None):
        response = _FakeResponse({"response": [], "errors": []})
        response.headers = {
            "x-ratelimit-requests-limit": "100",
            "x-ratelimit-requests-remaining": "7",
        }
        return response

    monkeypatch.setattr("urllib.request.urlopen", _answer)
    client.get("teams", {"id": 1})

    assert client.daily_limit == 100
    assert client.daily_remaining == 7

    # Com a cota zerada nos headers, a próxima pergunta nem sai.
    client.daily_remaining = 0
    with pytest.raises(ApiFootballQuotaError):
        client.get("teams", {"id": 2})
