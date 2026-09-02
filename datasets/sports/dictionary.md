---
okf_version: "0.2"
title: "Dicionário de Dados: Esportes"
description: "Dicionário formal de tipos e campos das tabelas teams, fixtures e standings."
type: "documentation"
---

# Dicionário de Dados: `sports` (v1.0)

### Tabela `teams`
| Coluna | Tipo DuckDB | Descrição |
| :--- | :--- | :--- |
| `team_id` | `INTEGER` | Identificador único do clube na API-Football |
| `name` | `VARCHAR` | Nome do clube |
| `code` | `VARCHAR` | Sigla/código do clube |
| `country` | `VARCHAR` | País de origem |
| `founded` | `INTEGER` | Ano de fundação |
| `national` | `BOOLEAN` | Se é seleção nacional |
| `logo` | `VARCHAR` | URL do escudo oficial |
| `venue_id` | `INTEGER` | ID do estádio/praça esportiva |
| `venue_name` | `VARCHAR` | Nome do estádio |
| `venue_city` | `VARCHAR` | Cidade do estádio |
| `uf` | `VARCHAR` | Sigla da UF associada (ex: `RO`) |
| `observed_at` | `TIMESTAMP` | Momento da observação UTC |
| `snapshot_id` | `VARCHAR` | ID do snapshot canônico |

### Tabela `fixtures`
| Coluna | Tipo DuckDB | Descrição |
| :--- | :--- | :--- |
| `fixture_id` | `INTEGER` | Identificador único da partida |
| `date` | `TIMESTAMP` | Data e hora de início (UTC) |
| `status_short` | `VARCHAR` | Status da partida (`FT`, `NS`, `PST`, `CANC`, `1H`, `2H`, etc.) |
| `elapsed` | `INTEGER` | Minutos transcorridos |
| `league_id` | `INTEGER` | ID da competição |
| `league_name` | `VARCHAR` | Nome da competição |
| `season` | `INTEGER` | Temporada (ano) |
| `round` | `VARCHAR` | Fase/rodada da competição |
| `home_team_id` | `INTEGER` | ID da equipe mandante |
| `home_team_name` | `VARCHAR` | Nome da equipe mandante |
| `away_team_id` | `INTEGER` | ID da equipe visitante |
| `away_team_name` | `VARCHAR` | Nome da equipe visitante |
| `score_home` | `INTEGER` | Gols da equipe mandante (tempo regulamentar) |
| `score_away` | `INTEGER` | Gols da equipe visitante (tempo regulamentar) |
| `score_halftime_home` | `INTEGER` | Gols mandante no intervalo |
| `score_halftime_away` | `INTEGER` | Gols visitante no intervalo |
| `venue_name` | `VARCHAR` | Estádio da partida |
| `venue_city` | `VARCHAR` | Cidade do jogo |
| `observed_at` | `TIMESTAMP` | Momento da observação UTC |
| `snapshot_id` | `VARCHAR` | ID do snapshot |

### Tabela `standings`
| Coluna | Tipo DuckDB | Descrição |
| :--- | :--- | :--- |
| `league_id` | `INTEGER` | ID da competição |
| `season` | `INTEGER` | Temporada |
| `rank` | `INTEGER` | Posição na tabela |
| `team_id` | `INTEGER` | ID do clube |
| `team_name` | `VARCHAR` | Nome do clube |
| `points` | `INTEGER` | Pontuação acumulada |
| `goals_diff` | `INTEGER` | Saldo de gols |
| `group_name` | `VARCHAR` | Grupo / Chave |
| `description` | `VARCHAR` | Status de avanço / rebaixamento |
| `all_played` | `INTEGER` | Total de jogos |
| `all_win` | `INTEGER` | Total de vitórias |
| `all_draw` | `INTEGER` | Total de empates |
| `all_lose` | `INTEGER` | Total de derrotas |
| `observed_at` | `TIMESTAMP` | Momento da observação |
| `snapshot_id` | `VARCHAR` | ID do snapshot |
