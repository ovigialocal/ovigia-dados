#!/usr/bin/env python3
"""Collect public Sesc Rondônia event pages confirmed in Porto Velho."""

from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import requests

from ovigia_dados.events.sesc import SESC_ARCHIVES, SescParseError, discover_event_urls, hydrate_event
from ovigia_dados.events.shared import materialize_observations

logger = logging.getLogger("ovigia.events.sesc")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--identities-dir", default="knowledge/events/events")
    parser.add_argument("--observations-dir", default="knowledge/events/observations")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    observed_at = datetime.now(UTC)
    session = requests.Session()
    try:
        urls = discover_event_urls(
            session=session,
            archives=SESC_ARCHIVES,
            pages=max(1, args.pages),
        )
    except requests.RequestException as exc:
        logger.error("Sesc: falha ao descobrir páginas públicas: %s", exc)
        return 1

    logger.info("Sesc: %d URLs públicas de evento descobertas", len(urls))
    observations = []

    def fetch_one(url: str):
        try:
            return hydrate_event(url, observed_at=observed_at)
        except (requests.RequestException, SescParseError) as exc:
            logger.debug("Sesc: descartado %s: %s", url, exc)
            return None

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(fetch_one, url): url for url in urls}
        for future in as_completed(futures):
            event = future.result()
            if event is not None:
                observations.append(event)

    observations.sort(key=lambda item: item.event_id)
    created = materialize_observations(
        observations,
        identities_root=Path(args.identities_dir),
        observations_root=Path(args.observations_dir),
    )
    logger.info(
        "Sesc: %d eventos com data editorial e local confirmado em Porto Velho; "
        "%d arquivos novos materializados",
        len(observations),
        len(created),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
