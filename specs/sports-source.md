---
okf_version: "0.2"
title: "Especificação de fonte esportiva"
description: "Catálogo de superfícies públicas usadas para agenda, resultado, contexto e dados abertos complementares."
type: "specification"
target_type: "sports-source"
fields:
  source_kind:
    type: string
    description: "Classe da fonte, como organizer_schedule, organizer_registry, team_page ou open_dataset."
  authority:
    type: string
    description: "Papel da fonte: primary, first_party_complementary ou open_data_complementary."
  scope:
    type: string
    description: "Escopo semântico da fonte: competition, team, registry ou dataset."
  entity_name:
    type: string
    description: "Competição, equipe, catálogo ou dataset representado."
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
  license:
    type: string
    description: "Licença declarada pela fonte quando aplicável."
  enabled:
    type: string
    description: "Booleano textual para fontes de coleta ou auditoria automática."
---

# Fontes esportivas

Cada superfície relevante é um concept próprio para que descoberta, autoridade, licença e URL não fiquem enterradas em código. Fontes `primary` pertencem à entidade organizadora da competição. Fontes `first_party_complementary` pertencem aos clubes e servem para confirmação/contexto. Fontes `open_data_complementary` podem enriquecer histórico e normalização, mas sua cobertura deve ser medida antes de uso operacional e nunca substitui a organizadora em conflito de fixture.
