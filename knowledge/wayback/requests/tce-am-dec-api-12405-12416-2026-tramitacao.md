---
okf_version: "0.2"
type: archive-request
source_url: "https://dec-api.tceam.tc.br/api/v1/consultas-publicas/processos/detalhes/tramitacao/4098882"
requested_at: "2026-09-24T13:26:33Z"
resource_kind: document
reason: material-source
---

Preservação do retorno da API pública do Domicílio Eletrônico de Contas (DEC) do TCE-AM com a tramitação do **Processo 12405/2026** (`idProcesso` 4098882), representação da SECEX contra a Inexigibilidade nº 003/2026 (ARP 0068/2026-1, CSC/AM – Fundagres).

Em 24/09/2026 o retorno registra 25 movimentos, sendo os dois mais recentes de 21/09/2026: DILCON → DIMP (Diretoria do Ministério Público de Contas) → 8.ª PROCONT, recebido em 22/09. Sustenta a atualização v3 da matéria `rondonia-seduc-ata-amazonas-inexigibilidade-2026` e a observação `knowledge/rondonia/sources/accountability/2026-09-24-tce-am-consulta-processual-12405-12416-mpc.md` da Redação.

A página pública `https://dec.tceam.tc.br/publico/processo/consulta` é aplicação JavaScript e o snapshot dela não reproduz os dados; por isso o locator preservado é o endpoint JSON. Endpoint equivalente do processo vinculado: `.../detalhes/tramitacao/4099312` (12416/2026). O host apresenta `502` e `connection reset` intermitentes.
