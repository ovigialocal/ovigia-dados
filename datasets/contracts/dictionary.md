---
okf_version: "0.2"
title: "Dicionário de Dados: Contratos Federais"
description: "Dicionário formal de tipos e campos da tabela contracts."
type: "documentation"
---

# Dicionário de Dados: `contracts` (v1.0)

| Coluna | Tipo SQL (DuckDB) | Tipo PyArrow | Descrição Semântica | Nulabilidade |
| :--- | :--- | :--- | :--- | :--- |
| `contract_id` | `VARCHAR` | `string` | Identificador único estável do contrato (composto por sistema + ID de origem) | NÃO NULO |
| `source_system` | `VARCHAR` | `string` | Sistema de origem dos dados (`PNCP`, `COMPRASGOV`, `TRANSPARENCIA`) | NÃO NULO |
| `source_url` | `VARCHAR` | `string` | Link público do contrato no portal oficial | NULÁVEL |
| `contract_number` | `VARCHAR` | `string` | Número do contrato informado pelo órgão contratante | NULÁVEL |
| `buyer_name` | `VARCHAR` | `string` | Razão social ou denominação do órgão/unidade compradora | NÃO NULO |
| `buyer_document` | `VARCHAR` | `string` | CNPJ ou código identificador do órgão comprador | NULÁVEL |
| `supplier_name` | `VARCHAR` | `string` | Nome empresarial ou razão social da empresa fornecedora/contratada | NÃO NULO |
| `supplier_document` | `VARCHAR` | `string` | CNPJ ou CPF do fornecedor contratado (com zeros à esquerda) | NULÁVEL |
| `object` | `VARCHAR` | `string` | Descrição factual do objeto do contrato / termo | NULÁVEL |
| `amount_initial` | `DOUBLE` | `float64` | Valor inicial pactuado no contrato (em R$) | NULÁVEL |
| `amount_current` | `DOUBLE` | `float64` | Valor atual consolidado (incluindo termos aditivos e repactuações) | NÃO NULO |
| `signed_at` | `DATE` | `date32` | Data de assinatura do instrumento contratual (YYYY-MM-DD) | NULÁVEL |
| `starts_at` | `DATE` | `date32` | Data de início da vigência do contrato (YYYY-MM-DD) | NULÁVEL |
| `ends_at` | `DATE` | `date32` | Data de término da vigência do contrato (YYYY-MM-DD) | NULÁVEL |
| `municipality_code` | `VARCHAR` | `string` | Código do município IBGE (7 dígitos) | NULÁVEL |
| `municipality_name` | `VARCHAR` | `string` | Nome oficial do município do comprador ou local de execução | NULÁVEL |
| `uf` | `VARCHAR` | `string` | Sigla da Unidade Federativa (2 letras, ex: `RO`) | NULÁVEL |
| `observed_at` | `TIMESTAMP` | `timestamp[us]` | Timestamp UTC no momento da coleta e observação pelo pipeline | NÃO NULO |
| `snapshot_id` | `VARCHAR` | `string` | Identificador da competência/snapshot canônico (ex: `2026-09`) | NÃO NULO |
