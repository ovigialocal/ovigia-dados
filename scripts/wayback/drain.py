# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "okf-parser==0.45.2",
#     "ovigia-dados",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
from pathlib import Path

from ovigia_dados.wayback.drain import drain_wayback_queue


def main() -> None:
    for path in drain_wayback_queue(Path.cwd()):
        print(path)


if __name__ == "__main__":
    main()
