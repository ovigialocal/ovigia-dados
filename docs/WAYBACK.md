---
okf_version: "0.2"
title: "Preservação com Wayback Machine"
description: "Módulo assíncrono de preservação de páginas de origem e evidências web via Save Page Now."
type: "documentation"
---

# Preservação com Wayback Machine (Internet Archive)

O módulo de preservação no Wayback Machine (`Save Page Now`) cria uma cópia pública e temporalmente estável de fontes já observadas pela Redação. **Ele não cria nem valida a evidência editorial; apenas aumenta sua durabilidade.**

A fila canônica é composta exclusivamente por concepts OKF `archive-request` em `knowledge/wayback/requests/`. A identidade pertence ao `concept_id` derivado pelo `okf-parser`; não existe fila paralela `.txt`, JSON ou YAML nem `request_id` redundante. Resultados terminais são concepts `archive-result` em `knowledge/wayback/results/` ligados à mesma request por `request_concept_id` e `sources[].resource`.

## Política de execução

A fila é semântica: todo `archive-request` sem `archive-result` terminal continua pendente. Cada execução do worker recompõe essa fila e tenta os pendentes, sem exigir alteração artificial do request e sem criar um segundo concept para a mesma URL.

O workflow é disparado por novos requests, mudanças materiais no worker, `workflow_dispatch` e também periodicamente. O disparo periódico existe para recuperar automaticamente requests pendentes, inclusive rate limits e falhas transitórias.

Runs são serializados pelo mesmo grupo de `concurrency`. O cliente respeita `Retry-After`/backoff e retries locais limitados. **Esgotar o orçamento local de retries não transforma um estado transitório em falha terminal.**

Uma execução periódica sem pendências ou sem novos resultados terminais é válida e não cria commit.

## Semântica de estados

São `pending/retryable`, portanto **não geram `archive-result(status=failed)`**:

- HTTP 429 (`Too Many Requests`), com ou sem `Retry-After`;
- HTTP 5xx transitório;
- DNS, timeout, socket, cancelamento de runner ou erro de cliente;
- ausência de secret/configuração antes de uma resposta terminal do IA;
- lookup de snapshot sem tentativa/captura concluída.

Nesses casos a request permanece sem resultado terminal e volta à fila em execução posterior.

Uma falha terminal só existe quando o Internet Archive rejeita definitivamente a captura de forma não transitória. Nesse caso, `archive-result(status=failed)` registra `failure.code` e `failure.detail` e não contém `archive_url`.

`archive-result(status=archived)` exige locator concreto `https://web.archive.org/web/...`. O locator não prova equivalência editorial: a Redação deve abrir o replay/snapshot e confirmar que ele representa materialmente o recurso usado antes de persistir a equivalência em sua `source-observation`.

## Relação com a Redação

Preservation é assíncrona. Uma request pendente **não bloqueia reporting, freeze, reviews, article-ready ou publicação**. A Redação pode publicar usando a origem viva observada e posteriormente enriquecer a provenance quando um snapshot equivalente for confirmado.

Apenas a insuficiência da própria observação factual pode bloquear o texto; esse é um problema de evidence/provenance, não de fila Wayback.

Para PDF, anexo ou documento material, preserve a URL exata do recurso efetivamente usado separadamente de qualquer landing page.
