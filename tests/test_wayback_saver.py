from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from ovigia_dados.wayback.save import WaybackSaveResult, save_to_wayback


class FakeResponse:
    def __init__(
        self, *, status=200, headers=None, url="https://web.archive.org/save/https://example.com"
    ):
        self.status = status
        self.headers = headers or Message()
        self._url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self._url


def test_result_structure_accepts_verified_snapshot():
    res = WaybackSaveResult(
        url="https://example.com",
        status="verified",
        archive_url="https://web.archive.org/web/20260902120000/https://example.com",
        http_status=200,
        attempted=True,
        reached_archive=True,
    )
    assert res.status == "verified"
    assert res.reached_archive is True


def test_success_without_snapshot_location_never_fabricates_archive_url():
    with patch("ovigia_dados.wayback.save.urllib.request.urlopen", return_value=FakeResponse()):
        result = save_to_wayback("https://example.com", max_retries=1)

    assert result.status == "accepted_unverified"
    assert result.archive_url is None
    assert result.attempted is True
    assert result.reached_archive is True


def test_content_location_yields_verified_snapshot():
    headers = Message()
    headers["Content-Location"] = "/web/20260902120000/https://example.com"
    with patch(
        "ovigia_dados.wayback.save.urllib.request.urlopen",
        return_value=FakeResponse(headers=headers),
    ):
        result = save_to_wayback("https://example.com", max_retries=1)

    assert result.status == "verified"
    assert result.archive_url == "https://web.archive.org/web/20260902120000/https://example.com"


def test_dns_or_transport_failure_is_infrastructure_error_not_archive_failure():
    with (
        patch(
            "ovigia_dados.wayback.save.urllib.request.urlopen",
            side_effect=URLError("dns failure"),
        ),
        patch("ovigia_dados.wayback.save.time.sleep"),
    ):
        result = save_to_wayback("https://example.com", max_retries=1)

    assert result.status == "infrastructure_error"
    assert result.reached_archive is False
    assert result.archive_failure is False


def test_terminal_http_refusal_is_real_archive_failure():
    headers = Message()
    error = HTTPError(
        "https://web.archive.org/save/https://example.com",
        403,
        "Forbidden",
        headers,
        None,
    )
    with patch("ovigia_dados.wayback.save.urllib.request.urlopen", side_effect=error):
        result = save_to_wayback("https://example.com", max_retries=1)

    assert result.status == "terminal_failure"
    assert result.http_status == 403
    assert result.reached_archive is True
    assert result.archive_failure is True
