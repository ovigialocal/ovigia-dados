# Fontes de agenda de Porto Velho

## Objetivo

O `ovigia-dados` mantém aquisição pública e reproduzível de eventos relevantes para uma agenda da cidade. A camada de dados registra o que cada fonte publicou e como esse estado mudou; relevância editorial, pauta e linguagem de publicação continuam fora deste repositório público.

Todos os adaptadores devem normalizar para o mesmo contrato `EventObservation` e persistir pelas mesmas identidades `city-event` / observações append-only `event-observation`. O módulo `ovigia_dados.events.shared` é a superfície comum para novos coletores, mesmo enquanto parte da implementação histórica ainda reside no módulo original da Sympla.

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

## PVH Mais / Eventos

Fonte municipal:

- `https://pvhmais.portovelho.ro.gov.br/site/eventos`
- páginas individuais em `https://pvhmais.portovelho.ro.gov.br/site/eventos/<id>`.

A superfície foi observada publicamente em setembro de 2026. A listagem se apresenta como a agenda completa de eventos e atividades da cidade. Páginas individuais estáveis expõem eventos por ID numérico; por exemplo, o Fórum de Contabilidade de 2026 foi observado em `/site/eventos/16`. O identificador canônico adotado pelo dataset é `pvhmais-<id>`.

O portal é uma SPA. O HTML inicial contém um `data-parameters` público usado para iniciar a aplicação, mas a lista completa é hidratada no cliente. O coletor deliberadamente **não depende de XHR ou API interna não documentada**. Ele usa somente a listagem e as páginas públicas `/site/eventos/<id>`:

1. lê o bootstrap público e coleta IDs de objetos explicitamente marcados como `Event` quando presentes;
2. mantém uma faixa inicial conservadora de IDs e pequena janela de lookahead para descobrir páginas públicas adicionais;
3. visita apenas páginas públicas de evento e procura o objeto correspondente ao próprio ID dentro do bootstrap HTML;
4. prefere o objeto rico da página a cards/promos que apenas referenciem o mesmo ID;
5. normaliza título, datas, local, endereço, organizador e status quando publicados;
6. trata Porto Velho/RO como escopo da agenda municipal quando a página não repete município/UF no objeto;
7. persiste pelo mesmo materializador e hash usados pelas demais fontes.

A sondagem numérica é diária, limitada e concorrente em poucos workers. Ela existe para evitar dependência de uma rota interna instável; não deve virar varredura ampla ou agressiva. O teto inicial e o lookahead são parâmetros explícitos do workflow.

## Wayback/CDX como memória e backfill

O Internet Archive complementa a coleta live em duas funções:

- recuperar URLs de eventos vistas em snapshots antigos de superfícies de discovery quando o HTML arquivado contém essas URLs;
- reconstruir estados arquivados de páginas individuais quando houver URL pública conhecida.

O coletor Sympla já usa o índice CDX em `https://web.archive.org/cdx/search/cdx`, limita a respostas HTTP 200 e colapsa snapshots pelo digest. O mesmo padrão pode ser aplicado por outros adaptadores quando trouxer benefício real.

Wayback não é pré-requisito da descoberta live. Falha do CDX ou ausência de snapshot não invalida observação pública feita diretamente na fonte. Da mesma forma, a existência de um snapshot não transforma automaticamente a página em fonte material de uma matéria; preservação editorial segue o contrato próprio da fila `archive-request` quando aquela URL efetivamente sustentar publicação.

## Superfícies verificadas para expansão

Estas fontes já possuem presença pública relevante, mas ainda exigem definir o melhor mecanismo de discovery antes de ganhar um adapter automático:

### Funcultural

- `https://funcultural.portovelho.ro.gov.br/noticias`

O feed publica programação cultural municipal, inclusive atividades recorrentes e eventos com data/local. É uma forte fonte de lead e confirmação, mas notícia individual não deve ser convertida cegamente em evento sem parser que distinga anúncio, cobertura pós-evento e programação futura.

### Semtel

- `https://semtel.portovelho.ro.gov.br/`
- `https://semtel.portovelho.ro.gov.br/noticias/agenda-porto-velho-estrutura-calendario-anual-de-turismo-esporte-e-lazer`

A secretaria publicou calendário anual de turismo, esporte e lazer para 2026. Prioridade: localizar a representação pública mais estruturada desse calendário e só então automatizar extração.

### SESI / Sistema FIERO

- `https://portal.fiero.org.br/`
- notícias públicas do SESI em `https://portal.fiero.org.br/sesi/imprensa/`.

Há eventos de Porto Velho com data, local e programação publicados em páginas institucionais. O adapter deve filtrar município e separar anúncio pré-evento de cobertura posterior.

### IFRO

- `https://portal.ifro.edu.br/`

O portal publica eventos realizados em Porto Velho, inclusive competições e encontros com datas verificáveis. Como a superfície é estadual/institucional, o filtro geográfico precisa ser explícito.

### UNIR e Sesc Rondônia

Permanecem como candidatos prioritários. Antes de automatizar, localizar uma listagem/feed institucional estável e documentar sua semântica. Não inferir endpoint ou catálogo por analogia.

## Limites deliberados

- Adaptadores não devem depender de endpoint interno não documentado quando uma superfície pública estável atende à aquisição.
- Evento sem localização verificável em fonte de escopo amplo não entra automaticamente na agenda local.
- Identidade entre plataformas diferentes não é inferida apenas por semelhança de título.
- Reconciliação futura deve usar data, local, organizador e outras evidências.
- O estado `unknown` é preferível a inventar status quando a fonte não o publica de forma confiável.
- Fonte de notícias exige distinguir anúncio futuro, mudança/cancelamento e cobertura pós-evento antes de materializar eventos.

## Reconciliação futura

A próxima camada deve comparar identidades source-specific (`sympla-*`, `pvhmais-*` etc.) e produzir evidência de equivalência sem apagar nenhuma origem. Bons sinais incluem:

- título normalizado semelhante;
- data/hora compatível;
- mesmo local/endereço;
- mesmo organizador/produtor;
- links cruzados entre as fontes.

Matching por título sozinho nunca é suficiente. Divergência entre fontes deve permanecer visível como dado investigável, não ser resolvida silenciosamente por overwrite.
