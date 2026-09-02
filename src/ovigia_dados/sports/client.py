"""Cliente HTTP resiliente e econômico para a API-Football v3."""

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
DEFAULT_USER_AGENT = (
    "OVigiaDados/0.1.0 (+https://github.com/ovigialocal/ovigia-dados; contato@ovigia.local)"
)


class ApiFootballClient:
    """Cliente com rotação de chaves, leitura de rate-limit headers e cache."""

    def __init__(
        self,
        api_keys: list[str] | None = None,
        base_url: str = API_BASE_URL,
        timeout: int = 30,
        max_retries: int = 3,
        requests_per_minute: int = 10,
    ):
        if api_keys is None:
            raw_key = (
                os.environ.get("API_FOOTBALL_KEY") or os.environ.get("API_FOOTBALL_KEYS") or ""
            )
            api_keys = [k.strip() for k in raw_key.replace(",", ";").split(";") if k.strip()]

        self.api_keys = api_keys
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.requests_per_minute = requests_per_minute
        self._current_key_idx = 0
        self._last_request_time = 0.0

    def get_current_key(self) -> str:
        if not self.api_keys:
            raise ValueError("Nenhuma API_FOOTBALL_KEY configurada.")
        return self.api_keys[self._current_key_idx % len(self.api_keys)]

    def rotate_key(self):
        if len(self.api_keys) > 1:
            self._current_key_idx = (self._current_key_idx + 1) % len(self.api_keys)
            logger.info(f"Rotacionada API_FOOTBALL_KEY para chave index={self._current_key_idx}")

    def _rate_limit_throttle(self):
        min_interval = 60.0 / float(self.requests_per_minute)
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa requisição GET ao endpoint da API-Football v3."""
        query_str = ""
        if params:
            query_str = "?" + urllib.parse.urlencode(params)

        url = f"{self.base_url}/{endpoint.lstrip('/')}{query_str}"

        for attempt in range(1, self.max_retries + 1):
            self._rate_limit_throttle()
            key = self.get_current_key()
            req = urllib.request.Request(
                url,
                headers={
                    "x-apisports-key": key,
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as res:
                    remaining_req = res.headers.get("x-ratelimit-requests-remaining")
                    if remaining_req:
                        logger.debug(f"API-Football requests restantes: {remaining_req}")

                    body = res.read().decode("utf-8")
                    data = json.loads(body)

                    errors = data.get("errors")
                    if errors and isinstance(errors, dict) and errors.get("rateLimit"):
                        logger.warning(
                            "Limite de requisições retornado no payload. Rotacionando/Aguardando..."
                        )
                        self.rotate_key()
                        time.sleep(2.0 * attempt)
                        continue

                    return data
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    logger.warning(
                        f"HTTP 429 Too Many Requests ao acessar {endpoint}. Tentativa {attempt}/{self.max_retries}..."
                    )
                    self.rotate_key()
                    time.sleep(5.0 * attempt)
                    continue
                elif e.code in (401, 403):
                    logger.error(f"Erro de autenticação HTTP {e.code} na API-Football.")
                    raise PermissionError(
                        "Chave de API inválida ou sem permissão para este recurso."
                    ) from e
                else:
                    logger.error(f"Erro HTTP {e.code} ao acessar {endpoint}: {e.reason}")
                    if attempt < self.max_retries:
                        time.sleep(2.0 * attempt)
                        continue
                    raise
            except Exception as ex:
                logger.error(f"Erro de conexão ao acessar {endpoint}: {ex}")
                if attempt < self.max_retries:
                    time.sleep(2.0 * attempt)
                    continue
                raise

        raise RuntimeError(f"Excedido número máximo de tentativas ao acessar {endpoint}")
