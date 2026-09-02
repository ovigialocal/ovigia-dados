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
