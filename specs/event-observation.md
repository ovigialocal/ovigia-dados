---
okf_version: "0.2"
title: "Especificação de Observação de Evento"
description: "Define um estado público observado de um evento da agenda, preservado de forma append-only."
type: "specification"
target_type: "event-observation"
fields:
  event_id:
    type: string
    description: "Identificador estável do city-event observado."
  source_platform:
    type: string
    description: "Plataforma pública onde o estado foi observado."
  source_url:
    type: string
    description: "URL pública canônica consultada."
  observed_at:
    type: string
    description: "Timestamp ISO 8601 do estado observado."
  observation_origin:
    type: string
    description: "Origem da observação: live ou wayback."
  archive_timestamp:
    type: string
    description: "Timestamp CDX do snapshot quando observation_origin for wayback."
  content_hash:
    type: string
    description: "SHA-256 do estado público normalizado, usado para evitar observações redundantes."
  title:
    type: string
    description: "Título público do evento."
  starts_at:
    type: string
    description: "Data e hora de início publicadas, quando disponíveis."
  ends_at:
    type: string
    description: "Data e hora de término publicadas, quando disponíveis."
  venue_name:
    type: string
    description: "Nome do local publicado, quando disponível."
  address:
    type: string
    description: "Endereço público do evento, quando disponível."
  city:
    type: string
    description: "Município informado na página individual do evento."
  state:
    type: string
    description: "UF ou estado informado na página individual do evento."
  organizer:
    type: string
    description: "Organizador ou produtor publicado, quando disponível."
  status:
    type: string
    description: "Estado normalizado: scheduled, cancelled, postponed, rescheduled, completed ou unknown."
---

# Observação de evento

Cada `event-observation` preserva um estado público materialmente distinto do mesmo evento. A observação é append-only: alteração posterior de data, local, produtor ou status gera novo concept em vez de reescrever a observação anterior.

A rota geográfica usada para descobrir o evento não basta para afirmar que ele ocorre em Porto Velho. A localização precisa ser confirmada na página individual ou em evidência equivalente da própria fonte.
