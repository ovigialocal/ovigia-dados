# Wayback preservation: estados observáveis

A operação de preservação precisa separar evidência do Internet Archive de falha da infraestrutura que executa o cliente.

Estados reutilizáveis:

- `verified`: o serviço devolveu uma URL concreta `https://web.archive.org/web/...`; somente esse estado carrega `archive_url`;
- `accepted_unverified`: Save Page Now respondeu, mas a execução ainda não obteve URL concreta do snapshot; não fabricar URL e não tratar como concluído;
- `terminal_failure`: a requisição alcançou o Internet Archive e terminou em resposta HTTP após a política de retry; pode sustentar `archive_failure` editorial;
- `infrastructure_error`: DNS, timeout, socket ou falha local anterior a resposta do IA; não é `archive_failure` e deve permanecer pendente para nova execução.

Cada execução versionada persiste relatório imutável em `raw/wayback/runs/<github-run-id>-<attempt>.json`. Quando um locator `verified` também puder ser reaberto pelo runner, uma cópia limitada do replay é persistida em `raw/wayback/snapshots/<run>-<attempt>/` e o relatório ganha `snapshot_evidence_path`.

O sidecar resolve um problema prático: consumidores que não alcançam `web.archive.org` podem inspecionar pelo GitHub os bytes que o próprio runner obteve do locator. Ele não converte automaticamente `verified` em equivalência editorial. A Redação ainda compara esses bytes com a fonte observada e decide se sustentam materialmente os fatos usados.

Se a segunda leitura do replay falhar, o locator continua `verified`, mas `snapshot_evidence_path` permanece ausente e `snapshot_fetch_error` registra a falha. Não se inventa equivalência.

## GitHub Actions: não usar fila global de concurrency

Uma execução real em 2026-09-02 mostrou que um grupo global de `concurrency` não funciona como fila durável de requests: quando já existe um run em execução e outro pendente, a chegada de um terceiro evento pode cancelar o pendente anterior mesmo com `cancel-in-progress: false`. Nesse caso a URL versionada nunca chega ao Save Page Now e tampouco produz evidência operacional.

Por isso o workflow de preservação não serializa todos os requests num único grupo. Runs podem coexistir; o cliente absorve `429`/5xx com `Retry-After`/backoff, e a persistência de `raw/wayback` reconcilia corridas com fetch, rebase e retry. Run cancelado ou falha do runner continua sendo problema de infraestrutura, jamais recusa do Internet Archive.
