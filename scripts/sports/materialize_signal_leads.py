# /// script
# requires-python = ">=3.12"
# ///
"""Materialize sports detector JSONL signals into persistent OKF concepts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from ovigia_dados.sports.leads import materialize_signal_concepts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signals", required=True)
    parser.add_argument("--output-dir", default="knowledge/sports/leads")
    args = parser.parse_args()

    signals_path = Path(args.signals)
    signals = [
        json.loads(line)
        for line in signals_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    created = materialize_signal_concepts(signals, args.output_dir)
    print(json.dumps({"created": [str(path) for path in created]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
