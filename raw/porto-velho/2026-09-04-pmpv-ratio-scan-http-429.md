# Evidência imutável — varredura PMPV bloqueada por HTTP 429

- observado em: 2026-09-04T00:23:25.502101Z
- endpoint: https://api.portovelho.ro.gov.br/api/v1/contratos
- operação pretendida: varredura paginada de razões monetárias 10/100/1000 entre contrato e licitação associada
- resultado: `blocked_external`
- código: `http-429`
- detalhe observado: `PMPV API returned HTTP 429 Too Many Requests`
- workflow de evidência: `33821550366`
- artifact: `pmpv-ratio-scan`
- artifact digest: `sha256:ff6d482d24db5bcfccdcdd16eebfd1af1128d544cdb80d2f17cb957b44bbfcad`

## Conteúdo do artifact

```json
{
  "contracts_source_url": "https://api.portovelho.ro.gov.br/api/v1/contratos",
  "failure": {
    "code": "http-429",
    "detail": "PMPV API returned HTTP 429 Too Many Requests"
  },
  "observed_at": "2026-09-04T00:23:25.502101+00:00",
  "status": "blocked_external"
}
```

## Interpretação operacional

A execução chegou ao serviço PMPV e recebeu uma resposta HTTP 429 antes de obter a primeira página do universo. Portanto esta execução **não mediu prevalência**, não é evidência de ausência de sinais e não deve ser convertida em resultado editorial negativo.

O CI de código permanece separado da disponibilidade da fonte: lint, testes, schemas e validação OKF podem passar enquanto o probe vivo registra explicitamente o bloqueio externo. Uma exceção determinística de código continua reprovando a execução.
