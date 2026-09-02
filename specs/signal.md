---
okf_version: "0.2"
title: "Especificação de Sinal Factual"
description: "Define a estrutura de um sinal factual emitido por um detector determinístico."
type: "specification"
target_type: "signal"
fields:
  signal_id:
    type: string
    description: "Identificador único do sinal."
  detector_id:
    type: string
    description: "Detector que gerou o sinal."
  observed_at:
    type: string
    description: "Timestamp ISO 8601 UTC do momento da emissão."
  entity_type:
    type: string
    description: "Tipo da entidade envolvida (ex: contract, team, player)."
  entity_id:
    type: string
    description: "Identificador da entidade na origem."
  reason_codes:
    type: list
    description: "Lista de códigos determinísticos satisfeitos."
  source_snapshot:
    type: string
    description: "Identificador do snapshot de dados que originou o sinal."
---

# Especificação: Sinal Factual

Documenta o formato canônico de saída dos detectores do `ovigia-dados` para consumo pela redação privada (`ovigia-redacao`).
