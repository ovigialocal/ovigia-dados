# O Vigia — Dados (`ovigia-dados`)

Repositório público de infraestrutura de dados, coletores, normalização, catálogo SQL e detectores determinísticos do **O Vigia**.

---

## 1. O que é o `ovigia-dados`?

O `ovigia-dados` é a camada aberta de engenharia de dados do O Vigia. Ele é responsável por:
1. Adquirir e monitorar bases públicas governamentais e registros oficiais;
2. Preservar arquivos brutos e snapshots canônicos no [Internet Archive](https://archive.org);
3. Normalizar registros em esquemas analíticos consistentes no formato **Apache Parquet**;
4. Fornecer contratos de consulta SQL padronizados (`catalog.sql`) executáveis via [DuckDB](https://duckdb.org);
5. Executar detectores determinísticos para emitir **sinais factuais e reproduzíveis** de interesse público.

---

## 2. O que o `ovigia-dados` NÃO é (Separação Editorial)

* **NÃO é a Redação do O Vigia**: A Redação opera em repositório privado (`ovigia-redacao`) para proteger estratégias de apuração, hipóteses jornalísticas, apurações em andamento, fontes humanas e drafts confidenciais.
* **NÃO produz matérias ou acusações**: Detectores emitem sinais matemáticos e estatísticos (ex: *"contrato no percentil 99,4 do município nos últimos 24 meses"*). Eles nunca emitem conclusões de irregularidade, fraude ou juízo de valor.
* **`dataset atualizado != notícia`**: A chegada de um novo snapshot apenas acorda detectores determinísticos. Apenas jornalistas na Redação privada decidem se um sinal factual merece investigação editorial.

---

## 3. Arquitetura e Contrato de Dados

* **Storage Canônico**: [Internet Archive](https://archive.org) hospeda os snapshots imutáveis em Parquet, arquivos brutos e manifestos com checksum SHA-256.
* **Formato Analítico**: Apache Parquet com tipos explícitos, partições estáveis e metadados de observação.
* **Catálogo SQL Reconstruível**: `catalog.sql` permite consultar diretamente os arquivos remotos no Internet Archive via DuckDB sem baixar dumps proprietários de banco.
* **DuckDB como Motor**: DuckDB é o motor de consulta efêmero do pipeline e dos analistas, não um formato de distribuição canônico.
* **Preservação de Fontes Web**: O [Wayback Machine](https://web.archive.org) é acionado para preservar as páginas e portais governamentais de onde os dados foram extraídos.

---

## 4. Datasets Disponíveis

| Família | Descrição | Snapshot Canônico | Catálogo SQL |
| :--- | :--- | :--- | :--- |
| **Contratos Federais** (`contracts`) | Contratos e compras públicas federais (PNCP / Compras.gov.br / Transparência) | [`ovigia-dados-contratos-federais`](https://archive.org/details/ovigia-dados-contratos-federais) | [`datasets/contracts/catalog.sql`](datasets/contracts/catalog.sql) |

---

## 5. Como Consultar via DuckDB

Você pode consultar os datasets diretamente via DuckDB em sua máquina ou terminal SQL:

```sql
-- Exemplo: Consultar contratos de Porto Velho/RO diretamente do snapshot público
SELECT
    contract_id,
    contract_number,
    buyer_name,
    supplier_name,
    amount_current,
    signed_at,
    object
FROM read_parquet('https://archive.org/download/ovigia-dados-contratos-federais-2026-09/contracts.parquet')
WHERE uf = 'RO'
  AND municipality_name = 'Porto Velho'
ORDER BY amount_current DESC
LIMIT 10;
```

---

## 6. Detectores Determinísticos

Os detectores operam sobre os dados normalizados e produzem artefatos estruturados (`signals.jsonl` / `signals.parquet`).

* [`large-local-contract-v1`](datasets/contracts/detectors/large_local_contract_v1.py): Identifica contratos federais de magnitude atípica para municípios específicos (como Porto Velho/RO), combinando valor absoluto, percentil local histórico (12/24 meses), novidade de fornecedor e dispersão de categorias.

---

## 7. Workflows do GitHub Actions

1. **`wayback-save.yml`**: Salva URLs de referência e páginas de origem no Wayback Machine com User-Agent rastreável e backoff adaptativo.
2. **`etl-daily.yml`**: Orquestra a coleta diária, checagem de mudanças (`no_source_change`), normalização para Parquet, validação de integridade, publicação no Internet Archive e disparo de detectores.
3. **`ci.yml`**: Executa Ruff, suíte de testes com `pytest`, validação de schemas SQL DuckDB, manifestos e dicionários.

---

## Licença

[MIT](LICENSE)
