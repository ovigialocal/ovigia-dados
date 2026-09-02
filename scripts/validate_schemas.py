# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "duckdb>=1.0.0",
# ]
# ///
"""Validação estática e dinâmica de schemas SQL DuckDB."""

from pathlib import Path

import duckdb


def main():
    con = duckdb.connect(":memory:")
    schema_files = list(Path("datasets").glob("**/schema.sql"))
    if not schema_files:
        print("Nenhum schema.sql encontrado.")
        return
    for sf in schema_files:
        print(f"Validando {sf}...")
        con.execute(sf.read_text(encoding="utf-8"))
        print(f"OK: {sf}")


if __name__ == "__main__":
    main()
