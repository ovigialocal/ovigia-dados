# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "ovigia-dados",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
from pathlib import Path

from ovigia_dados.wayback.text_replay import materialize_decoded_text_replays


def main() -> None:
    for path in materialize_decoded_text_replays(Path.cwd()):
        print(path)


if __name__ == "__main__":
    main()
