---
okf_version: "0.2"
title: "Dataset: Futebol Regional e Nacional"
description: "Documentação do dataset esportivo com fontes oficiais como autoridade de agenda e resultado."
type: "documentation"
---

# Datasets esportivos (`sports`)

A fonte primária de agenda e resultado é a entidade organizadora da competição. Para Rondônia, o primeiro coletor oficial lê a tabela pública da **FFER**; competições nacionais devem usar superfícies oficiais da **CBF** conforme os respectivos adaptadores forem incorporados.

A projeção atual da agenda fica em `datasets/sports/current/`. Ela é derivada e pode ser reconstituída a partir da fonte pública; não substitui a evidência bruta da observação.

Páginas oficiais dos clubes são fontes de primeira parte complementares para agenda, elenco, comunicados e contexto. Em conflito sobre data, local, placar ou situação regulamentar de uma partida, prevalece a entidade organizadora e a divergência deve ser preservada como achado.

A integração histórica com **API-Football** continua disponível durante a migração para não quebrar detectores e consultas existentes, mas deixa de ser a autoridade editorial para agenda ou resultado pós-jogo.
