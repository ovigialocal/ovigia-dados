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

from ovigia_dados.wayback.drain import drain_wayback_queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-path", action="append", default=None)
    args = parser.parse_args()
    selected = set(args.request_path) if args.request_path else None
    for path in drain_wayback_queue(Path.cwd(), request_paths=selected):
        print(path)


if __name__ == "__main__":
    main()
