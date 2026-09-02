---
okf_version: "0.2"
title: "Especificação de Dataset"
description: "Define uma família de dados públicos adquirida, normalizada e publicada pelo O Vigia."
type: "specification"
target_type: "dataset"
fields:
  dataset_id:
    type: string
    description: "Identificador canônico estável do dataset."
  title:
    type: string
    description: "Nome oficial do dataset."
  publisher:
    type: string
    description: "Entidade ou órgão governamental produtor da base."
  source_url:
    type: string
    description: "URL da fonte primária pública."
  observation_unit:
    type: string
    description: "Unidade atômica de cada registro na tabela."
  stable_key:
    type: string
    description: "Identificador estável ou chave composta primária."
  schema_version:
    type: string
    description: "Versão semântica do esquema de dados."
  storage_policy:
    type: string
    description: "Política de retenção e publicação no Internet Archive."
  cadence:
    type: string
    description: "Frequência esperada de atualização na origem."
---

# Especificação: Dataset

Define o contrato semântico obrigatório para qualquer família de dados incorporada ao repositório `ovigia-dados`.
