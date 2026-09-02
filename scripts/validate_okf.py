# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "okf-parser==0.45.2",
#     "pydantic>=2.0.0",
# ]
# ///
"""Validação do bundle OKF e conferência de conformidade dos modelos."""

import subprocess
import sys


def main():
    print("Executando validação OKF em specs/ e knowledge/...")

    # Valida specs
    cmd_specs = ["okf-parser", "check", "specs"]
    res_specs = subprocess.run(cmd_specs, capture_output=True, text=True)
    if res_specs.returncode != 0:
        print("Erro na validação de specs:", res_specs.stderr or res_specs.stdout)
        sys.exit(res_specs.returncode)
    print("OK: specs/")

    # Valida knowledge
    cmd_know = ["okf-parser", "check", "knowledge"]
    res_know = subprocess.run(cmd_know, capture_output=True, text=True)
    if res_know.returncode != 0:
        print("Erro na validação de knowledge:", res_know.stderr or res_know.stdout)
        sys.exit(res_know.returncode)
    print("OK: knowledge/")

    # Valida exportação de schemas
    cmd_schema = ["okf-parser", "schema", "--format", "pydantic", "knowledge"]
    res_schema = subprocess.run(cmd_schema, capture_output=True, text=True)
    if res_schema.returncode != 0:
        print("Erro na geração de schemas pydantic:", res_schema.stderr)
        sys.exit(res_schema.returncode)
    print("OK: okf-parser schema generation")


if __name__ == "__main__":
    main()
