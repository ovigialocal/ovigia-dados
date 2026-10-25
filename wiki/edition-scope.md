---
okf_version: "0.2"
title: "Escopo de edição nos detectores"
description: "Como datasets e detectores públicos se relacionam com as edições locais de O Vigia."
---

# Escopo de edição

Uma edição é uma unidade da superfície jornalística, não uma propriedade intrínseca de um dataset. Datasets podem cobrir vários municípios, estados ou o país inteiro. Detectores locais declaram `edition_id` apenas para registrar seu consumidor editorial prioritário.

O registry canônico de `PublicEdition` e a política `PublicEditionRegistry.default_edition_id` pertencem ao repositório público do site. `ovigia-dados` consulta essa autoridade quando precisa validar um escopo, sem copiar nomes, URLs, coordenadas ou fallback para um registry paralelo.
