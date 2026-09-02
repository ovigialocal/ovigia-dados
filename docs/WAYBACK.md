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

Um push que adiciona requests tenta somente os `archive-request` incluídos naquele push. Isso impede que uma URL nova espere atrás de retries de todo o backlog histórico antes que seu resultado possa ser persistido.

`workflow_dispatch` é a operação explícita de recuperação: ela drena toda a fila pendente e pode ser usada para repetir requests que permaneceram sem resultado terminal por falha de infraestrutura anterior.

Alterações apenas de código, testes, documentação ou workflow não fazem uma nova tentativa contra todas as URLs pendentes. O CI valida essas mudanças separadamente.

Runs de preservação podem coexistir. O cliente trata `429` e erros transitórios com `Retry-After`/backoff, e a etapa de persistência de resultados reconcilia corridas de escrita com `fetch` + `rebase` + retry.

## Semântica de falha

Falha local, timeout, DNS, socket, cancelamento de runner ou indisponibilidade anterior a uma resposta do Internet Archive deixa a request pendente e nunca deve ser registrada como `archive-result(status=failed)` ou `archive_failure` editorial. Uma falha terminal só existe quando a tentativa alcançou o Internet Archive e recebeu resultado terminal compatível com o contrato.

Para PDF, anexo ou documento material, preserve a URL exata do recurso efetivamente usado separadamente de qualquer landing page.
