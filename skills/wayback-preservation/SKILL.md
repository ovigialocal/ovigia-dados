# Skill: Wayback preservation

## Purpose

Preservar URLs públicas materiais no Internet Archive sem confundir aceitação, snapshot localizado, equivalência material, recusa do serviço e falha da infraestrutura local.

## Procedure

1. Receba apenas URLs públicas; não copie hipótese, draft ou estratégia editorial privada para este repositório.
2. Execute `uv run scripts/wayback/save.py --url <URL> --output-report <arquivo> --snapshot-dir <diretório>` ou use o workflow `wayback-save.yml`.
3. Para lote versionado, use `--file <arquivo>` e uma URL por linha.
4. Classifique cada resultado apenas pelos estados documentados em `wiki/wayback-preservation.md`.
5. Nunca sintetize `archive_url`. Só aceite URL concreta devolvida pelo Wayback em `/web/...`.
6. Para `verified`, tente reabrir o locator e materialize os bytes limitados do replay em `raw/wayback/snapshots/`; registre o caminho no relatório.
7. Falha nessa segunda leitura não invalida o locator nem cria equivalência: deixe `snapshot_evidence_path` vazio e registre `snapshot_fetch_error`.
8. Respeite `429`, `Retry-After` e retries limitados.
9. Preserve relatório e sidecars em `raw/wayback/` quando rodado pelo workflow.
10. Trate PDF/anexo como URL própria quando esse for o recurso efetivamente usado.
11. Request que terminou sem `archive-result` por DNS, timeout, socket, runner ou outro erro anterior à resposta do IA continua pendente. Depois de corrigir `src/ovigia_dados/wayback/**`, `scripts/wayback/**` ou o próprio workflow, a execução seguinte deve redrenar a fila pendente inteira sob a implementação nova; não exigir alteração artificial do request para tentar de novo.
12. Em pushes que apenas adicionam requests, drene somente os requests novos/alterados para evitar repetição desnecessária. `workflow_dispatch` continua sendo recuperação explícita da fila pendente completa.
13. Entregue a evidência à Redação; não execute gate, não altere `source_digest` e não tome decisão editorial. A Redação é quem compara o sidecar com a fonte observada e confirma equivalência material.

## Validation

A implementação deve manter testes que provem: ausência de URL fabricada; separação entre `infrastructure_error` e `terminal_failure`; emissão de `verified` apenas para snapshot concreto; sidecar persistido quando o replay é legível; ausência de equivalência fabricada quando a leitura do replay falha; e recuperação de requests pendentes depois de mudança material no worker sem reescrever a identidade do request.
