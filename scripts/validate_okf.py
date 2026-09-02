# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "okf-parser==0.45.2",
#     "pydantic>=2.0.0",
# ]
# ///
"""Validação do bundle OKF e conferência de conformidade dos modelos."""

from pathlib import Path

from okf_parser import validate_path
from okf_parser.schema_export import export_pydantic_source


def _validate(root: str) -> None:
    report = validate_path(Path(root))
    errors = [item for item in report.violations if item.severity.value == "error"]
    if errors:
        rendered = "\n".join(f"{item.path}: {item.code}: {item.message}" for item in errors)
        raise SystemExit(f"Erro na validação de {root}:\n{rendered}")
    print(f"OK: {root}/")


def main() -> None:
    print("Executando validação OKF em specs/ e knowledge/...")
    _validate("specs")
    _validate("knowledge")

    source = export_pydantic_source("knowledge")
    if not source.strip():
        raise SystemExit("Erro na geração de schemas pydantic: saída vazia")
    print("OK: okf-parser schema generation")


if __name__ == "__main__":
    main()
