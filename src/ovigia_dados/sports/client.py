"""Cliente HTTP resiliente e econômico para a API-Football v3.

A mesma assinatura é vendida por dois canais com host, header e prefixo de
caminho próprios: direto (API-Sports) e RapidAPI. Uma chave só é reconhecida
no canal onde foi emitida, e apresentá-la ao canal errado produz exatamente o
mesmo `errors.token` de uma chave inválida. Repetir isso em cron diário é o
que faz uma chave saudável parecer suspensa e o que atrai bloqueio de fato.

Cadência e retry são delegados a bibliotecas — `pyrate-limiter` e `tenacity`.
O que este módulo escreve é só a política: quantas requisições por minuto,
quanto esperar depois de um 429 e quando desistir. Limitador caseiro erra
justamente nos casos que importam aqui.
"""

import logging
import os
import random
from typing import Any
from urllib.parse import urlparse

from pyrate_limiter import Duration, InMemoryBucket, Limiter, Rate
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
)

import requests

logger = logging.getLogger(__name__)

API_BASE_URL = "https://v3.football.api-sports.io"
RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}/v3"
DEFAULT_USER_AGENT = (
    "OVigiaDados/0.1.0 (+https://github.com/ovigialocal/ovigia-dados; contato@ovigia.local)"
)

# O plano gratuito dá 100 requisições por dia em qualquer canal. Um run que
# possa gastar as 100 deixa o dia seguinte sem margem para reprocessar nada.
DEFAULT_RUN_BUDGET = 60

# Requisições por minuto. O plano gratuito documenta 10 no canal direto; a
# RapidAPI não publica o limite por minuto em header nenhum, então o número
# conservador vale para os dois. Não vale descobrir o teto empiricamente:
# cada tentativa de descobrir é uma requisição recusada a mais no histórico
# da conta.
DEFAULT_REQUESTS_PER_MINUTE = 10

# Piso de requisições que a execução nunca consome. Chegar a zero é o que
# antecede a rajada de 429 — e é a rajada, não o esgotamento, que motiva
# bloqueio.
DEFAULT_DAILY_RESERVE = 10

# Espera após 429 sem header de reset. O limite por minuto só zera quando o
# minuto passa; repetir antes disso gasta requisição para colher a mesma
# recusa e engorda o histórico de abuso da chave.
RATE_LIMIT_COOLDOWN_SECONDS = 60.0

# Reset diário vem em horas. Acima deste corte, nenhum retry resolve.
DAILY_RESET_THRESHOLD_SECONDS = 120


class ApiFootballAuthError(PermissionError):
    """A chave foi recusada pela API-Football."""


class ApiFootballPlanError(RuntimeError):
    """O plano da assinatura não cobre o recurso pedido.

    Distinta das demais recusas porque não é defeito nem falha de
    infraestrutura: é o contrato do plano. Quem chama decide se o recurso é
    essencial ou se a coleta segue sem ele.
    """

    def __init__(self, endpoint: str, errors: dict[str, Any]):
        self.endpoint = endpoint
        self.detail = str(errors.get("plan", ""))
        super().__init__(f"Plano da API-Football não cobre {endpoint}: {self.detail}")


class ApiFootballQuotaError(RuntimeError):
    """A cota acabou. Insistir agora é o comportamento que gera bloqueio.

    Separada de erro de rede porque não há retry que a resolva: só o reset
    diário devolve o direito de perguntar.
    """

    def __init__(self, endpoint: str, detail: str, reset_seconds: int | None = None):
        self.endpoint = endpoint
        self.reset_seconds = reset_seconds
        super().__init__(f"Cota da API-Football esgotada em {endpoint}: {detail}")


class _TransientRateLimit(RuntimeError):
    """Limite por minuto: passa sozinho quando o minuto vira."""


class _TransientTransport(RuntimeError):
    """Falha de rede ou 5xx: repetir pode resolver."""


def _payload_errors(data: dict[str, Any]) -> dict[str, Any]:
    """Normaliza o campo errors, que vem como lista vazia quando não há erro."""
    errors = data.get("errors")
    return errors if isinstance(errors, dict) else {}


def detect_channel(api_key: str) -> str:
    """Descobre o canal pelo formato da chave, sem gastar requisição.

    O único formato que identifica positivamente é o da API-Sports: 32
    caracteres hexadecimais. A RapidAPI não emite um formato único — a chave
    de 50 alfanuméricos é a mais comum, mas o secret em produção neste
    repositório tem 32 caracteres não hexadecimais e é aceito lá. Por isso a
    regra é "hexadecimal de 32 é direto, o resto é RapidAPI", e não uma
    dicotomia entre dois formatos conhecidos.

    Errar aqui não é silencioso: o canal escolhido aparece no log e na
    mensagem de recusa, que é o que faltava para distinguir chave inválida
    de chave no canal errado.
    """
    key = (api_key or "").strip()
    if len(key) == 32 and all(c in "0123456789abcdefABCDEF" for c in key):
        return "apisports"
    return "rapidapi"


def build_limiter(requests_per_minute: int) -> Limiter:
    """Monta o limitador com as duas taxas que a política exige.

    Duas, porque uma só não basta. A taxa por minuto é o limite que a API
    conta; a taxa por intervalo espalha as requisições dentro do minuto, em
    vez de disparar as dez de uma vez e ficar cinquenta segundos calado —
    rajada é a forma mais fácil de esbarrar em guarda por segundo que
    ninguém documenta.
    """
    rates = [Rate(requests_per_minute, Duration.MINUTE)]

    # A biblioteca exige que taxas empilhadas tenham densidade não crescente,
    # e é bom que exija: uma taxa de espaçamento mais permissiva que o teto
    # do minuto não espaça nada. Acima de uma por segundo o espaçamento não
    # cabe em segundos inteiros, e aí a taxa do minuto responde sozinha.
    spacing = 60 // max(1, requests_per_minute)
    if spacing >= 1 and requests_per_minute > 1:
        rates.insert(0, Rate(1, Duration.SECOND * spacing))

    return Limiter(InMemoryBucket(rates), buffer_ms=50)


def _wait_policy(retry_state: RetryCallState) -> float:
    """Quanto esperar antes de repetir, conforme o motivo da recusa.

    O jitter existe porque cadência perfeitamente periódica vinda de IP de CI
    é assinatura de robô, e custa segundos remover.
    """
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number
    if isinstance(exception, _TransientRateLimit):
        base = RATE_LIMIT_COOLDOWN_SECONDS * attempt
    else:
        base = 2.0 * attempt
    return base + random.uniform(0.0, 0.3 * base)


class ApiFootballClient:
    """Cliente ciente de canal e de cota, com teto de gasto por execução."""

    def __init__(
        self,
        api_keys: list[str] | None = None,
        base_url: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        channel: str = "auto",
        run_budget: int = DEFAULT_RUN_BUDGET,
        daily_reserve: int = DEFAULT_DAILY_RESERVE,
        session: requests.Session | None = None,
    ):
        if api_keys is None:
            raw_key = (
                os.environ.get("API_FOOTBALL_KEY") or os.environ.get("API_FOOTBALL_KEYS") or ""
            )
            api_keys = [k.strip() for k in raw_key.replace(",", ";").split(";") if k.strip()]

        self.api_keys = api_keys
        self.timeout = timeout
        self.max_retries = max_retries
        self.requests_per_minute = requests_per_minute
        self.run_budget = run_budget
        self.daily_reserve = daily_reserve
        self._current_key_idx = 0
        self.requests_made = 0
        self.session = session or requests.Session()
        self.limiter = build_limiter(requests_per_minute)
        # Preenchidos pelos headers de cada resposta: é a única leitura
        # confiável de quanto ainda resta, e sai do DEBUG porque orçamento
        # que ninguém vê não é orçamento.
        self.daily_limit: int | None = None
        self.daily_remaining: int | None = None

        if channel == "auto":
            channel = detect_channel(api_keys[0]) if api_keys else "apisports"
        if channel not in ("apisports", "rapidapi"):
            msg = f"canal desconhecido: {channel!r}"
            raise ValueError(msg)
        self.channel = channel

        default_base = RAPIDAPI_BASE_URL if channel == "rapidapi" else API_BASE_URL
        self.base_url = (base_url or default_base).rstrip("/")

    def get_current_key(self) -> str:
        if not self.api_keys:
            raise ValueError("Nenhuma API_FOOTBALL_KEY configurada.")
        return self.api_keys[self._current_key_idx % len(self.api_keys)]

    def rotate_key(self):
        """Troca para outra chave configurada.

        Nunca chamada em resposta a rate limit: girar chaves para escapar do
        limite de uma conta é justamente o padrão que motiva suspensão. Serve
        só para trocar uma credencial que o operador já sabe estar quebrada.
        """
        if len(self.api_keys) > 1:
            self._current_key_idx = (self._current_key_idx + 1) % len(self.api_keys)
            logger.info(f"Rotacionada API_FOOTBALL_KEY para chave index={self._current_key_idx}")

    def _headers(self) -> dict[str, str]:
        key = self.get_current_key()
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }
        if self.channel == "rapidapi":
            headers["x-rapidapi-key"] = key
            headers["x-rapidapi-host"] = urlparse(self.base_url).netloc
        else:
            headers["x-apisports-key"] = key
        return headers

    def _read_quota(self, headers: Any) -> int | None:
        """Lê os headers de cota e devolve o reset diário em segundos."""

        def _int(name: str) -> int | None:
            raw = headers.get(name) if headers else None
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        limit = _int("x-ratelimit-requests-limit")
        remaining = _int("x-ratelimit-requests-remaining")
        if limit is not None:
            self.daily_limit = limit
        if remaining is not None:
            self.daily_remaining = remaining
            logger.info(
                "Cota API-Football: %s de %s requisições restantes hoje",
                remaining,
                limit if limit is not None else "?",
            )
        return _int("x-ratelimit-requests-reset")

    def _attempt(self, endpoint: str, url: str, params: dict[str, Any] | None) -> dict[str, Any]:
        """Uma requisição: devolve o payload ou levanta a recusa que couber."""
        # O limitador segura aqui, antes de a requisição existir. Bloqueante
        # de propósito: a alternativa é decidir por conta própria o que fazer
        # com um "não pode agora", que é a decisão que se erra.
        self.limiter.try_acquire("api-football", blocking=True)

        self.requests_made += 1
        try:
            response = self.session.get(
                url, params=params, headers=self._headers(), timeout=self.timeout
            )
        except requests.RequestException as failure:
            raise _TransientTransport(f"Erro de conexão ao acessar {endpoint}: {failure}") from None

        reset = self._read_quota(response.headers)

        if response.status_code == 429:
            # Reset em horas é cota diária: não há retry que a devolva, e
            # continuar tentando é o que transforma limite em bloqueio.
            if reset is not None and reset > DAILY_RESET_THRESHOLD_SECONDS:
                raise ApiFootballQuotaError(
                    endpoint,
                    f"cota diária esgotada, reset em {reset}s",
                    reset_seconds=reset,
                )
            raise _TransientRateLimit(f"HTTP 429 em {endpoint}")

        if response.status_code in (401, 403):
            raise ApiFootballAuthError(
                f"Chave recusada no canal '{self.channel}' ({self.base_url}): "
                "inválida, não assinante deste canal ou sem permissão para o recurso."
            )

        if response.status_code >= 500:
            raise _TransientTransport(f"HTTP {response.status_code} ao acessar {endpoint}")

        response.raise_for_status()
        data = response.json()

        errors = _payload_errors(data)
        if errors.get("rateLimit"):
            raise _TransientRateLimit(f"Limite por minuto em {endpoint}: {errors['rateLimit']}")

        # A API responde HTTP 200 com errors preenchido. Tratar isso como
        # resposta vazia faz o pipeline reportar sucesso sem ter coletado
        # nada, que é indistinguível de um dia sem jogo.
        if errors.get("token"):
            raise ApiFootballAuthError(
                f"Chave recusada pela API-Football ao acessar {endpoint} "
                f"no canal '{self.channel}' ({self.base_url}): {errors['token']}. "
                "Uma chave só vale no canal que a emitiu — confira se a chave "
                "é da API-Sports (32 hex) ou da RapidAPI (50 alfanuméricos)."
            )

        if errors.get("plan"):
            raise ApiFootballPlanError(endpoint, errors)

        if errors:
            raise RuntimeError(f"API-Football recusou a requisição a {endpoint}: {errors}")

        return data

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa requisição GET ao endpoint da API-Football v3."""
        if self.requests_made >= self.run_budget:
            raise ApiFootballQuotaError(
                endpoint,
                f"teto de {self.run_budget} requisições por execução atingido",
            )
        if self.daily_remaining is not None and self.daily_remaining <= self.daily_reserve:
            raise ApiFootballQuotaError(
                endpoint,
                f"restam {self.daily_remaining} requisições e a reserva é "
                f"{self.daily_reserve}: a execução para antes de zerar a cota",
            )

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        retrying = Retrying(
            retry=retry_if_exception_type((_TransientRateLimit, _TransientTransport)),
            wait=_wait_policy,
            stop=stop_after_attempt(self.max_retries),
            reraise=True,
            before_sleep=lambda state: logger.warning(
                "Repetindo %s em %.0fs: %s",
                endpoint,
                state.next_action.sleep if state.next_action else 0,
                state.outcome.exception() if state.outcome else "",
            ),
        )

        try:
            return retrying(self._attempt, endpoint, url, params)
        except _TransientRateLimit as limited:
            # Esgotadas as tentativas, o limite deixou de ser transitório.
            raise ApiFootballQuotaError(endpoint, str(limited)) from limited
        except _TransientTransport as failure:
            raise RuntimeError(str(failure)) from failure
