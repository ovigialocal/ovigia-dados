---
okf_version: "0.2"
title: "Especificação de Snapshot de Dataset"
description: "Define a ocorrência de uma observação imutável de uma competência ou extração de dados."
type: "specification"
target_type: "dataset-snapshot"
fields:
  dataset_id:
    type: string
    description: "Identificador do dataset ao qual o snapshot pertence."
  snapshot_id:
    type: string
    description: "Identificador único da competência ou data da coleta."
  observed_at:
    type: string
    description: "Timestamp ISO 8601 UTC do momento da observação."
  source_url:
    type: string
    description: "URL exata consultada no momento da coleta."
  row_count:
    type: integer
    description: "Contagem total de registros do snapshot."
  parquet_sha256:
    type: string
    description: "Hash SHA-256 do arquivo Apache Parquet gerado."
  schema_version:
    type: string
    description: "Versão do schema no momento da geração."
  archive_item:
    type: string
    description: "Identificador do item no Internet Archive onde o snapshot foi publicado."
---

# Especificação: Snapshot de Dataset

Documenta a proveniência imutável e a integridade de um snapshot arquivado no Internet Archive.
