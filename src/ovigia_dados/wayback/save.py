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


@dataclass
class WaybackSaveResult:
    url: str
    status: str  # "saved", "already_available", "rate_limited", "network_error", "blocked"
    archive_url: str | None = None
    http_status: int | None = None
    error_message: str | None = None
    timestamp: str | None = None


def save_to_wayback(
    url: str, max_retries: int = 3, initial_backoff: float = 2.0
) -> WaybackSaveResult:
    """Tenta salvar uma URL no Wayback Machine respeitando rate limits e Retry-After."""
    save_endpoint = f"https://web.archive.org/save/{url}"

    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(
            save_endpoint,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/html",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                status_code = response.status
                archive_location = response.headers.get("Content-Location") or response.headers.get(
                    "Location"
                )
                if archive_location and not archive_location.startswith("http"):
                    archive_location = f"https://web.archive.org{archive_location}"

                return WaybackSaveResult(
                    url=url,
                    status="saved",
                    archive_url=archive_location or f"https://web.archive.org/web/{url}",
                    http_status=status_code,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("Retry-After")
                wait_seconds = (
                    float(retry_after) if retry_after else (initial_backoff * (2 ** (attempt - 1)))
                )
                logger.warning(
                    f"Rate limited (429) no Wayback. Aguardando {wait_seconds}s (tentativa {attempt}/{max_retries})..."
                )
                if attempt < max_retries:
                    time.sleep(min(wait_seconds, 60.0))
                    continue
                return WaybackSaveResult(
                    url=url,
                    status="rate_limited",
                    http_status=429,
                    error_message="Exceeded max retries for Wayback rate limit",
                )
            elif e.code in (403, 401):
                return WaybackSaveResult(
                    url=url,
                    status="blocked",
                    http_status=e.code,
                    error_message=f"Access blocked by origin/archive: {e.reason}",
                )
            else:
                return WaybackSaveResult(
                    url=url,
                    status="network_error",
                    http_status=e.code,
                    error_message=f"HTTP {e.code}: {e.reason}",
                )
        except Exception as ex:
            logger.error(f"Erro ao salvar no Wayback ({url}): {ex}")
            if attempt < max_retries:
                time.sleep(initial_backoff * (2 ** (attempt - 1)))
                continue
            return WaybackSaveResult(
                url=url,
                status="network_error",
                error_message=str(ex),
            )

    return WaybackSaveResult(url=url, status="network_error", error_message="Max retries reached")


def main():
    parser = argparse.ArgumentParser(description="Salva URLs no Wayback Machine")
    parser.add_argument("--url", help="URL única para arquivar")
    parser.add_argument("--file", help="Arquivo contendo lista de URLs (uma por linha)")
    parser.add_argument("--output-report", help="Caminho JSON para salvar relatório de execução")
    args = parser.parse_args()

    urls_to_save = []
    if args.url:
        urls_to_save.append(args.url)
    elif args.file:
        p = Path(args.file)
        if p.exists():
            urls_to_save = [
                line.strip()
                for line in p.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]

    if not urls_to_save:
        print("Nenhuma URL fornecida.")
        return

    results = []
    for u in urls_to_save:
        print(f"Arquivando no Wayback: {u}...")
        res = save_to_wayback(u)
        results.append(asdict(res))
        print(
            f"Resultado: {res.status} (HTTP {res.http_status}) -> {res.archive_url or res.error_message}"
        )

    if args.output_report:
        out_p = Path(args.output_report)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Relatório gravado em: {out_p}")


if __name__ == "__main__":
    main()
