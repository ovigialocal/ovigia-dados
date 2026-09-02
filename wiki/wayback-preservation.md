# Wayback preservation: estados observáveis

A operação de preservação precisa separar evidência do Internet Archive de falha da infraestrutura que executa o cliente.

Estados reutilizáveis:

- `verified`: o serviço devolveu uma URL concreta `https://web.archive.org/web/...`; somente esse estado carrega `archive_url`;
- `accepted_unverified`: Save Page Now respondeu, mas a execução ainda não obteve URL concreta do snapshot; não fabricar URL e não tratar como concluído;
- `terminal_failure`: a requisição alcançou o Internet Archive e terminou em resposta HTTP após a política de retry; pode sustentar `archive_failure` editorial;
- `infrastructure_error`: DNS, timeout, socket ou falha local anterior a resposta do IA; não é `archive_failure` e deve permanecer pendente para nova execução.

Cada execução versionada deve persistir relatório imutável em `raw/wayback/runs/<github-run-id>-<attempt>.json`. O relatório é evidência operacional pública; a Redação continua responsável por verificar equivalência material do snapshot antes de usar `archive_url` como provenance editorial.
