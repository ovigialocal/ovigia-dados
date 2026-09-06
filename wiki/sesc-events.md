# Sesc Rondônia como fonte de eventos

## Superfícies públicas

O Sesc Rondônia mantém páginas públicas de evento em `https://sescro.com.br/etn/<slug>/` e arquivos públicos que permitem discovery sem credenciais. O coletor começa por:

- `https://sescro.com.br/etn_category/cultura/`;
- `https://sescro.com.br/etn_category/assistencia/`;
- `https://sescro.com.br/etn-tags/lazer/`.

As unidades confirmadas publicamente em Porto Velho incluem Sesc Esplanada, Sesc Centro e Sesc Campestre. O filtro geográfico também aceita referências explícitas a Porto Velho e alguns locais inequívocos da capital que aparecem na programação, como Teatro Guaporé, Porto Velho Shopping e Complexo Madeira-Mamoré.

O endereço da sede exibido no rodapé do site **não é evidência do local do evento**. Uma página de Ji-Paraná, Nova Mamoré ou outro município recebe o mesmo rodapé e não pode ser classificada como Porto Velho por isso.

## Problema observado no metadata do plugin

Em setembro de 2026, páginas públicas `/etn/` apresentavam inconsistência entre o texto editorial do evento e a data renderizada pelo componente de calendário. Exemplos observados publicamente incluíram:

- `Festival de Natação`: bloco editorial `Data: 26/04/2025`, enquanto o componente também apresentava uma sequência concatenada com `15 de agosto de 2026`;
- `Sesc Apresenta`: bloco editorial `14 e 15 de maio de 2025`, com outra data de 2026 aparecendo no componente;
- páginas históricas de 2023 e 2024 exibindo de modo semelhante uma segunda data de 2026.

Por isso o adapter não usa o metadata automático do plugin como verdade de agenda. Ele exige o bloco editorial explícito:

```text
Evento: ...
Data: ...
Local: ...
```

Somente a `Data:` desse bloco é normalizada. Datas posteriores renderizadas pelo widget `Adicionar ao calendário` são ignoradas.

## Datas sem horário

Muitos registros editoriais do Sesc publicam a data mas não um horário confiável. Esses casos usam `starts_on` / `ends_on` no `EventObservation`. O coletor não converte dia civil em `00:00` nem tenta aproveitar um horário do widget quando o próprio metadata temporal já demonstrou inconsistência.

Intervalos simples são preservados como datas civis, por exemplo:

- `26/04/2025` → `starts_on: 2025-04-26`;
- `14 e 15 de maio de 2025` → `starts_on: 2025-05-14`, `ends_on: 2025-05-15`;
- `25, 26 e 27 de setembro de 2025` → intervalo de 25 a 27 de setembro.

Expressões sem ano, como `01/12`, não são materializadas automaticamente porque inferir o ano a partir da data de crawl ou do plugin pode produzir agenda falsa.

## Programação 2026 fora do tipo `/etn/`

O site também publicou páginas de blog com programação agregada, entre elas o calendário cultural do primeiro semestre de 2026 e o calendário de Turismo Social de 2026. Essas páginas são fontes valiosas de lead e confirmação, mas exigem um parser de programação composto: uma mesma página pode conter muitas atividades, datas recorrentes e locais diferentes.

Esta primeira integração do Sesc mantém esse conteúdo registrado como superfície de expansão e automatiza somente o formato `/etn/` que pode ser normalizado de modo conservador. Um adapter posterior pode decompor calendários agregados em múltiplos `city-event` sem reutilizar a data defeituosa do plugin.

## Operação

`collect_sesc.py` descobre URLs nos arquivos públicos, hidrata as páginas individuais e só materializa um evento quando:

1. existe o trio editorial `Evento/Data/Local`;
2. a data contém ano e pode ser normalizada sem inventar horário;
3. o local confirma Porto Velho pela própria informação editorial;
4. o URL é um `/etn/<slug>/` público e canônico do Sesc Rondônia.

O workflow roda duas vezes ao dia com uma página por arquivo por padrão. Profundidade maior é manual e serve para backfill. Após a coleta, o workflow geral de reconciliação pode ligar `sescro-*` a identidades da Sympla, PVH Mais e futuras fontes usando a mesma evidência temporal/geográfica.
