# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "ovigia-dados",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
from pathlib import Path

from ovigia_dados.wayback.queue import load_wayback_queue


def main() -> None:
    queue = load_wayback_queue(Path.cwd())
    print(
        f"Wayback OKF queue valid: pending={len(queue.pending)} "
        f"archived={len(queue.archived)} failed={len(queue.failed)}"
    )


if __name__ == "__main__":
    main()
