# Skill: fontes oficiais de futebol

## Purpose

Manter agenda e resultados pós-jogo de clubes locais a partir de fontes públicas oficiais, sem depender de live score ou API comercial.

## Procedure

1. Descubra a partida primeiro na entidade organizadora: FFER para competição estadual, CBF para competição nacional.
2. Trate a mesma identidade de partida como estado temporal: `scheduled` antes do resultado e `finished` quando a fonte oficial publicar placar final.
3. Preserve data, hora e notas exatamente como publicadas quando houver indicação como `IMT`; não fabrique horário resolvido.
4. Registre URL da fonte e URL de súmula/boletim/relatório quando a página expuser esses documentos.
5. Use página oficial do clube como fonte complementar para agenda, elenco, comunicado e contexto. Em divergência de fixture, preserve o conflito e prefira a organizadora.
6. Não faça polling de placar ao vivo. Uma revisita periódica da agenda é suficiente para detectar o encerramento.
7. Na primeira importação, não gere backlog de leads de todos os jogos antigos. Gere `official_match_finished` somente quando uma partida previamente conhecida como agendada passa a encerrada.
8. Se uma coleta retornar zero partidas reconhecidas, trate como possível quebra do parser e mantenha a projeção anterior; agenda vazia exige evidência positiva, não ausência de parsing.
9. Materialize a projeção tabular atual em formato determinístico e mantenha a evidência bruta da execução separada dela.
10. O sinal pós-jogo é uma entrada factual para a Redação, não uma decisão automática de publicar.
11. Quando a página ou documento sustentar materialmente uma publicação, use a fila Wayback já existente para preservação.

## Validation

Mantenha testes para: parsing de linha agendada; parsing de placar final; preservação de nota de horário; resolução de link de documento; ausência de backlog no bootstrap; emissão única na transição `scheduled -> finished`; idempotência para partida já encerrada; e falha segura quando nenhuma partida reconhecível for extraída.
