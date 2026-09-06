# API-Football: canal, cota e por que a chave parecia suspensa

## O diagnóstico

A chave nunca foi suspensa. Ela é reconhecida pela **RapidAPI** e estava
sendo apresentada ao **canal direto** da API-Sports
(`v3.football.api-sports.io`, header `x-apisports-key`), que não a emitiu.

A mesma assinatura é vendida por dois canais com host, header e prefixo de
caminho próprios:

| canal | host | header | ping barato |
| --- | --- | --- | --- |
| direto (API-Sports) | `https://v3.football.api-sports.io` | `x-apisports-key` | `/status` |
| RapidAPI | `https://api-football-v1.p.rapidapi.com/v3` | `x-rapidapi-key` + `x-rapidapi-host` | `/v3/timezone` |

O canal errado devolve HTTP 200 com `errors.token` — texto idêntico ao de
uma chave inválida. Daí a leitura de "chave suspensa".

Verificação em 6 de setembro de 2026, com o secret `API_FOOTBALL_KEY` do
repositório, em runner do GitHub Actions:

- `v3.football.api-sports.io/status` → `errors.token: Error/Missing application key`
- `api-football-v1.p.rapidapi.com/v3/timezone` → **aceita**, cota `99/100`

### Sobre o formato da chave

O formato decide o canal localmente, sem gastar requisição, mas a regra não é
uma dicotomia limpa. **32 caracteres hexadecimais** identifica positivamente
uma chave da API-Sports. Tudo o mais vai para a RapidAPI, que não emite um
formato único: a chave de 50 alfanuméricos é a mais comum, e o secret deste
repositório tem 32 caracteres **não** hexadecimais e é aceito lá.

Uma sonda anterior (5 de setembro) leu esses 32 caracteres, concluiu
"chave de outro canal ou conta não ativada" e parou — porque testava a
RapidAPI em `/v3/status`, endpoint que não existe naquele canal, e o 404
foi lido como recusa. Endpoint errado produz o mesmo silêncio que chave
errada; é por isso que a sonda agora usa `/v3/timezone`.

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
   margem para reprocessar, e `daily_reserve` (padrão 10) impede que a cota
   chegue a zero.
5. **Sondas não rodam a cada push.** O workflow de diagnose gastava ~9 buscas
   por commit; virou `workflow_dispatch`, com as buscas por nome atrás de
   `SEARCH_ENTITIES=true`.
6. **Leia a cota em vez de adivinhá-la.** `x-ratelimit-requests-limit` e
   `-remaining` saíram do DEBUG e aparecem no log de cada execução.

## Cadência e rate limit

A cadência não é escrita à mão. `pyrate-limiter` aplica as taxas e `tenacity`
aplica o retry; o que o repositório define é só a política.

**Duas taxas, não uma.** `Rate(10, minuto)` é o limite que a API conta, mas
sozinho ele permite disparar as dez de uma vez e ficar cinquenta segundos
calado. `Rate(1, 6 segundos)` espalha as requisições dentro do minuto. Rajada
é a forma mais fácil de esbarrar em guarda por segundo que a API não
documenta — e a RapidAPI não publica limite por minuto em header nenhum, então
o número conservador (10/min) vale para os dois canais. Não vale descobrir o
teto empiricamente: cada tentativa de descobrir é mais uma requisição recusada
no histórico da conta.

**O limitador bloqueia, e é de propósito.** A alternativa é receber "não pode
agora" e decidir o que fazer, que é exatamente a decisão que se erra.

**Espera por motivo, não por tentativa.** 429 sem header de reset espera o
minuto virar (60s × tentativa), porque o limite por minuto só zera quando o
minuto passa; repetir em 11 segundos gasta requisição para colher a mesma
recusa. Falha de rede espera 2s × tentativa, que é transitória de verdade e
não merece o mesmo castigo. Jitter em cima das duas: cadência perfeitamente
periódica vinda de IP de CI é assinatura de robô e custa segundos remover.

**A execução para antes de zerar.** `daily_reserve` (padrão 10) faz o run
parar com dez requisições sobrando. Chegar a zero é o que antecede a rajada
de 429, e é a rajada — não o esgotamento — que motiva bloqueio.

## Orçamento do pipeline diário

Com o registry atual (7 times, 4 competições), um run consome:

| chamada | antes | agora |
| --- | --- | --- |
| `teams?id=` | 7 | 0 — lido de `raw/` |
| `fixtures?team=&last=`/`&next=` | 14 | 14 |
| `leagues?id=` (sondagem de cobertura) | 4 | 0 — removida |
| `standings?league=&season=` | até 4 | até 4 |
| **total** | **~29 de 100** | **18 de 100** |

A conta acima é só do pipeline. O orçamento que importa é o da conta, somando
todos os workflows que dividem a mesma cota:

| workflow | cadência | requisições |
| --- | --- | --- |
| `sports-api-football.yml` | diário 05:30 UTC | 18 |
| `sports-quarto-queries.yml` | diário 06:15 UTC | 0 — lê de `raw/` |
| `sports-diagnose.yml` | sob demanda | 2 (mais 7 com `SEARCH_ENTITIES`) |

Uma sonda que gasta requisição para reconfirmar a mesma resposta todo dia é
exatamente o que a economia removeu, então a cobertura declarada da liga
também mora em `raw/`. `REFRESH_LEAGUE_COVERAGE=true` rebusca.

## Onde o dado bruto mora

Time e competição são entidades estáveis: nome, fundação, estádio e cidade não
mudam de um dia para o outro. O payload da API fica em
`raw/sports/api-football/teams/<id>.json`, versionado, e o pipeline lê de lá.
Só `--refresh-static` rebusca, e aí o diff mostra o que a fonte mudou.

Três camadas, cada uma para um consumidor:

- **`raw/` no git** é o caminho de leitura em tempo de execução. É o que
  compra a economia, e é reproduzível fora do CI.
- **Cache do Actions** foi descartado: é evictável — sete dias sem uso e some
  — e o miss vira requisição silenciosa contra a mesma cota que se queria
  proteger. Economia que falha calada não é economia.
- **Internet Archive** é a cópia pública e durável. Os payloads brutos vão
  zipados junto do snapshot, pelo `--raw` que o publisher já aceitava, para
  que repórteres usem o dado sem chave e sem consultar a API.

Transcrever esses campos para o frontmatter do registry seria pior que as três:
o registry é autoria editorial, e misturar nele dado copiado da fonte cria
divergência silenciosa no dia em que a fonte mudar.

A sondagem de cobertura (`leagues?id=`) saiu porque custava uma requisição por
competição para prever uma recusa que a própria chamada de `standings` já
informa — e que o pipeline já tratava sem derrubar a coleta.
