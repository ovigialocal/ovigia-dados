# Fontes de agenda de Porto Velho

## Objetivo

O `ovigia-dados` mantém aquisição pública e reproduzível de eventos relevantes para uma agenda da cidade. A camada de dados registra o que cada fonte publicou e como esse estado mudou; relevância editorial, pauta e linguagem de publicação continuam fora deste repositório público.

## Sympla

Fonte de descoberta inicial:

- `https://www.sympla.com.br/eventos/porto-velho-ro/para-voce`

Observação de 2026-09-05 mostrou que a listagem pública expõe links de eventos no HTML e que páginas individuais publicam informação suficiente para hidratar parte importante da agenda, incluindo título, datas e localização. O identificador numérico no fim da URL individual é tratado como identidade estável da plataforma: `sympla-<id>`.

A rota de Porto Velho é uma superfície de **discovery**, não prova final de localização. O coletor confirma `city`/`state` na página individual e descarta da agenda automática itens cuja ocorrência em Porto Velho não possa ser verificada pela própria página. Isso protege contra recomendações amplas, eventos online ou resultados geograficamente misturados.

### Procedimento de aquisição

1. consultar a listagem pública da cidade;
2. extrair apenas URLs canônicas `/evento/.../<id>` e remover query strings de tracking;
3. hidratar cada página individual;
4. preferir JSON-LD `Event` quando publicado;
5. usar o HTML server-rendered como fallback conservador para título, datas e localização explícita;
6. confirmar Porto Velho na página individual;
7. materializar uma identidade `city-event` uma única vez;
8. calcular hash do estado normalizado e criar `event-observation` somente quando houver mudança material.

O hash considera o estado público do evento, não o horário em que o coletor o viu. Assim, uma coleta idêntica não produz ruído, enquanto mudança de data, local, organizador ou status produz nova observação append-only.

## Wayback/CDX como memória e backfill

O Internet Archive complementa a coleta live em duas funções:

- recuperar URLs de eventos vistas em snapshots antigos da listagem de Porto Velho;
- reconstruir o último estado arquivado de uma página individual que já não aparece na listagem atual.

O coletor usa o índice CDX em `https://web.archive.org/cdx/search/cdx`, limita a respostas HTTP 200 e colapsa snapshots pelo digest. Replay é lido em modo `id_` para obter o recurso arquivado sem depender da interface visual do Wayback.

Wayback não é pré-requisito da descoberta live. Falha do CDX ou ausência de snapshot não invalida a observação pública feita diretamente na Sympla. Da mesma forma, a existência de um snapshot não transforma automaticamente a página em fonte material de uma matéria; preservação editorial segue o contrato próprio da fila `archive-request` quando aquela URL efetivamente sustentar publicação.

## Limites deliberados

- O coletor não depende de GraphQL, XHR ou endpoints internos não documentados da Sympla.
- A API oficial de produtores da Sympla não é usada como catálogo geral da cidade.
- Evento sem localização verificável em Porto Velho não entra automaticamente na agenda local.
- Identidade entre plataformas diferentes não é inferida apenas por semelhança de título; reconciliação futura deve usar data, local, organizador e outras evidências.
- O estado `unknown` é preferível a inventar status quando o HTML não o publica de forma confiável.

## Próximas fontes da agenda

A mesma arquitetura deve acomodar adaptadores independentes para outras fontes, mantendo identidade e provenance de cada origem:

- PVH Mais / Eventos;
- Funcultural;
- Semtel;
- Sesc Rondônia e suas unidades em Porto Velho;
- SESI Rondônia / FIERO;
- UNIR;
- IFRO;
- plataformas adicionais de ingressos e produtores quando oferecerem páginas públicas verificáveis.

A reconciliação entre fontes deve produzir evidência acumulativa, não apagar observações anteriores quando duas páginas divergem.
