from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from ovigia_dados.wayback.save import (
    WaybackSaveResult,
    materialize_snapshot,
    save_to_wayback,
)


class FakeResponse:
    def __init__(
        self,
        *,
        status=200,
        headers=None,
        url="https://web.archive.org/save/https://example.com",
        body=b"<html><body>material evidence</body></html>",
    ):
        self.status = status
        self.headers = headers or Message()
        self._url = url
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self._url

    def read(self, _limit=None):
        return self._body


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


def test_rate_limit_remains_retryable_after_local_retry_budget():
    headers = Message()
    headers["Retry-After"] = "10"
    error = HTTPError(
        "https://web.archive.org/save/https://example.com",
        429,
        "Too Many Requests",
        headers,
        None,
    )
    with patch("ovigia_dados.wayback.save.urllib.request.urlopen", side_effect=error):
        result = save_to_wayback("https://example.com", max_retries=1)

    assert result.status == "retryable_error"
    assert result.http_status == 429
    assert result.reached_archive is True
    assert result.archive_failure is False


def test_transient_5xx_remains_retryable_after_local_retry_budget():
    error = HTTPError(
        "https://web.archive.org/save/https://example.com",
        503,
        "Service Unavailable",
        Message(),
        None,
    )
    with patch("ovigia_dados.wayback.save.urllib.request.urlopen", side_effect=error):
        result = save_to_wayback("https://example.com", max_retries=1)

    assert result.status == "retryable_error"
    assert result.http_status == 503
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


def test_materialize_snapshot_persists_body_and_links_report(tmp_path):
    result = WaybackSaveResult(
        url="https://example.com",
        status="verified",
        archive_url="https://web.archive.org/web/20260902120000/https://example.com",
        reached_archive=True,
    )
    with patch(
        "ovigia_dados.wayback.save.urllib.request.urlopen",
        return_value=FakeResponse(
            url=result.archive_url,
            body=b"<html><body>price R$ 50 and Kids esgotado</body></html>",
        ),
    ):
        enriched = materialize_snapshot(result, tmp_path)

    assert enriched.snapshot_evidence_path is not None
    path = tmp_path / enriched.snapshot_evidence_path
    assert path.read_bytes().startswith(b"<html>")
    assert enriched.snapshot_fetch_error is None


def test_materialize_snapshot_failure_does_not_fake_equivalence(tmp_path):
    result = WaybackSaveResult(
        url="https://example.com",
        status="verified",
        archive_url="https://web.archive.org/web/20260902120000/https://example.com",
        reached_archive=True,
    )
    with patch(
        "ovigia_dados.wayback.save.urllib.request.urlopen",
        side_effect=URLError("snapshot fetch failed"),
    ):
        enriched = materialize_snapshot(result, tmp_path)

    assert enriched.snapshot_evidence_path is None
    assert "snapshot fetch failed" in (enriched.snapshot_fetch_error or "")
