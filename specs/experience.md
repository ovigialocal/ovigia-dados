---
okf_version: "0.2"
title: "Especificação de Experience"
description: "Representa uma execução observada e suas evidências imutáveis como entrada do loop WikiSkill."
type: "specification"
target_type: "experience"
fields:
  occurred_at:
    type: string
    description: "Instante ISO-8601 da experiência."
  operation:
    type: string
    description: "Operação, coletor, detector ou procedimento executado."
  outcome:
    type: string
    description: "Resultado factual da execução."
  evidence_refs:
    type: list
    description: "Referências para evidências imutáveis, como snapshots, manifests, logs ou testes."
  skill_refs:
    type: list
    description: "Skills e versões usadas durante a execução."
  reusable_observations:
    type: list
    description: "Observações potencialmente generalizáveis extraídas da experiência."
---

# Especificação: `experience`

Uma experiência é um nó semântico que referencia evidência; ela não substitui nem reescreve a evidência bruta.
