---
okf_version: "0.2"
title: "Especificação de Entidade Canônica de Evento"
description: "Define uma identidade consolidada para um evento real quando duas ou mais fontes públicas são reconciliadas."
type: "specification"
target_type: "event-entity"
fields:
  canonical_event_id:
    type: string
    description: "Identificador estável da entidade consolidada."
  member_event_ids:
    type: array
    description: "city-event source-specific atualmente ligados a esta entidade."
  created_at:
    type: string
    description: "Timestamp ISO 8601 UTC da primeira consolidação."
  updated_at:
    type: string
    description: "Timestamp ISO 8601 UTC da última alteração de membros."
---

# Entidade canônica de evento

`event-entity` representa o evento real acima das identidades de cada plataforma. O identificador nasce quando a primeira equivalência automática é estabelecida e permanece estável quando novas fontes são adicionadas ao mesmo grupo.

A lista de membros pode crescer conforme surgem novas evidências. Observações e reconciliações antigas permanecem preservadas, inclusive quando fontes divergem sobre data, local ou status.
