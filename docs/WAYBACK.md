# Preservação com Wayback Machine (Internet Archive)

O módulo de preservação no Wayback Machine (`Save Page Now`) garante que páginas web, editais, termos de homologação e páginas de catálogo de dados públicos sejam capturados no momento exato em que serviram de evidência.

---

## 1. Princípios de Uso

* **Preservação de Evidência**: Páginas HTML, documentações de APIs e notas técnicas de órgãos oficiais devem ser salvas no Wayback.
* **User-Agent Identificável**: Todas as requisições utilizam o User-Agent oficial:
  ```text
  OVigiaDados/0.1.0 (+https://github.com/ovigialocal/ovigia-dados; contato@ovigia.local)
  ```
* **Respeito a Rate Limits**:
  * Resposta HTTP `429 Too Many Requests`: Respeita o cabeçalho `Retry-After` ou aplica backoff exponencial.
  * Nunca insiste em loop fechado contra os servidores do Internet Archive.

---

## 2. Modos de Invocação

### 2.1 Linha de Comando (CLI via PEP 723)
```bash
# Salvar uma URL avulsa
uv run scripts/wayback/save.py --url "https://pncp.gov.br"

# Salvar lote a partir de arquivo de texto
uv run scripts/wayback/save.py --file urls.txt --output-report report.json
```

### 2.2 GitHub Actions (`wayback-save.yml`)
O workflow pode ser acionado:
1. Manualmente via `workflow_dispatch` informando uma URL;
2. Por chamadas de outros workflows via `workflow_call`;
3. Recebendo arquivos de links gerados por coletores.
