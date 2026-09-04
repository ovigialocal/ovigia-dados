---
okf_version: "0.2"
title: "Detectores Esportivos Locais (v1)"
description: "Detectores determinísticos para resultados esportivos e movimentações de tabela de clubes de Rondônia."
type: "detector"
edition_id: "porto-velho"
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
