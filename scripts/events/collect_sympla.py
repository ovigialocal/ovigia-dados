#!/usr/bin/env python3
"""Collect public Porto Velho events from Sympla, with optional Wayback backfill."""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

import requests
from ovigia_dados.events.sympla import (
    SYMPLA_LISTING_URL,
    SymplaParseError,
    discover_historical_event_urls,
    discover_live_event_urls,
    hydrate_latest_archived_event,
    hydrate_live_event,
    is_porto_velho,
    materialize_observations,
)

logger = logging.getLogger("ovigia.events.sympla")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listing-url", default=SYMPLA_LISTING_URL)
    parser.add_argument("--wayback-snapshots", type=int, default=0)
    parser.add_argument("--identities-dir", default="knowledge/events/events")
    parser.add_argument("--observations-dir", default="knowledge/events/observations")
    parser.add_argument("--max-events", type=int, default=100)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    observed_at = datetime.now(UTC)
    session = requests.Session()

    live_urls = discover_live_event_urls(session=session, listing_url=args.listing_url)
    if args.max_events > 0:
        live_urls = live_urls[: args.max_events]
    logger.info("Sympla live: %d URLs de evento descobertas", len(live_urls))

    observations = []
    for event_url in live_urls:
        try:
            event = hydrate_live_event(event_url, session=session, observed_at=observed_at)
        except (requests.RequestException, SymplaParseError) as exc:
            logger.warning("Falha ao hidratar %s: %s", event_url, exc)
            continue
        if not is_porto_velho(event):
            logger.info(
                "Descartado fora de Porto Velho ou sem localização verificável: %s", event_url
            )
            continue
        observations.append(event)

    if args.wayback_snapshots > 0:
        try:
            historical_urls = discover_historical_event_urls(
                session=session,
                listing_url=args.listing_url,
                snapshot_limit=args.wayback_snapshots,
            )
        except requests.RequestException as exc:
            logger.warning("Backfill CDX indisponível: %s", exc)
            historical_urls = []
        live_set = set(live_urls)
        for event_url in historical_urls:
            if event_url in live_set:
                continue
            try:
                event = hydrate_latest_archived_event(event_url, session=session)
            except (requests.RequestException, SymplaParseError) as exc:
                logger.warning("Falha no evento histórico %s: %s", event_url, exc)
                continue
            if event is not None and is_porto_velho(event):
                observations.append(event)

    observations.sort(key=lambda item: item.observed_at)
    created = materialize_observations(
        observations,
        identities_root=Path(args.identities_dir),
        observations_root=Path(args.observations_dir),
    )
    logger.info(
        "Agenda Sympla: %d observações válidas; %d arquivos novos materializados",
        len(observations),
        len(created),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
