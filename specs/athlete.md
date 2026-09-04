---
okf_version: "0.2"
title: "Especificação de Atleta"
description: "Define um atleta acompanhado longitudinalmente pelo O Vigia e o vínculo verificável que o inclui no cadastro esportivo de Rondônia."
type: "specification"
target_type: "athlete"
fields:
  athlete_id:
    type: string
    description: "Identificador canônico estável do atleta, usado por matérias e outros concepts para referenciá-lo."
  name:
    type: string
    description: "Nome público pelo qual o atleta é identificado."
  sport:
    type: string
    description: "Modalidade esportiva principal acompanhada."
  rondonia_link:
    type: string
    description: "Descrição factual do vínculo com Rondônia, sustentada pelas fontes do concept."
  current_team:
    type: string
    description: "Equipe, clube ou entidade esportiva atual, quando aplicável e verificado."
  sources:
    type: array
    description: "Fontes públicas que sustentam a identidade, o vínculo com Rondônia e os dados atuais do perfil."
---

# Especificação: Atleta

Cada atleta acompanhado pelo O Vigia é um concept Markdown próprio do tipo `athlete`.

O arquivo do atleta é a identidade canônica e estável do perfil. Matérias, observações, eventos de carreira e sinais esportivos devem referenciar `athlete_id` em vez de duplicar a ficha da pessoa ou inferir identidade por nome.

Mudanças de carreira devem ser registradas preservando histórico; o perfil não deve apagar fatos anteriores apenas para refletir o estado corrente.
