---
okf_version: "0.2"
title: "Preservação com Wayback Machine"
description: "Módulo de preservação de páginas de origem e evidências web via Save Page Now."
type: "documentation"
---

# Preservação com Wayback Machine (Internet Archive)

O módulo de preservação no Wayback Machine (`Save Page Now`) garante que páginas web, editais, termos e outros recursos públicos usados como evidência possam ser preservados por uma fronteira operacional pública.

A fila canônica é composta exclusivamente por concepts OKF `archive-request` em `knowledge/wayback/requests/`. A identidade pertence ao `concept_id` derivado pelo `okf-parser`; não existe fila paralela `.txt`, JSON ou YAML nem `request_id` redundante. Resultados terminais são concepts `archive-result` em `knowledge/wayback/results/` ligados à mesma request por `request_concept_id` e `sources[].resource`.

## Política de execução

A fila é semântica: todo `archive-request` sem `archive-result` terminal continua pendente. Cada execução do worker recompõe essa fila e tenta os pendentes, sem exigir alteração artificial do request e sem criar um segundo concept para a mesma URL.

O workflow é disparado por novos requests, mudanças materiais no worker, `workflow_dispatch` e também periodicamente. O disparo periódico existe para recuperar automaticamente requests que permaneceram pendentes por DNS, timeout, socket, runner ou outra falha de infraestrutura anterior a uma resposta do Internet Archive.

Runs são serializados pelo mesmo grupo de `concurrency`. O cliente trata `429` e erros transitórios que alcançam o IA com `Retry-After`/backoff, e a etapa de persistência reconcilia corridas de escrita com `fetch` + `rebase` + retry.

Uma execução periódica sem pendências ou sem novos resultados terminais é válida e não cria commit.

## Semântica de falha

Falha local, timeout, DNS, socket, cancelamento de runner ou indisponibilidade anterior a uma resposta do Internet Archive deixa a request pendente e nunca deve ser registrada como `archive-result(status=failed)` ou `archive_failure` editorial. O worker voltará a tentar a mesma identidade em execução posterior.

Uma falha terminal só existe quando a tentativa alcançou o Internet Archive e recebeu resultado terminal compatível com o contrato. Nesse caso, `archive-result(status=failed)` registra `failure.code` e `failure.detail` e não contém `archive_url`.

`archive-result(status=archived)` exige locator concreto `https://web.archive.org/web/...`. O locator não prova equivalência editorial: a Redação deve abrir o replay/snapshot e confirmar que ele representa materialmente o recurso usado antes de persistir a equivalência em sua `source-observation`.

Para PDF, anexo ou documento material, preserve a URL exata do recurso efetivamente usado separadamente de qualquer landing page.
