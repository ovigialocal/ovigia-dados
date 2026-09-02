"""Preservação de páginas e recursos no Wayback Machine (Internet Archive)."""

import argparse
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

USER_AGENT = (
    "OVigiaDados/0.1.0 (+https://github.com/ovigialocal/ovigia-dados; contato@ovigia.local)"
)
WAYBACK_ROOT = "https://web.archive.org"


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


def _retry_delay(headers, attempt: int, initial_backoff: float) -> float:
    retry_after = headers.get("Retry-After") if headers else None
    if retry_after:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass
    return initial_backoff * (2 ** (attempt - 1))


def save_to_wayback(
    url: str, max_retries: int = 3, initial_backoff: float = 2.0
) -> WaybackSaveResult:
    """Attempt Save Page Now without confusing local failures with IA refusals."""
    save_endpoint = f"{WAYBACK_ROOT}/save/{url}"

    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(
            save_endpoint,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/html",
            },
        )
        try:
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
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or 500 <= exc.code < 600:
                if attempt < max_retries:
                    time.sleep(min(_retry_delay(exc.headers, attempt, initial_backoff), 60.0))
                    continue
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
            logger.warning(
                "Infraestrutura local falhou antes de resposta do IA para %s: %s", url, exc
            )
            if attempt < max_retries:
                time.sleep(initial_backoff * (2 ** (attempt - 1)))
                continue
            return WaybackSaveResult(
                url=url,
                status="infrastructure_error",
                error_message=str(exc),
                timestamp=_now(),
                reached_archive=False,
                archive_failure=False,
            )

    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description="Salva URLs no Wayback Machine")
    parser.add_argument("--url", help="URL única para arquivar")
    parser.add_argument("--file", help="Arquivo contendo lista de URLs (uma por linha)")
    parser.add_argument("--output-report", help="Caminho JSON para salvar relatório de execução")
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
