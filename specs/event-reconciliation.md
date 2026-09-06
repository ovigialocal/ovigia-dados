---
okf_version: "0.2"
title: "Especificação de Reconciliação de Evento"
description: "Registra a evidência de que dois city-event de fontes diferentes representam o mesmo evento real ou precisam de revisão."
type: "specification"
target_type: "event-reconciliation"
fields:
  reconciliation_id:
    type: string
    description: "Identificador determinístico da comparação entre dois eventos source-specific."
  left_event_id:
    type: string
    description: "Primeiro city-event comparado."
  right_event_id:
    type: string
    description: "Segundo city-event comparado."
  decision:
    type: string
    description: "Resultado da regra: equivalent ou review."
  score:
    type: number
    description: "Pontuação agregada de similaridade entre 0 e 1."
  title_similarity:
    type: number
    description: "Similaridade normalizada dos títulos entre 0 e 1."
  same_local_date:
    type: boolean
    description: "Indica se as duas fontes publicam a mesma data local de início."
  venue_similarity:
    type: number
    description: "Similaridade do local quando ambos o publicam."
  organizer_similarity:
    type: number
    description: "Similaridade do organizador quando ambos o publicam."
  evaluated_at:
    type: string
    description: "Timestamp ISO 8601 UTC em que a reconciliação foi materializada."
---

# Reconciliação de evento

`event-reconciliation` é evidência derivada e reproduzível. Ele nunca substitui as observações originais. A decisão `equivalent` pode alimentar uma identidade `event-entity`; a decisão `review` mantém a ambiguidade explícita para revisão posterior.
