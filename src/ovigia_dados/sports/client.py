"""Cliente HTTP resiliente e econômico para a API-Football v3.

A mesma assinatura é vendida por dois canais com host, header e prefixo de
caminho próprios: direto (API-Sports) e RapidAPI. Uma chave só é reconhecida
no canal onde foi emitida, e apresentá-la ao canal errado produz exatamente o
mesmo `errors.token` de uma chave inválida. Repetir isso em cron diário é o
que faz uma chave saudável parecer suspensa e o que atrai bloqueio de fato.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

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


def _payload_errors(data: dict[str, Any]) -> dict[str, Any]:
    """Normaliza o campo errors, que vem como lista vazia quando não há erro."""
    errors = data.get("errors")
    return errors if isinstance(errors, dict) else {}


def detect_channel(api_key: str) -> str:
    """Descobre o canal pelo formato da chave, sem gastar requisição.

    Chave emitida pela API-Sports tem 32 caracteres hexadecimais; a da
    RapidAPI tem 50 alfanuméricos. O formato é decidível localmente, e usar
    isso evita a rodada de descoberta que gastava cota para redescobrir todo
    dia a mesma coisa.
    """
    key = (api_key or "").strip()
    if len(key) == 32 and all(c in "0123456789abcdefABCDEF" for c in key):
        return "apisports"
    return "rapidapi"


class ApiFootballClient:
    """Cliente ciente de canal e de cota, com teto de gasto por execução."""

    def __init__(
        self,
        api_keys: list[str] | None = None,
        base_url: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        requests_per_minute: int = 10,
        channel: str = "auto",
        run_budget: int = DEFAULT_RUN_BUDGET,
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
        self._current_key_idx = 0
        self._last_request_time = 0.0
        self.requests_made = 0
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
            headers["x-rapidapi-host"] = urllib.parse.urlparse(self.base_url).netloc
        else:
            headers["x-apisports-key"] = key
        return headers

    def _rate_limit_throttle(self):
        min_interval = 60.0 / float(self.requests_per_minute)
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def _read_quota(self, headers: Any) -> int | None:
        """Lê os headers de cota e devolve o reset diário em segundos."""

        def _int(name: str) -> int | None:
            raw = headers.get(name)
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

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa requisição GET ao endpoint da API-Football v3."""
        if self.requests_made >= self.run_budget:
            raise ApiFootballQuotaError(
                endpoint,
                f"teto de {self.run_budget} requisições por execução atingido",
            )
        if self.daily_remaining is not None and self.daily_remaining <= 0:
            raise ApiFootballQuotaError(endpoint, "cota diária zerada segundo os headers")

        query_str = ""
        if params:
            query_str = "?" + urllib.parse.urlencode(params)

        url = f"{self.base_url}/{endpoint.lstrip('/')}{query_str}"

        for attempt in range(1, self.max_retries + 1):
            self._rate_limit_throttle()
            req = urllib.request.Request(url, headers=self._headers())
            try:
                self.requests_made += 1
                with urllib.request.urlopen(req, timeout=self.timeout) as res:
                    self._read_quota(res.headers)

                    body = res.read().decode("utf-8")
                    data = json.loads(body)

                    errors = _payload_errors(data)
                    if errors.get("rateLimit"):
                        # Limite por minuto: esperar resolve, insistir rápido não.
                        if attempt >= self.max_retries:
                            raise ApiFootballQuotaError(endpoint, str(errors["rateLimit"]))
                        logger.warning(
                            "Limite por minuto atingido em %s. Aguardando antes de repetir.",
                            endpoint,
                        )
                        time.sleep(60.0 / float(self.requests_per_minute) * attempt + 5.0)
                        continue

                    # A API responde HTTP 200 com errors preenchido. Tratar isso
                    # como resposta vazia faz o pipeline reportar sucesso sem
                    # ter coletado nada, que é indistinguível de um dia sem jogo.
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
                        raise RuntimeError(
                            f"API-Football recusou a requisição a {endpoint}: {errors}"
                        )

                    return data
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    reset = self._read_quota(e.headers) if e.headers else None
                    # Reset em horas é cota diária: não há retry que a devolva,
                    # e continuar tentando é o que transforma limite em bloqueio.
                    if reset is not None and reset > 120:
                        raise ApiFootballQuotaError(
                            endpoint,
                            f"cota diária esgotada, reset em {reset}s",
                            reset_seconds=reset,
                        ) from e
                    if attempt >= self.max_retries:
                        raise ApiFootballQuotaError(endpoint, "HTTP 429 persistente") from e
                    logger.warning(
                        "HTTP 429 em %s. Tentativa %s/%s após espera.",
                        endpoint,
                        attempt,
                        self.max_retries,
                    )
                    time.sleep(60.0 / float(self.requests_per_minute) * attempt + 5.0)
                    continue
                elif e.code in (401, 403):
                    logger.error(f"Erro de autenticação HTTP {e.code} na API-Football.")
                    raise ApiFootballAuthError(
                        f"Chave recusada no canal '{self.channel}' ({self.base_url}): "
                        "inválida, não assinante deste canal ou sem permissão para o recurso."
                    ) from e
                else:
                    logger.error(f"Erro HTTP {e.code} ao acessar {endpoint}: {e.reason}")
                    if attempt < self.max_retries:
                        time.sleep(2.0 * attempt)
                        continue
                    raise
            except (ApiFootballAuthError, ApiFootballQuotaError, RuntimeError):
                # A própria API recusou a requisição: repetir não muda a resposta.
                raise
            except Exception as ex:
                logger.error(f"Erro de conexão ao acessar {endpoint}: {ex}")
                if attempt < self.max_retries:
                    time.sleep(2.0 * attempt)
                    continue
                raise

        raise RuntimeError(f"Excedido número máximo de tentativas ao acessar {endpoint}")
