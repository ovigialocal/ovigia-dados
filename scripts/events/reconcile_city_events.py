#!/usr/bin/env python3
"""Reconcile the latest city-event observations across public sources."""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from ovigia_dados.events.reconcile import (
    load_latest_observations,
    materialize_entities,
    materialize_reconciliations,
    reconcile_observations,
)

logger = logging.getLogger("ovigia.events.reconcile")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations-dir", default="knowledge/events/observations")
    parser.add_argument("--reconciliations-dir", default="knowledge/events/reconciliations")
    parser.add_argument("--entities-dir", default="knowledge/events/entities")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    evaluated_at = datetime.now(UTC)
    observations = load_latest_observations(Path(args.observations_dir))
    reconciliations = reconcile_observations(observations, evaluated_at=evaluated_at)
    equivalent = [item for item in reconciliations if item.decision == "equivalent"]
    review = [item for item in reconciliations if item.decision == "review"]

    created_reconciliations = materialize_reconciliations(
        reconciliations,
        Path(args.reconciliations_dir),
    )
    changed_entities = materialize_entities(
        equivalent,
        Path(args.entities_dir),
        materialized_at=evaluated_at,
    )

    logger.info(
        "Reconciliação: %d observações atuais; %d equivalências; %d revisões; "
        "%d evidências novas; %d entidades criadas/atualizadas",
        len(observations),
        len(equivalent),
        len(review),
        len(created_reconciliations),
        len(changed_entities),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
