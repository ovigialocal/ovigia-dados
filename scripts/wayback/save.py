# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "ovigia-dados",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
"""CLI wrapper for the canonical Wayback preservation implementation."""

from ovigia_dados.wayback.save import main


if __name__ == "__main__":
    main()
