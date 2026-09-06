# Sympla city events

Use esta skill para atualizar a agenda pública de Porto Velho a partir da Sympla e, quando necessário, recuperar histórico pelo Wayback.

## Procedimento

1. Rode `uv run scripts/events/collect_sympla.py` para a coleta live.
2. Trate a listagem de Porto Velho apenas como discovery; confirme município/UF na página individual antes de materializar o evento local.
3. Prefira JSON-LD `Event`; use o HTML server-rendered apenas como fallback conservador.
4. Preserve `sympla-<id>` como identidade estável e crie `event-observation` somente quando o hash do estado público mudar.
5. Para backfill, rode com `--wayback-snapshots N`. CDX recupera URLs antigas da listagem e o último snapshot disponível da página individual.
6. Falha ou ausência de Wayback não bloqueia a coleta live.
7. Não introduza dependência de endpoints internos/GraphQL/XHR não documentados da Sympla.

## Evidência e validação

Conhecimento consolidado: `wiki/city-event-sources.md`.

Valide alterações com:

`uv run pytest tests/events/test_sympla.py`

Quando alterar os contracts, valide também `specs/` e os concepts materializados com `okf-parser check`.
