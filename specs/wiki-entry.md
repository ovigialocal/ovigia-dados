---
okf_version: "0.2"
title: "Especificação de Wiki Entry"
description: "Conhecimento persistente consolidado a partir de experiências verificáveis."
type: "specification"
target_type: "wiki-entry"
fields:
  topic:
    type: string
    description: "Tema estável da entrada de conhecimento."
  evidence_refs:
    type: list
    description: "Experiências e evidências que sustentam a consolidação."
  claims:
    type: list
    description: "Lições ou fatos operacionais reutilizáveis."
  confidence:
    type: string
    description: "Estado qualitativo da consolidação, sem substituir evidência."
  supersedes:
    type: list
    description: "Entradas anteriores substituídas ou refinadas."
---

# Especificação: `wiki-entry`

A wiki é memória persistente e cumulativa. Uma skill pode ser revertida; uma lição bem sustentada permanece e pode ser refinada por novas experiências.
