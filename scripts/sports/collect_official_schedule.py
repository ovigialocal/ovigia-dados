#!/usr/bin/env python3
"""Collect an official football agenda and emit post-match transition leads."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from ovigia_dados.sports.leads import materialize_signal_concepts
from ovigia_dados.sports.official_sources import (
    fetch_public_html,
    finished_transitions,
    parse_ffer_fixture_table,
    read_fixture_csv,
    write_fixture_csv,
)

DEFAULT_FFER_RONDONIENSE_2026 = "https://ffer.com.br/Publicacao.aspx?id=640220"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Coleta agenda/resultados oficiais sem depender de API comercial"
    )
    parser.add_argument("--source", choices=["ffer"], default="ffer")
    parser.add_argument("--url", default=DEFAULT_FFER_RONDONIENSE_2026)
    parser.add_argument("--competition", default="Rondoniense")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument(
        "--output",
        default="datasets/sports/current/rondoniense-2026.csv",
        help="Projeção atual estável de agenda/resultados",
    )
    parser.add_argument(
        "--raw-output",
        default="data/output/sports-official/source.html",
        help="HTML observado nesta execução; evidência transitória para artifact/archive",
    )
    parser.add_argument(
        "--leads-dir",
        default="knowledge/sports/leads",
        help="Bundle OKF de sinais públicos",
    )
    parser.add_argument(
        "--snapshot-id",
        default=datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ"),
    )
    args = parser.parse_args()

    output = Path(args.output)
    previous = read_fixture_csv(output)

    html = fetch_public_html(args.url)
    raw_output = Path(args.raw_output)
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_text(html, encoding="utf-8")

    records = parse_ffer_fixture_table(
        html,
        source_url=args.url,
        season=args.season,
        competition_name=args.competition,
    )
    if not records:
        raise SystemExit(
            "A fonte oficial respondeu, mas nenhuma partida reconhecível foi extraída."
        )

    signals = finished_transitions(previous, records, snapshot_id=args.snapshot_id)
    write_fixture_csv(records, output)
    created = materialize_signal_concepts(signals, args.leads_dir)

    scheduled = sum(record["status"] == "scheduled" for record in records)
    finished = sum(record["status"] == "finished" for record in records)
    print(
        "official sports collection: "
        f"matches={len(records)} scheduled={scheduled} finished={finished} "
        f"post_match_leads={len(created)} output={output}"
    )


if __name__ == "__main__":
    main()
