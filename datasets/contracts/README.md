# Dataset: Contratos e Compras Públicas Federais (`contracts`)

Este dataset consolida contratos administrativos, termos aditivos e compras públicas realizadas por órgãos da administração direta, autárquica e fundacional do Governo Federal do Brasil.

---

## 1. Fontes de Dados

1. **PNCP (Portal Nacional de Contratações Públicas)**:
   * Portal canônico criado pela Lei Federal nº 14.133/2021.
   * Endpoint de API aberta: `https://pncp.gov.br/api/consulta/v1/contratos`
2. **Compras.gov.br / Portal da Transparência (CGU)**:
   * Dados históricos legados e consolidados mensais de compras públicas federais.

---

## 2. Formato de Armazenamento

* **Arquivo**: `contracts.parquet`
* **Storage Canônico**: `https://archive.org/details/ovigia-dados-contratos-federais-{snapshot}`
* **Schema**: Versão 1.0 (declarado em `schema.sql` e `dictionary.md`)

---

## 3. Consulta Rápida via DuckDB

Execute localmente ou aponte para a view canônica em [`catalog.sql`](catalog.sql):

```sql
SELECT
    contract_number,
    buyer_name,
    supplier_name,
    amount_current,
    signed_at,
    object
FROM read_parquet('https://archive.org/download/ovigia-dados-contratos-federais-2026-09/contracts.parquet')
WHERE uf = 'RO' AND municipality_name = 'Porto Velho'
ORDER BY amount_current DESC
LIMIT 5;
```
