# Fontes oficiais de futebol e agenda pós-jogo

## Regra de autoridade

Para agenda, local, resultado e documentos de uma partida, a fonte preferencial é a **entidade organizadora da competição**. Em Rondônia, isso significa FFER para competições estaduais e CBF para competições nacionais. Páginas próprias dos clubes são fontes de primeira parte complementares: são valiosas para agenda, elenco, comunicados e contexto, mas não substituem a tabela/regulamento da organizadora quando houver divergência.

O pipeline não precisa de placar ao vivo. A rotina desejada é:

`agenda oficial -> partida conhecida -> revisita pós-jogo -> resultado/documentos oficiais -> sinal factual -> redação`

Uma partida que aparece pela primeira vez já encerrada durante bootstrap não gera backlog editorial automaticamente. O sinal `official_match_finished` nasce quando uma partida previamente conhecida como agendada passa a encerrada na fonte oficial.

## FFER

Fonte de agenda/resultados do Campeonato Rondoniense 2026:

- `https://ffer.com.br/Publicacao.aspx?id=640220`

A página reúne classificação e tabelas por rodada com número do jogo, data, hora, mandante, placar, visitante, estádio e acesso a SÚM/BOR/REL. A mesma linha serve antes do jogo como agenda e depois do jogo como registro de resultado. Isso permite coleta determinística sem API comercial.

Catálogo oficial de clubes profissionais:

- `https://ffer.com.br/Publicacao.aspx?id=393357`

A FFER identifica como páginas oficiais, entre outras:

- Vilhenense EC — `https://www.facebook.com/Vilhenense`
- Sport Club Genus — `https://www.facebook.com/sportclubgenus`
- União Cacoalense — `https://www.facebook.com/s.e.uniaocacoalenseoficial`
- Gazin Porto Velho EC — `https://www.facebook.com/portovelhoec`
- Barcelona FC — `https://www.facebook.com/BarcelonaFutebolClube2016`
- Guaporé FC — `http://guaporefc.com.br/`
- Pimentense — `https://www.facebook.com/CAPPIMENTENSE`
- Real Ariquemes — `http://realariquemes.com.br/`
- Ji-Paraná FC — `http://www.jipafc.com.br/`
- Rondoniense SC — `https://www.rondoniensesc.com.br/`

## Porto Velho EC

Além da página indicada pela FFER, o clube mantém site próprio atual:

- site: `https://ecportovelho.com/`
- agenda: `https://ecportovelho.com/agenda/`

A agenda do clube informa próximos jogos e resultados anteriores. Ela é boa fonte de confirmação e de contexto de primeira parte. Quando houver diferença com FFER/CBF sobre partida organizada por essas entidades, registrar a divergência e usar a organizadora como autoridade do fixture.

## Ji-Paraná e Guaporé

Os domínios indicados pela própria FFER continuam sendo superfícies próprias úteis:

- Ji-Paraná FC — `http://www.jipafc.com.br/`
- Guaporé FC — `http://guaporefc.com.br/`

Não inferir que toda página social encontrada em buscadores é oficial. Prefira URL publicada pelo próprio clube, pela FFER ou por outra fonte institucional verificável.

## CBF

Para Série D, Copa Verde, Copa do Brasil e competições nacionais de base/feminino, usar páginas oficiais da CBF. As páginas individuais de jogo expõem placar e superfícies de escalação, arbitragem e documentos; quando disponíveis, súmula, boletim financeiro e relatório de jogo são evidência pós-jogo de alta qualidade.

O adaptador FFER é o primeiro coletor oficial implementado porque a tabela estadual concentra toda a agenda em uma página estável. O contrato do pipeline é deliberadamente source-neutral para que um adaptador CBF produza os mesmos estados (`scheduled`/`finished`) sem reintroduzir IDs proprietários de API comercial como identidade canônica.

## OpenFootball / football.db

OpenFootball é uma fonte aberta complementar especialmente atraente porque os dados e o schema são publicados em CC0/domínio público e podem ser incorporados, transformados e redistribuídos sem chave de API.

A qualidade precisa ser separada em duas perguntas:

1. **qualidade onde existe cobertura** — alta para o objetivo de fixtures/resultados simples;
2. **cobertura de Rondônia** — atualmente insuficiente.

Na auditoria de 5 de setembro de 2026, o repositório `openfootball/south-america` tinha `brazil/2026_br1.txt` com agenda/resultados da Série A 2026 acompanhando a temporada corrente, inclusive fixtures de 5 e 6 de setembro. Isso demonstra boa atualidade para a competição coberta.

Por outro lado, para 2026 não havia arquivos equivalentes de Série B, Série C, Série D ou Copa do Brasil no diretório brasileiro. O catálogo `openfootball/clubs` também não continha nenhum dos sete clubes atualmente monitorados no registry do O Vigia: Genus, Guajará, Ji-Paraná, Porto Velho, Real Desportivo Ariquemes, União Cacoalense e Vilhena. Como consequência, a cobertura corrente medida para Rondônia é `0/7` clubes no catálogo e `0/7` em partidas brasileiras 2026.

Isso torna OpenFootball excelente como **open data complementar e histórico**, mas inadequado hoje como fonte operacional principal para futebol rondoniense. O pipeline registra a fonte como `open_data_complementary` e roda auditoria semanal. Se Série D ou clubes de Rondônia surgirem no dataset, a mudança aparecerá automaticamente em `datasets/sports/quality/openfootball-rondonia*.csv` e poderá justificar promoção de uso.

## API-Football e migração

API-Football permanece temporariamente como compatibilidade para detectores e consultas legadas, mas não é mais a fonte de autoridade para agenda/resultados.

## Observações operacionais

- Não fazer polling de live score.
- Revisitar periodicamente a agenda oficial é suficiente; a coleta atual roda em cadência baixa e detecta transição para encerrado.
- Preservar a URL exata da fonte e, quando material para publicação, enfileirar a página/documento no fluxo Wayback existente.
- Não transformar automaticamente todo resultado em notícia: o `signal` é lead factual. A Redação decide relevância e reapura contexto.
- Se a estrutura HTML mudar e zero partidas forem reconhecidas, falhar sem sobrescrever a projeção anterior. Zero partidas extraídas não equivale a agenda vazia.
- Tratar qualidade de open data como propriedade observável: licença, recência, competições presentes e cobertura dos clubes locais devem ser medidas, não presumidas.
