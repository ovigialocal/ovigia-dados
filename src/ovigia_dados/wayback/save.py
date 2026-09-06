"""Preservação de páginas e recursos no Wayback Machine (Internet Archive)."""

import argparse
import hashlib
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from tenacity import Retrying, RetryCallState, before_sleep_log, retry_if_exception, stop_after_attempt

logger = logging.getLogger(__name__)

USER_AGENT = (
    "OVigiaDados/0.1.0 (+https://github.com/ovigialocal/ovigia-dados; contato@ovigia.local)"
)
WAYBACK_ROOT = "https://web.archive.org"
_MAX_SNAPSHOT_BYTES = 5_000_000


@dataclass
class WaybackSaveResult:
    """Structured evidence for one preservation attempt."""

    url: str
    status: str
    archive_url: str | None = None
    http_status: int | None = None
    error_message: str | None = None
    timestamp: str | None = None
    attempted: bool = True
    reached_archive: bool = False
    archive_failure: bool = False
    snapshot_evidence_path: str | None = None
    snapshot_fetch_error: str | None = None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _snapshot_url(response) -> str | None:
    """Return only a concrete Wayback snapshot URL supplied by the service."""
    for candidate in (
        response.headers.get("Content-Location"),
        response.headers.get("Location"),
        response.geturl(),
    ):
        if not candidate:
            continue
        if candidate.startswith("/"):
            candidate = f"{WAYBACK_ROOT}{candidate}"
        if candidate.startswith(f"{WAYBACK_ROOT}/web/"):
            return candidate
    return None


def _is_retryable_http(status: int) -> bool:
    """Return whether an IA response means retry later rather than terminal refusal."""
    return status == 429 or 500 <= status < 600


def _is_retryable_exception(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return _is_retryable_http(exc.code)
    return isinstance(exc, (urllib.error.URLError, TimeoutError, OSError))


def _retry_wait(initial_backoff: float):
    """Build a Tenacity wait function honoring Retry-After when IA provides it."""

    def wait(retry_state: RetryCallState) -> float:
        outcome = retry_state.outcome
        exc = outcome.exception() if outcome is not None and outcome.failed else None
        if isinstance(exc, urllib.error.HTTPError):
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if retry_after:
                try:
                    return min(max(float(retry_after), 0.0), 60.0)
                except ValueError:
                    pass
        attempt = retry_state.attempt_number
        return min(initial_backoff * (2 ** (attempt - 1)), 60.0)

    return wait


def materialize_snapshot(result: WaybackSaveResult, root: Path) -> WaybackSaveResult:
    """Persist a bounded replay body so downstream reviewers can inspect captured bytes."""
    if result.status != "verified" or result.archive_url is None:
        return result

    request = urllib.request.Request(result.archive_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            body = response.read(_MAX_SNAPSHOT_BYTES + 1)
        if len(body) > _MAX_SNAPSHOT_BYTES:
            return replace(
                result,
                snapshot_fetch_error=f"snapshot exceeds {_MAX_SNAPSHOT_BYTES} byte evidence limit",
            )
        digest = hashlib.sha256(result.archive_url.encode("utf-8")).hexdigest()
        filename = f"{digest}.html"
        root.mkdir(parents=True, exist_ok=True)
        path = root / filename
        path.write_bytes(body)
        return replace(result, snapshot_evidence_path=filename, snapshot_fetch_error=None)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        return replace(result, snapshot_fetch_error=str(exc))


def _attempt_save(url: str) -> WaybackSaveResult:
    save_endpoint = f"{WAYBACK_ROOT}/save/{url}"
    req = urllib.request.Request(
        save_endpoint,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/html",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
        snapshot = _snapshot_url(response)
        if snapshot is None:
            return WaybackSaveResult(
                url=url,
                status="accepted_unverified",
                http_status=response.status,
                timestamp=_now(),
                reached_archive=True,
                error_message="Save Page Now responded without a concrete snapshot URL",
            )
        return WaybackSaveResult(
            url=url,
            status="verified",
            archive_url=snapshot,
            http_status=response.status,
            timestamp=_now(),
            reached_archive=True,
        )


def save_to_wayback(
    url: str, max_retries: int = 3, initial_backoff: float = 2.0
) -> WaybackSaveResult:
    """Attempt Save Page Now using Tenacity for bounded in-run retries."""
    retrying = Retrying(
        stop=stop_after_attempt(max_retries),
        wait=_retry_wait(initial_backoff),
        retry=retry_if_exception(_is_retryable_exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

    try:
        return retrying(_attempt_save, url)
    except urllib.error.HTTPError as exc:
        if _is_retryable_http(exc.code):
            logger.warning(
                "Internet Archive pediu retry posterior para %s após %s tentativas: HTTP %s",
                url,
                max_retries,
                exc.code,
            )
            return WaybackSaveResult(
                url=url,
                status="retryable_error",
                http_status=exc.code,
                error_message=f"Save Page Now returned retryable HTTP {exc.code}: {exc.reason}",
                timestamp=_now(),
                reached_archive=True,
                archive_failure=False,
            )
        return WaybackSaveResult(
            url=url,
            status="terminal_failure",
            http_status=exc.code,
            error_message=f"Save Page Now returned HTTP {exc.code}: {exc.reason}",
            timestamp=_now(),
            reached_archive=True,
            archive_failure=True,
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Infraestrutura local falhou antes de resposta do IA para %s: %s", url, exc)
        return WaybackSaveResult(
            url=url,
            status="infrastructure_error",
            error_message=str(exc),
            timestamp=_now(),
            reached_archive=False,
            archive_failure=False,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Salva URLs no Wayback Machine")
    parser.add_argument("--url", help="URL única para arquivar")
    parser.add_argument("--file", help="Arquivo contendo lista de URLs (uma por linha)")
    parser.add_argument("--output-report", help="Caminho JSON para salvar relatório de execução")
    parser.add_argument(
        "--snapshot-dir",
        help="Diretório para persistir cópias limitadas dos replays Wayback verificados",
    )
    args = parser.parse_args()

    urls_to_save: list[str] = []
    if args.url:
        urls_to_save.append(args.url)
    elif args.file:
        path = Path(args.file)
        if path.exists():
            urls_to_save = [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]

    if not urls_to_save:
        print("Nenhuma URL fornecida.")
        return

    results = []
    for source_url in urls_to_save:
        print(f"Arquivando no Wayback: {source_url}...")
        result = save_to_wayback(source_url)
        if args.snapshot_dir:
            snapshot_root = Path(args.snapshot_dir)
            materialized = materialize_snapshot(result, snapshot_root)
            if materialized.snapshot_evidence_path is not None:
                materialized = replace(
                    materialized,
                    snapshot_evidence_path=(
                        snapshot_root / materialized.snapshot_evidence_path
                    ).as_posix(),
                )
            result = materialized
        results.append(asdict(result))
        print(
            f"Resultado: {result.status} (HTTP {result.http_status}) -> "
            f"{result.archive_url or result.error_message}"
        )

    if args.output_report:
        output = Path(args.output_report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Relatório gravado em: {output}")


if __name__ == "__main__":
    main()
