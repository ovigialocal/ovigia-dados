---
okf_version: "0.2"
title: "Especificação de Evento da Cidade por Fonte"
description: "Define a identidade estável de um evento dentro de uma fonte pública da agenda de Porto Velho."
type: "specification"
target_type: "city-event"
fields:
  event_id:
    type: string
    description: "Identificador estável dentro da fonte, por exemplo sympla-<id> ou pvhmais-<id>."
  source_platform:
    type: string
    description: "Plataforma ou fonte que fornece esta identidade source-specific."
  source_url:
    type: string
    description: "URL pública canônica do evento naquela fonte."
  first_seen_at:
    type: string
    description: "Timestamp ISO 8601 UTC da primeira observação materializada pelo O Vigia."
---

# Evento da cidade por fonte

O concept `city-event` representa a identidade estável que uma fonte pública atribui ao evento. Ele não afirma sozinho que dois registros de plataformas diferentes sejam o mesmo evento real.

Alterações de data, local, produtor ou status ficam em concepts `event-observation`. Equivalências entre `city-event` de fontes diferentes são registradas separadamente em `event-reconciliation`, e identidades consolidadas ficam em `event-entity`.
