"""Clientes HTTP mínimos para as fontes oficiais de dados de Porto Velho."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

CKAN_BASE_URL = "https://dados.portovelho.ro.gov.br/api/3/action"
PMPV_API_BASE_URL = "https://api.portovelho.ro.gov.br/api/v1"
DEFAULT_TIMEOUT = 30

LICITACAO_FILTERS = frozenset(
    {
        "titulo",
        "objeto",
        "processo",
        "edital",
        "data_acolhimento_inicio",
        "data_acolhimento_fim",
        "data_propostas_abertura",
        "data_publicacao",
        "data_publicacao_ratificacao",
        "data_disputa",
        "ano",
        "tipo.nome",
        "modalidade.nome",
        "classificacao.nome",
        "situacao.nome",
    }
)


class PortoVelhoCkanClient:
    """Cliente fino para a Action API do CKAN municipal."""

    def __init__(
        self,
        *,
        base_url: str = CKAN_BASE_URL,
        session: requests.Session | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def action(self, name: str, **params: Any) -> Any:
        """Executa uma action CKAN e devolve somente o campo ``result``."""
        response = self.session.get(
            f"{self.base_url}/{name}",
            params=params or None,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is not True:
            raise ValueError(f"CKAN action {name!r} returned success=false")
        return payload["result"]

    def list_datasets(self) -> list[str]:
        """Lista os identificadores dos datasets publicados no catálogo."""
        return list(self.action("package_list"))

    def search_datasets(self, query: str, *, rows: int = 100, start: int = 0) -> dict[str, Any]:
        """Pesquisa o catálogo por texto usando ``package_search``."""
        return dict(self.action("package_search", q=query, rows=rows, start=start))

    def dataset(self, dataset_id: str) -> dict[str, Any]:
        """Obtém metadados e recursos de um dataset pelo identificador CKAN."""
        return dict(self.action("package_show", id=dataset_id))

    def datastore_search(
        self,
        resource_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        """Consulta um recurso CKAN DataStore quando o recurso oferecer essa interface."""
        params: dict[str, Any] = {
            "resource_id": resource_id,
            "limit": limit,
            "offset": offset,
        }
        if filters:
            import json

            params["filters"] = json.dumps(filters, ensure_ascii=False, sort_keys=True)
        if q:
            params["q"] = q
        return dict(self.action("datastore_search", **params))


class PortoVelhoApiClient:
    """Cliente para rotas observadas da API oficial PMPV v1.

    Novos paths específicos só devem ganhar métodos quando estiverem sustentados pela
    documentação oficial ou por resposta observada. ``get`` continua disponível para
    investigação de rotas já verificadas sem obrigar uma modelagem prematura.
    """

    def __init__(
        self,
        *,
        base_url: str = PMPV_API_BASE_URL,
        bearer_token: str | None = None,
        session: requests.Session | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.headers = {"Accept": "application/json"}
        if bearer_token:
            self.headers["Authorization"] = f"Bearer {bearer_token}"

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        accept: str | None = None,
    ) -> requests.Response:
        """Faz GET em um path relativo da API preservando resposta bruta para auditoria."""
        headers = dict(self.headers)
        if accept:
            headers["Accept"] = accept
        response = self.session.get(
            f"{self.base_url}/{path.lstrip('/')}",
            params=params,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        """Faz GET e desserializa resposta JSON."""
        return self.get(path, params=params).json()

    def list_contracts(
        self,
        *,
        ano: int | None = None,
        secretaria: str | int | None = None,
        modelo: str | int | None = None,
        vigencia: str | None = None,
        classificacao: str | int | None = None,
        por_pagina: int | None = None,
        contratante: str | int | None = None,
        situacao: str | int | None = None,
        categoria: str | int | None = None,
    ) -> Any:
        """Lista contratos pela rota pública ``GET /contratos`` documentada no CKAN."""
        params = {
            "ano": ano,
            "secretaria": secretaria,
            "modelo": modelo,
            "vigencia": vigencia,
            "classificacao": classificacao,
            "por-pagina": por_pagina,
            "contratante": contratante,
            "situacao": situacao,
            "categoria": categoria,
        }
        clean_params = {key: value for key, value in params.items() if value is not None}
        return self.get_json("contratos", params=clean_params)

    def _normalize_pagination_url(self, next_url: str) -> str:
        """Mantém paginação dentro da API e corrige apenas o downgrade HTTP observado."""
        base = urlsplit(self.base_url)
        candidate = urlsplit(next_url)
        base_path = base.path.rstrip("/")

        same_authority = (
            candidate.hostname == base.hostname
            and candidate.port == base.port
            and candidate.username is None
            and candidate.password is None
        )
        same_api_root = candidate.path == base_path or candidate.path.startswith(f"{base_path}/")
        same_scheme = candidate.scheme == base.scheme
        observed_http_downgrade = base.scheme == "https" and candidate.scheme == "http"

        if not (same_authority and same_api_root and (same_scheme or observed_http_downgrade)):
            raise ValueError(f"PMPV pagination link escaped configured API base: {next_url!r}")

        if observed_http_downgrade:
            return urlunsplit((base.scheme, base.netloc, candidate.path, candidate.query, ""))
        return next_url

    def iter_contract_pages(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Segue a paginação observada de ``GET /contratos`` por ``links.next``.

        O método não inventa um parâmetro de página. Depois da primeira consulta segue
        somente ``links.next`` da própria API. A fonte foi observada emitindo links
        ``http://`` para a mesma raiz servida em HTTPS; esse caso é promovido para
        HTTPS, enquanto qualquer mudança de autoridade ou raiz da API falha fechado.
        """
        payload = self.list_contracts(**params)
        while True:
            if not isinstance(payload, dict):
                raise ValueError("PMPV /contratos response must be an object")
            yield payload

            links = payload.get("links")
            next_url = links.get("next") if isinstance(links, dict) else None
            if not next_url:
                return
            if not isinstance(next_url, str):
                raise ValueError(f"PMPV pagination link must be a string: {next_url!r}")
            safe_next_url = self._normalize_pagination_url(next_url)

            response = self.session.get(
                safe_next_url,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()

    def list_licitations(
        self,
        *,
        sort: str = "-id",
        por_pagina: int = 10,
        filters: dict[str, str] | None = None,
    ) -> Any:
        """Lista licitações pela rota pública ``GET /licitacoes`` documentada no CKAN."""
        params: dict[str, Any] = {"sort": sort, "por-pagina": por_pagina}
        for name, value in (filters or {}).items():
            if name not in LICITACAO_FILTERS:
                raise ValueError(f"undocumented licitacao filter: {name}")
            params[f"filter[{name}]"] = value
        return self.get_json("licitacoes", params=params)
