# Observação imutável — PMPV API `GET /contratos`

- observado em: 2026-09-03T21:32:00Z
- catálogo oficial: https://dados.portovelho.ro.gov.br/dataset/api-contratos
- endpoint observado: https://api.portovelho.ro.gov.br/api/v1/contratos
- método: GET
- autenticação na observação: nenhuma

## Contrato do endpoint no CKAN

O dataset oficial `Contratos` documentava `endpoint_path: /contratos`, `http_method: GET`, `operation_id: v1.contratos.` e resposta HTTP 200 `application/json` paginada de `ContratoResource`.

Parâmetros de consulta documentados: `ano`, `secretaria`, `modelo`, `vigencia`, `classificacao`, `por-pagina`, `contratante`, `situacao`, `categoria`.

## Forma observada da resposta viva

A resposta pública continha `data`, `links` e `meta`. Registros de `data` expunham campos como `id`, `numero`, `numero_processo`, `valor`, `valor_executado`, `contratante`, `fornecedor`, `licitacao`, `arquivos`, `empenhos`, `itens`, `created_at` e `updated_at`.

### Recorte material: contrato id 4285

O registro relativo a uma ambulância da SEMUSA apresentava, na mesma resposta:

```text
id = 4285
numero = CONTRATO Nº20/2026/DEJ/CGAF/SEMUSA
numero_processo = 005.002970/2026-47
valor.value = 341869
valor.brl = R$ 341.869,00
arquivo[0].valor.value = 341869
licitacao.id = 8678
licitacao.valor_estimado.value = 385780
licitacao.valor_contratado.value = 341869000
licitacao.valor_contratado.brl = R$ 341.869.000,00
```

O objeto do contrato informa aquisição de uma ambulância para a Maternidade Municipal Mãe Esperança. A divergência entre `valor.value` e `licitacao.valor_contratado.value` é exatamente fator 1.000.

## Interpretação permitida

Esta evidência demonstra que uma divergência ×1000 aparece dentro de uma resposta oficial da PMPV API em um segundo objeto, além do caso já observado do Contrato 027 na superfície de transparência. Não demonstra ainda qual sistema ou transformação introduziu o fator, nem que o valor divergente seja usado contabilmente.

A apuração deve confrontar o registro individual da licitação, instrumento contratual, empenhos e outras ocorrências antes de descrever causa ou abrangência sistêmica.
