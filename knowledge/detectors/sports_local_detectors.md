---
okf_version: "0.2"
title: "Detectores Esportivos Locais (v1)"
description: "Detectores determinísticos para resultados esportivos e movimentações de tabela de clubes de Rondônia."
type: "detector"
detector_id: "sports-local"
version: "1.0"
input_dataset: "sports"
scope: "Clubes de Rondônia (Porto Velho EC, Ji-Paraná, etc.)"
baseline_policy: "temporada corrente e confrontos diretos"
reason_codes:
  - "high_margin_victory"
  - "high_margin_defeat"
  - "high_scoring_match"
  - "league_leader"
  - "qualification_zone"
  - "relegation_zone"
---

# Detectores Esportivos: `sports-local-v1`

Detecta eventos esportivos objetivamente relevantes sem transformar jogos corriqueiros em matéria automática.

## Fronteira com a Redação

Cada sinal novo é materializado de forma idempotente como concept OKF `signal` em `knowledge/sports/leads/<snapshot>/`. O concept preserva detector, `reason_codes`, entidade, competição, temporada, métricas e snapshot de origem.

Esses concepts são uma caixa de entrada pública de **leads**, não matérias. A Redação privada decide se vale reapurar e deve procurar fonte primária, estado temporal, regra da competição e contexto antes de qualquer publicação. Um sinal já persistido nunca é reescrito por execução posterior; observação nova recebe sua própria identidade temporal.

## Registry monitorado

Regiões, competições e equipes acompanhadas são autoradas em `knowledge/sports/registry/` como concepts `sports-monitor`. Não existe registry JSON autorado paralelo; qualquer projeção estrutural deve ser derivada desses concepts.
