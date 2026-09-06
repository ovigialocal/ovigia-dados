# API-Football: canal, cota e por que a chave parecia suspensa

## O diagnóstico

A chave nunca foi suspensa. Ela é uma chave **RapidAPI** (50 caracteres
alfanuméricos) e estava sendo apresentada ao **canal direto** da API-Sports
(`v3.football.api-sports.io`, header `x-apisports-key`), que não a emitiu.

A mesma assinatura é vendida por dois canais com host, header e prefixo de
caminho próprios:

| canal | host | header | ping barato |
| --- | --- | --- | --- |
| direto (API-Sports) | `https://v3.football.api-sports.io` | `x-apisports-key` | `/status` |
| RapidAPI | `https://api-football-v1.p.rapidapi.com/v3` | `x-rapidapi-key` + `x-rapidapi-host` | `/v3/timezone` |

O canal errado devolve HTTP 200 com `errors.token` — texto idêntico ao de
uma chave inválida. Daí a leitura de "chave suspensa".

Verificação em 6 de setembro de 2026, com a mesma chave:

- `v3.football.api-sports.io/status` → `errors.token: Error/Missing application key`
- `api-football-v1.p.rapidapi.com/v3/timezone` → `results: 427`, cota `98/100`
- `api-football-v1.p.rapidapi.com/v3/teams?search=Porto Velho` → `results: 3`,
  `team_id=12946`

O formato da chave decide o canal e é verificável localmente, sem gastar
requisição: 32 hexadecimais = API-Sports; 50 alfanuméricos = RapidAPI.

## O que fazer para não ser suspenso

1. **Apresente a chave ao canal que a emitiu.** Requisição rejeitada continua
   sendo requisição: um cron diário batendo no canal errado é tráfego de
   autenticação falha vindo de IP de CI, que é exatamente o padrão que motiva
   bloqueio real.
2. **Nunca gire chaves para escapar de rate limit.** Múltiplas chaves da mesma
   conta usadas em rodízio ao receber 429 viola os termos e é o gatilho mais
   direto de suspensão. `rotate_key()` existe para trocar credencial quebrada,
   e não é mais chamada em resposta a limite.
3. **Não repita 429 de cota diária.** O header `x-ratelimit-requests-reset`
   diz em quantos segundos a cota volta. Reset em horas significa que só o dia
   seguinte resolve; o cliente levanta `ApiFootballQuotaError` na hora.
4. **Teto por execução.** O plano gratuito dá 100 requisições por dia. Nenhum
   run isolado deve poder gastar as 100 — `--budget` (padrão 60) garante
   margem para reprocessar.
5. **Sondas não rodam a cada push.** O workflow de diagnose gastava ~9 buscas
   por commit; virou `workflow_dispatch`, com as buscas por nome atrás de
   `SEARCH_ENTITIES=true`.
6. **Leia a cota em vez de adivinhá-la.** `x-ratelimit-requests-limit` e
   `-remaining` saíram do DEBUG e aparecem no log de cada execução.

## Orçamento do pipeline diário

Com o registry atual (7 times, 4 competições), um run consome:

| chamada | quantidade |
| --- | --- |
| `teams?id=` | 7 |
| `fixtures?team=&last=`/`&next=` | 14 |
| `leagues?id=` | 4 |
| `standings?league=&season=` | até 4 |
| **total** | **~29 de 100** |

Próxima economia disponível, ainda não implementada: `teams?id=` e
`leagues?id=` devolvem dados que praticamente não mudam. Cacheá-los (ou
projetá-los do registry OKF) tira ~11 requisições por dia, mais de um terço do
consumo, sem perder nada de editorial.
