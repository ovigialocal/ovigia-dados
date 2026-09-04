from __future__ import annotations

from typing import Any

import pytest

from ovigia_dados.connectors.porto_velho import PortoVelhoApiClient, PortoVelhoCkanClient


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


def test_ckan_lists_datasets_and_uses_action_api() -> None:
    session = FakeSession([FakeResponse({"success": True, "result": ["contratos", "empenhos"]})])
    client = PortoVelhoCkanClient(session=session)

    assert client.list_datasets() == ["contratos", "empenhos"]
    assert session.calls[0]["url"].endswith("/api/3/action/package_list")


def test_ckan_datastore_serializes_filters() -> None:
    session = FakeSession([FakeResponse({"success": True, "result": {"records": []}})])
    client = PortoVelhoCkanClient(session=session)

    client.datastore_search("resource-1", filters={"ano": 2026}, limit=50)

    params = session.calls[0]["params"]
    assert params["resource_id"] == "resource-1"
    assert params["limit"] == 50
    assert params["filters"] == '{"ano": 2026}'


def test_pmpv_api_builds_relative_url_and_optional_bearer() -> None:
    session = FakeSession([FakeResponse({"ok": True})])
    client = PortoVelhoApiClient(session=session, bearer_token="token-de-teste")

    assert client.get_json("contratos", params={"ano": 2026}) == {"ok": True}
    call = session.calls[0]
    assert call["url"] == "https://api.portovelho.ro.gov.br/api/v1/contratos"
    assert call["headers"]["Authorization"] == "Bearer token-de-teste"
    assert call["params"] == {"ano": 2026}


def test_pmpv_api_does_not_require_bearer_for_public_route() -> None:
    session = FakeSession([FakeResponse({"ok": True})])
    client = PortoVelhoApiClient(session=session)

    client.get_json("publico")

    assert "Authorization" not in session.calls[0]["headers"]


def test_pmpv_api_lists_contracts_with_only_documented_filters() -> None:
    payload = {"data": [{"id": 42, "valor": {"value": 1000}}]}
    session = FakeSession([FakeResponse(payload)])
    client = PortoVelhoApiClient(session=session)

    result = client.list_contracts(
        ano=2026,
        secretaria="SEINFRA",
        por_pagina=50,
        situacao="vigente",
    )

    assert result == payload
    call = session.calls[0]
    assert call["url"] == "https://api.portovelho.ro.gov.br/api/v1/contratos"
    assert call["params"] == {
        "ano": 2026,
        "secretaria": "SEINFRA",
        "por-pagina": 50,
        "situacao": "vigente",
    }


def test_pmpv_api_follows_contract_pagination_links() -> None:
    second_url = "https://api.portovelho.ro.gov.br/api/v1/contratos?page=2"
    session = FakeSession(
        [
            FakeResponse({"data": [{"id": 1}], "links": {"next": second_url}}),
            FakeResponse({"data": [{"id": 2}], "links": {"next": None}}),
        ]
    )
    client = PortoVelhoApiClient(session=session)

    pages = list(client.iter_contract_pages(ano=2026, por_pagina=100))

    assert [page["data"][0]["id"] for page in pages] == [1, 2]
    assert session.calls[0]["params"] == {"ano": 2026, "por-pagina": 100}
    assert session.calls[1]["url"] == second_url
    assert session.calls[1]["headers"] == {"Accept": "application/json"}


def test_pmpv_api_upgrades_observed_http_pagination_link() -> None:
    observed_next = "http://api.portovelho.ro.gov.br/api/v1/contratos?page=2"
    expected_next = "https://api.portovelho.ro.gov.br/api/v1/contratos?page=2"
    session = FakeSession(
        [
            FakeResponse({"data": [{"id": 1}], "links": {"next": observed_next}}),
            FakeResponse({"data": [{"id": 2}], "links": {"next": None}}),
        ]
    )
    client = PortoVelhoApiClient(session=session)

    pages = list(client.iter_contract_pages(por_pagina=100))

    assert [page["data"][0]["id"] for page in pages] == [1, 2]
    assert session.calls[1]["url"] == expected_next


def test_pmpv_api_rejects_pagination_link_outside_configured_base() -> None:
    session = FakeSession(
        [FakeResponse({"data": [], "links": {"next": "https://example.org/contratos?page=2"}})]
    )
    client = PortoVelhoApiClient(session=session)

    with pytest.raises(ValueError, match="escaped configured API base"):
        list(client.iter_contract_pages())


def test_pmpv_api_rejects_pagination_link_outside_api_root() -> None:
    session = FakeSession(
        [
            FakeResponse(
                {
                    "data": [],
                    "links": {"next": "http://api.portovelho.ro.gov.br/outro?page=2"},
                }
            )
        ]
    )
    client = PortoVelhoApiClient(session=session)

    with pytest.raises(ValueError, match="escaped configured API base"):
        list(client.iter_contract_pages())


def test_pmpv_api_lists_licitations_with_documented_filters() -> None:
    payload = {"data": [{"id": 8678}]}
    session = FakeSession([FakeResponse(payload)])
    client = PortoVelhoApiClient(session=session)

    result = client.list_licitations(
        por_pagina=25,
        filters={"processo": "005.002970/2026-47", "ano": "2026"},
    )

    assert result == payload
    call = session.calls[0]
    assert call["url"] == "https://api.portovelho.ro.gov.br/api/v1/licitacoes"
    assert call["params"] == {
        "sort": "-id",
        "por-pagina": 25,
        "filter[processo]": "005.002970/2026-47",
        "filter[ano]": "2026",
    }


def test_pmpv_api_rejects_undocumented_licitation_filter() -> None:
    client = PortoVelhoApiClient(session=FakeSession([]))

    with pytest.raises(ValueError, match="undocumented licitacao filter"):
        client.list_licitations(filters={"id": "8678"})
