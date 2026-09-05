---
okf_version: "0.2"
title: "Especificação de entidade monitorada no esporte"
description: "Define regiões, competições e equipes que o pipeline esportivo acompanha como fonte de verdade autorada em OKF."
type: "specification"
target_type: "sports-monitor"
fields:
  entity_kind:
    type: string
    description: "Classe da entidade: region, competition ou team."
  external_id:
    type: string
    description: "Identificador estável na fonte externa quando aplicável."
  name:
    type: string
    description: "Nome público da entidade."
  priority:
    type: string
    description: "Prioridade editorial/operacional quando aplicável."
  city:
    type: string
    description: "Município relacionado, quando aplicável."
  uf:
    type: string
    description: "UF relacionada, quando aplicável."
  municipality_code:
    type: string
    description: "Código IBGE quando a entidade é uma região monitorada."
  is_local_focus:
    type: string
    description: "Booleano textual preservado pelo OKF indicando foco local."
---

# Entidades esportivas monitoradas

Cada região, competição e equipe acompanhada pelo pipeline esportivo é um concept Markdown próprio. Estes concepts são a fonte de verdade autorada; artefatos JSON eventualmente produzidos são apenas projeções geradas.
