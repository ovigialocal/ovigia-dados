# Skill: Wayback preservation

## Purpose

Preservar URLs públicas materiais no Internet Archive sem confundir aceitação, snapshot localizado, equivalência material, recusa do serviço e falha da infraestrutura local.

## Procedure

1. Receba apenas URLs públicas; não copie hipótese, draft ou estratégia editorial privada para este repositório.
2. A fila canônica é formada pelos concepts OKF `archive-request` sob `knowledge/wayback/requests/`; não crie fila `.txt`, JSON/YAML paralela nem `request_id` redundante.
3. Use o workflow `wayback-save.yml` como executor governado. O script `uv run scripts/wayback/save.py --url <URL> ...` permanece útil para desenvolvimento/teste explícito, mas não substitui o `archive-result` governado da fila.
4. Em cada execução, recomponha a fila semântica e drene todos os requests sem `archive-result` terminal. Não exija mudança artificial no arquivo e não duplique request para tentar novamente.
5. O workflow também executa periodicamente para recuperar requests deixados pendentes por DNS, timeout, socket, runner ou outra falha anterior à resposta do IA.
6. Nunca sintetize `archive_url`. Só aceite URL concreta devolvida pelo Wayback em `/web/...`.
7. Para resultado `archived`, materialize replay auditável quando possível. Para HTML/texto e CSVs públicos dentro do limite, mantenha os bytes raw em formato inspecionável; reconheça CSV tanto por MIME próprio quanto por URL `.csv` quando o servidor responder `application/octet-stream`. Para PDF, produza a evidência de equivalência mecânica disponível.
8. Relatório de replay já persistido é append-only: uma execução posterior pode acrescentar o corpo bounded ausente somente quando o SHA-256 obtido do locator ainda coincide com o digest registrado; não reescreva o sidecar para acomodar a nova leitura.
9. Falha ao reabrir o replay não inventa equivalência e não converte o locator em falha terminal: registre a limitação da evidência de replay.
10. Respeite `429`, `Retry-After` e retries limitados.
11. Trate PDF/anexo como URL própria quando esse for o recurso efetivamente usado.
12. Request que terminou sem `archive-result` por DNS, timeout, socket, runner ou outro erro anterior à resposta do IA continua pendente e será tentado novamente em execução posterior. Nunca materialize `archive_failure` para esse caso.
13. `archive-result(status=failed)` só pode ser produzido quando a tentativa realmente alcançou o Internet Archive e recebeu falha terminal; deve registrar `failure.code` e `failure.detail` e não conter `archive_url`.
14. Entregue a evidência à Redação; não execute gate, não altere `source_digest` e não tome decisão editorial. A Redação compara replay/snapshot com a fonte observada e confirma equivalência material.

## Validation

A implementação deve manter testes que provem: ausência de URL fabricada; separação entre `infrastructure_error` e `terminal_failure`; emissão de `archived` apenas para snapshot concreto; replay persistido quando legível; CSV preservado como `.csv` mesmo quando servido como `application/octet-stream`; backfill do corpo sem reescrever sidecar de digest existente; ausência de equivalência fabricada quando a leitura falha; recuperação de requests pendentes sem reescrever sua identidade; e execução idempotente quando não existem novos resultados terminais.
