# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "okf-parser==0.45.2",
#     "ovigia-dados",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
import argparse
from pathlib import Path

from ovigia_dados.wayback.replay import (
    materialize_replay_evidence,
    select_replay_result_paths,
)


def _read_result_paths(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("knowledge/wayback/results/")
        and line.strip().endswith(".md")
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-path-file", type=Path, default=None)
    parser.add_argument("--backfill-limit", type=int, default=None)
    args = parser.parse_args()

    if args.result_path_file is None and args.backfill_limit is None:
        selected = None
    else:
        selected = select_replay_result_paths(
            Path.cwd(),
            preferred_paths=_read_result_paths(args.result_path_file),
            backfill_limit=1 if args.backfill_limit is None else args.backfill_limit,
        )

    for path in materialize_replay_evidence(Path.cwd(), result_paths=selected):
        print(path)


if __name__ == "__main__":
    main()
