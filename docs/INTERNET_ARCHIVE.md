# Guia de Integração com o Internet Archive

O **Internet Archive** (`archive.org`) é a camada de armazenamento primário e distribuição canônica de todos os snapshots públicos do `ovigia-dados`.

---

## 1. Convenção de Identificadores (Item Identifiers)

Os itens no Internet Archive seguem o formato padronizado:

```text
ovigia-dados-{dataset_name}-{period}
```

Exemplos:
* `ovigia-dados-contratos-federais-2026-09` (snapshot mensal de compras federais)
* `ovigia-dados-contratos-federais-catalog` (catálogo SQL consolidado e manifesto de contratos)
* `ovigia-dados-cnes-2026-09` (estabelecimentos de saúde e leitos)

---

## 2. Artefatos Publicados por Item

Para cada item publicado, os seguintes arquivos devem estar presentes:
1. `{dataset}.parquet`: Dataset normalizado em formato Apache Parquet.
2. `raw/{raw_filename}.zip` ou `.csv.gz`: Arquivo bruto original para fins de auditoria de proveniência (quando aplicável).
3. `manifest.json`: Manifesto de integridade com metadados, contagem de linhas e SHA-256.
4. `dictionary.md`: Dicionário semântico dos campos.
5. `catalog.sql`: Script SQL DuckDB para mapear as views remotas.

---

## 3. Credenciais e Segurança

* **`IA_ACCESS_KEY`**: Chave de acesso S3 da API do Internet Archive.
* **`IA_SECRET_KEY`**: Chave secreta S3 da API do Internet Archive.

Ambas as credenciais devem ser configuradas exclusivamente como **GitHub Secrets** no repositório (`Settings > Secrets and variables > Actions`).

Nunca inclua credenciais em código ou arquivos de configuração versionados.

---

## 4. Idempotência e Imutabilidade

* Uma vez publicado um snapshot mensal/histórico, ele deve ser considerado imutável.
* Tentativas de publicação redundante no mesmo item são idempotentes: o script valida se os checksums SHA-256 coincidem antes de realizar o upload.
