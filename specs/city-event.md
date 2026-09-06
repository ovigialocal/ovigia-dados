---
okf_version: "0.2"
title: "Especificação de Evento da Cidade"
description: "Define a identidade estável de um evento público descoberto para a agenda de Porto Velho."
type: "specification"
target_type: "city-event"
fields:
  event_id:
    type: string
    description: "Identificador canônico estável; para Sympla usa sympla-<id numérico>."
  source_platform:
    type: string
    description: "Plataforma ou fonte que fornece a identidade estável do evento."
  source_url:
    type: string
    description: "URL pública canônica do evento."
  first_seen_at:
    type: string
    description: "Timestamp ISO 8601 UTC da primeira observação materializada pelo O Vigia."
---

# Evento da cidade

O concept `city-event` representa identidade, não o estado mutável da programação.
Alterações de data, local, produtor ou status ficam em concepts `event-observation`, preservando a série histórica do evento sem reescrever o passado.
