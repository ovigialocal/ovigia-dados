---
okf_version: "0.2"
title: "Especificação de fonte esportiva"
description: "Catálogo de superfícies públicas oficiais usadas para agenda, resultado e contexto de primeira parte."
type: "specification"
target_type: "sports-source"
fields:
  source_kind:
    type: string
    description: "Classe da fonte, como organizer_schedule, organizer_registry ou team_page."
  authority:
    type: string
    description: "Papel da fonte: primary para organizadora ou first_party_complementary para clube."
  scope:
    type: string
    description: "Escopo semântico da fonte: competition, team ou registry."
  entity_name:
    type: string
    description: "Competição, equipe ou catálogo representado."
  url:
    type: string
    description: "URL pública canônica observada."
  agenda_url:
    type: string
    description: "URL específica de agenda/resultados quando diferente da página principal."
  competition:
    type: string
    description: "Competição relacionada quando aplicável."
  season:
    type: string
    description: "Temporada relacionada quando aplicável."
  parser:
    type: string
    description: "Adaptador determinístico usado para fonte estruturada quando aplicável."
  enabled:
    type: string
    description: "Booleano textual para fontes de coleta automática."
---

# Fontes esportivas

Cada superfície oficial relevante é um concept próprio para que descoberta, autoridade e URL não fiquem enterradas em código. Fontes `primary` pertencem à entidade organizadora da competição. Fontes `first_party_complementary` pertencem aos clubes e servem para confirmação/contexto, sem substituir a organizadora em conflito de fixture.
