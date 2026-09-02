# Contrato Padrão de Datasets

Todo dataset integrado ao `ovigia-dados` deve cumprir as diretrizes deste contrato.

---

## 1. Estrutura de Diretórios por Dataset

Cada família de dados possui uma pasta em `datasets/{nome_dataset}/`:

```text
datasets/{nome_dataset}/
├── README.md         # Contexto, órgão de origem, frequência e links oficiais
├── dictionary.md     # Dicionário formal de variáveis e tipos
├── schema.sql        # Esquema DDL DuckDB da tabela/view
├── catalog.sql       # Script de views remotas apontando para o Internet Archive
└── detectors/        # Detectores determinísticos associados à família
    ├── README.md
    └── {detector_name}.py
```

---

## 2. Requisitos de Metadados (`manifest.json`)

Todo snapshot de dados deve produzir um `manifest.json` contendo:
* `dataset_id`: Identificador canônico do dataset (ex: `contracts`);
* `snapshot_id`: Identificador temporal do snapshot (ex: `2026-09`);
* `source_url`: URL oficial da fonte;
* `observed_at`: Timestamp ISO 8601 do momento da coleta;
* `row_count`: Número total de registros normalizados;
* `sha256_parquet`: Checksum SHA-256 do arquivo Parquet gerado;
* `sha256_raw`: Checksum SHA-256 do arquivo bruto original (se houver);
* `schema_version`: Versão semântica do esquema de dados.
