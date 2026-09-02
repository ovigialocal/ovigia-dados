# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "ovigia-dados",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
from ovigia_dados.wayback.save import main

if __name__ == "__main__":
    main()
