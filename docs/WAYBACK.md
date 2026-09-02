---
okf_version: "0.2"
title: "Preservação com Wayback Machine"
description: "Módulo de preservação de páginas de origem e evidências web via Save Page Now."
type: "documentation"
---

# Preservação com Wayback Machine (Internet Archive)

O módulo de preservação no Wayback Machine (`Save Page Now`) garante que páginas web, editais, termos de homologação e páginas de catálogo de dados públicos sejam capturados no momento exato em que serviram de evidência.

Cada arquivo novo ou alterado em `requests/wayback/*.txt` precisa gerar uma tentativa própria. Não serialize os runs com um único grupo global de `concurrency`: o GitHub Actions mantém no máximo um run pendente por grupo e pode cancelar um pendente anterior quando chega outro evento, mesmo com `cancel-in-progress: false`. Isso faria uma request versionada parecer enfileirada sem nunca alcançar o Internet Archive.

Runs de preservação podem, portanto, coexistir. O cliente trata `429` e erros transitórios com `Retry-After`/backoff, e a etapa de persistência de evidência já reconcilia corridas de escrita com `fetch` + `rebase` + retry. Falha local, cancelamento de runner ou indisponibilidade anterior a uma resposta do Internet Archive nunca deve ser registrada como `archive_failure`.
