---
okf_version: "0.2"
title: "Especificação de Detector Determinístico"
description: "Define um detector determinístico de sinais factuais e matemáticos sobre dados normalizados."
type: "specification"
target_type: "detector"
fields:
  detector_id:
    type: string
    description: "Identificador do detector (ex: large-local-contract)."
  edition_id:
    type: string
    description: "Edição pública que consome prioritariamente os sinais; deve existir no registry canônico do site."
  version:
    type: string
    description: "Versão do algoritmo de detecção."
  input_dataset:
    type: string
    description: "Dataset sobre o qual o detector opera."
  scope:
    type: string
    description: "Recorte geográfico ou setorial prioritário."
  baseline_policy:
    type: string
    description: "Requisito mínimo de histórico para cálculo de percentil ou ranking."
  reason_codes:
    type: list
    description: "Códigos de razão objetivos que podem ser emitidos."
---

# Especificação: Detector Determinístico

Contrato de regras determinísticas. Detectores produzem sinais reproduzíveis e nunca matérias prontas ou juízos de valor editorial.
