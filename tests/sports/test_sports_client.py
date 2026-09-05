import io
import json

import pytest

from ovigia_dados.sports.client import ApiFootballAuthError, ApiFootballClient


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
