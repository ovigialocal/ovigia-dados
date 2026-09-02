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

from ovigia_dados.wayback.replay import materialize_replay_evidence


if __name__ == "__main__":
    for path in materialize_replay_evidence(Path.cwd()):
        print(path)
