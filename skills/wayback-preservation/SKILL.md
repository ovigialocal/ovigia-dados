# Skill: Wayback preservation

## Purpose

Preservar URLs públicas materiais no Internet Archive sem confundir aceitação, snapshot verificado, recusa do serviço e falha da infraestrutura local.

## Procedure

1. Receba apenas URLs públicas; não copie hipótese, draft ou estratégia editorial privada para este repositório.
2. Execute `uv run scripts/wayback/save.py --url <URL> --output-report <arquivo>` ou use o workflow `wayback-save.yml`.
3. Para lote versionado, use `--file <arquivo>` e uma URL por linha.
4. Classifique cada resultado apenas pelos estados documentados em `wiki/wayback-preservation.md`.
5. Nunca sintetize `archive_url`. Só aceite URL concreta devolvida pelo Wayback em `/web/...`.
6. Respeite `429`, `Retry-After` e retries limitados.
7. Preserve o relatório da execução em `raw/wayback/runs/` quando rodado pelo workflow.
8. Trate PDF/anexo como URL própria quando esse for o recurso efetivamente usado.
9. Entregue o resultado à Redação; não execute gate, não altere `source_digest` e não tome decisão editorial.

## Validation

A implementação deve manter testes que provem: ausência de URL fabricada; separação entre `infrastructure_error` e `terminal_failure`; e emissão de `verified` apenas para snapshot concreto.
