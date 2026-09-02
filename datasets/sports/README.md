# Datasets Esportivos: API-Football (`sports`)

Estrutura pública de dados esportivos locais e regionais a partir da API-Football v3 (`https://www.api-football.com/documentation-v3`).

---

## 1. Princípios de Coleta e Economia de Quota

* **Respeito a Rate Limits**: Leitura de cabeçalhos `x-ratelimit-requests-remaining` e suporte a rotação via `API_FOOTBALL_KEY` / `API_FOOTBALL_KEYS`.
* **Verificação Prévia de `coverage`**: Nunca consulta endpoints sem cobertura declarada na liga/temporada (ex: `coverage.injuries`, `coverage.fixtures.events`).
* **Cache e Imutabilidade**: Partidas passadas e finalizadas são arquivadas de forma imutável em Parquet. Apenas partidas recentes/agendadas e movimentações de tabela são consultadas periodicamente.
* **Storage Canônico**: Snapshots em Apache Parquet publicados no [Internet Archive](https://archive.org/details/ovigia-dados-sports-catalog).

---

## 2. Tabelas Disponíveis

1. `teams.parquet`: Cadastro de clubes monitorados, cidade, estádio e metadados.
2. `fixtures.parquet`: Jogos, datas, horários, locais, placares e status.
3. `standings.parquet`: Histórico de classificação por rodada e pontos.
4. `events.parquet`: Gols, cartões, substituições e VAR das partidas cobertas.
5. `signals.parquet` / `signals.jsonl`: Sinais factuais emitidos pelos detectores esportivos.

---

## 3. Catálogo SQL DuckDB

Consulte diretamente via [`catalog.sql`](catalog.sql):

```sql
SELECT
    f.fixture_id,
    f.date,
    f.home_team_name,
    f.away_team_name,
    f.score_home,
    f.score_away,
    f.status_short
FROM read_parquet('https://archive.org/download/ovigia-dados-sports-*/fixtures.parquet') f
WHERE f.league_id = 662 -- Rondoniense
ORDER BY f.date DESC
LIMIT 10;
```
