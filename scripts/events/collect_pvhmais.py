#!/usr/bin/env python3
"""Collect public Porto Velho events from the municipal PVH Mais portal."""

from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import requests

from ovigia_dados.events.pvhmais import (
    PVHMAIS_EVENTS_URL,
    PvhMaisParseError,
    hydrate_event,
    scan_ids_from_listing,
)
from ovigia_dados.events.shared import fetch_text, materialize_observations

logger = logging.getLogger("ovigia.events.pvhmais")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listing-url", default=PVHMAIS_EVENTS_URL)
    parser.add_argument("--bootstrap-max", type=int, default=150)
    parser.add_argument("--lookahead", type=int, default=30)
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
    listing = fetch_text(args.listing_url)
    event_ids = scan_ids_from_listing(
        listing,
        bootstrap_max=max(1, args.bootstrap_max),
        lookahead=max(0, args.lookahead),
    )
    logger.info("PVH+: verificando %d IDs públicos de evento", len(event_ids))

    observations = []

    def fetch_one(event_id: int):
        try:
            return hydrate_event(event_id, observed_at=observed_at)
        except (requests.RequestException, PvhMaisParseError):
            return None

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(fetch_one, event_id): event_id for event_id in event_ids}
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
        "PVH+: %d eventos públicos válidos; %d arquivos novos materializados",
        len(observations),
        len(created),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
