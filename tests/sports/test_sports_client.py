import time

import pytest

import requests
from ovigia_dados.sports.client import (
    RAPIDAPI_BASE_URL,
    RAPIDAPI_HOST,
    ApiFootballAuthError,
    ApiFootballClient,
    ApiFootballPlanError,
    ApiFootballQuotaError,
    build_limiter,
    detect_channel,
)


class _FakeResponse:
    """Stand-in mínimo para a resposta que requests devolve."""

    def __init__(self, payload: dict, status_code: int = 200, headers: dict | None = None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class _FakeSession:
    """Sessão que devolve respostas roteirizadas e guarda o que foi pedido."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        if not self._responses:
            raise AssertionError("requisição a mais do que o roteiro previa")
        answer = self._responses.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def _client(*responses, **kwargs) -> tuple[ApiFootballClient, _FakeSession]:
    """Cliente sem espera real: a cadência é testada à parte, com relógio."""
    session = _FakeSession(*responses)
    kwargs.setdefault("api_keys", ["a" * 32])
    kwargs.setdefault("requests_per_minute", 6000)
    return ApiFootballClient(session=session, **kwargs), session


def test_client_rotation():
    client = ApiFootballClient(api_keys=["key1", "key2", "key3"])
    assert client.get_current_key() == "key1"
    client.rotate_key()
    assert client.get_current_key() == "key2"
    client.rotate_key()
    assert client.get_current_key() == "key3"
    client.rotate_key()
    assert client.get_current_key() == "key1"


def test_rejected_key_raises_instead_of_reporting_no_data():
    """API-Sports answers HTTP 200 with errors.token when the key is refused.

    Treating that as an empty result is what let run 33989389927 report
    success while collecting nothing at all.
    """
    client, _ = _client(
        _FakeResponse(
            {"response": [], "results": 0, "errors": {"token": "Error/Missing application key."}}
        )
    )

    with pytest.raises(ApiFootballAuthError):
        client.get("teams", {"id": 7780})


def test_payload_error_raises_instead_of_reporting_no_data():
    """Any other errors payload is a failed request, not an empty answer."""
    client, _ = _client(
        _FakeResponse(
            {
                "response": [],
                "results": 0,
                "errors": {"plan": "Free plans do not have access to this season."},
            }
        )
    )

    with pytest.raises(RuntimeError):
        client.get("standings", {"league": 662, "season": 2026})


def test_genuinely_empty_answer_is_returned():
    """An unknown entity answers with no errors, and that is a real result."""
    payload = {"response": [], "results": 0, "errors": []}
    client, _ = _client(_FakeResponse(payload))

    assert client.get("teams", {"id": 999999}) == payload


def test_http_401_raises_the_same_auth_error_as_a_refused_payload():
    """A refused key is one condition, so it gets one exception type.

    API-Sports signals refusal both ways: HTTP 200 with errors.token, and a
    bare 401/403. Callers that catch the specific error should not miss half
    of them.
    """
    client, _ = _client(_FakeResponse({}, status_code=401))

    with pytest.raises(ApiFootballAuthError):
        client.get("status")


def test_http_403_is_not_retried():
    """Repeating a refused request cannot change the answer."""
    client, session = _client(_FakeResponse({}, status_code=403))

    with pytest.raises(ApiFootballAuthError):
        client.get("status")

    assert len(session.calls) == 1


def test_errors_plan_levanta_plan_error_com_atributos():
    client, _ = _client(
        _FakeResponse(
            {"errors": {"plan": "Free plans do not have access to this season"}, "response": []}
        )
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


def test_chave_rapidapi_usa_host_e_header_do_canal_certo():
    """Apresentar chave da RapidAPI ao host direto é recusa garantida.

    Era o defeito que fazia a chave parecer suspensa: todo request do cron
    caía em errors.token porque ia ao canal que não a emitiu.
    """
    client, session = _client(_FakeResponse({"response": [], "errors": []}), api_keys=["k" * 50])
    assert client.channel == "rapidapi"
    assert client.base_url == RAPIDAPI_BASE_URL

    client.get("teams", {"id": 12946})

    call = session.calls[0]
    assert call["url"] == f"{RAPIDAPI_BASE_URL}/teams"
    assert call["params"] == {"id": 12946}
    assert call["headers"]["x-rapidapi-key"] == "k" * 50
    assert call["headers"]["x-rapidapi-host"] == RAPIDAPI_HOST
    assert "x-apisports-key" not in call["headers"]


def test_chave_apisports_mantem_canal_direto():
    client, session = _client(_FakeResponse({"response": [], "errors": []}))
    assert client.channel == "apisports"

    client.get("status")

    assert session.calls[0]["headers"]["x-apisports-key"] == "a" * 32
    assert "x-rapidapi-key" not in session.calls[0]["headers"]


def test_cota_diaria_esgotada_nao_e_repetida():
    """429 com reset em horas é cota do dia: insistir só atrai bloqueio."""
    client, session = _client(
        _FakeResponse({}, status_code=429, headers={"x-ratelimit-requests-reset": "29829"})
    )

    with pytest.raises(ApiFootballQuotaError) as esgotada:
        client.get("teams", {"id": 12946})

    assert len(session.calls) == 1
    assert esgotada.value.reset_seconds == 29829


def test_teto_por_execucao_impede_gastar_a_cota_do_dia():
    """Nenhuma execução isolada pode consumir o orçamento diário inteiro."""
    client, _ = _client(
        _FakeResponse({"response": [], "errors": []}),
        _FakeResponse({"response": [], "errors": []}),
        run_budget=2,
    )

    client.get("teams", {"id": 1})
    client.get("teams", {"id": 2})

    with pytest.raises(ApiFootballQuotaError):
        client.get("teams", {"id": 3})


def test_headers_de_cota_ficam_visiveis_para_quem_chama():
    """Saber quanto resta é o que permite decidir sem apanhar da API."""
    client, _ = _client(
        _FakeResponse(
            {"response": [], "errors": []},
            headers={
                "x-ratelimit-requests-limit": "100",
                "x-ratelimit-requests-remaining": "70",
            },
        ),
        daily_reserve=10,
    )
    client.get("teams", {"id": 1})

    assert client.daily_limit == 100
    assert client.daily_remaining == 70


def test_execucao_para_antes_de_zerar_a_cota_do_dia():
    """Chegar a zero é o que antecede a rajada de 429 que motiva bloqueio."""
    client, _ = _client(
        _FakeResponse(
            {"response": [], "errors": []},
            headers={
                "x-ratelimit-requests-limit": "100",
                "x-ratelimit-requests-remaining": "10",
            },
        ),
        daily_reserve=10,
    )
    client.get("teams", {"id": 1})

    with pytest.raises(ApiFootballQuotaError, match="reserva"):
        client.get("teams", {"id": 2})


def test_429_transitorio_espera_o_minuto_virar(monkeypatch):
    """Repetir antes do minuto colhe a mesma recusa e engorda o histórico."""
    esperas: list[float] = []
    monkeypatch.setattr("tenacity.nap.time.sleep", esperas.append)

    client, session = _client(
        _FakeResponse({}, status_code=429, headers={}),
        _FakeResponse({}, status_code=429, headers={}),
        max_retries=2,
    )

    with pytest.raises(ApiFootballQuotaError):
        client.get("teams", {"id": 1})

    assert len(session.calls) == 2
    assert esperas and min(esperas) >= 60.0


def test_falha_de_rede_e_repetida_com_espera_curta(monkeypatch):
    """Rede é transitória de verdade: não merece o castigo do rate limit."""
    esperas: list[float] = []
    monkeypatch.setattr("tenacity.nap.time.sleep", esperas.append)

    payload = {"response": [{"team": {"id": 12946}}], "errors": []}
    client, _ = _client(
        requests.ConnectionError("boom"),
        _FakeResponse(payload),
        max_retries=3,
    )

    assert client.get("teams", {"id": 12946}) == payload
    assert esperas and max(esperas) < 60.0


def test_limitador_espalha_as_requisicoes_dentro_do_minuto():
    """Dez de uma vez e cinquenta segundos calado é rajada, não cadência.

    A taxa por minuto sozinha permite a rajada; a taxa de espaçamento é o
    que mantém o pipeline longe de qualquer guarda por segundo que a API
    não documenta.
    """
    limiter = build_limiter(requests_per_minute=10)

    inicio = time.monotonic()
    for _ in range(2):
        limiter.try_acquire("api-football", blocking=True)
    decorrido = time.monotonic() - inicio

    # 10/min significa uma a cada seis segundos, e o limitador segura mesmo.
    assert decorrido >= 5.5
