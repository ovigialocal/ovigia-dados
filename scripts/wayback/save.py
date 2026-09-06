# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "ovigia-dados",
#     "tenacity>=9.0",
# ]
# [tool.uv.sources]
# ovigia-dados = { path = "../.." }
# ///
from ovigia_dados.wayback.save import main

if __name__ == "__main__":
    main()
