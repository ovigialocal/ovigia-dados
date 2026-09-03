from __future__ import annotations

from typing import Any

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
