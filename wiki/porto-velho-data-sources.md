# Fontes de dados oficiais de Porto Velho

## Escopo

O `ovigia-dados` trata duas superfícies municipais como fontes institucionais complementares:

1. Portal de Dados Abertos — `https://dados.portovelho.ro.gov.br/`, desenvolvido sobre CKAN;
2. PMPV API — documentação em `https://api.portovelho.ro.gov.br/docs/api#/` e base de produção observada `https://api.portovelho.ro.gov.br/api/v1`.

O Portal de Dados Abertos é apropriado para descoberta de datasets, metadados e recursos estáveis. A PMPV API expõe rotas de integração próprias da Prefeitura e pode descrever a mesma entidade administrativa por outra superfície. Uma divergência entre essas fontes é sinal para investigação, não conclusão automática de erro ou irregularidade.

## Inventário observado em 2026-09-03

A superfície CKAN anunciava **28 conjuntos de dados**, **7 organizações** e **7 grupos temáticos**. O grupo `Contabilidade` reunia **21 conjuntos**. Entre os datasets observados como alimentados pela API municipal estavam:

- Contratos;
- Empenhos;
- Liquidações;
- Pagamentos;
- Despesas com Obras;
- Despesas com Diárias;
- Despesas com Passagens;
- Receitas e Receitas Previstas;
- Dívidas Ativas;
- Fornecedores;
- Unidades Gestoras;
- Programas, Projetos e Ações;
- emendas parlamentares municipais/estaduais/federais quando catalogadas na superfície correspondente.

Os metadados do CKAN descrevem `Contratos` como categoria `Contratos` e `Empenhos`, `Liquidações` e `Pagamentos` como categoria `Despesas`. Eles também publicam os parâmetros de consulta em metadados do catálogo. Isso torna o CKAN útil não apenas como lista de links, mas como **mapa verificável da superfície da PMPV API**.

Fontes observadas:

- `https://dados.portovelho.ro.gov.br/`
- `https://dados.portovelho.ro.gov.br/en/dataset/?_tags_limit=0&groups=contabilidade&res_format=JSON&tags=api&tags=dados-abertos&tags=json`
- `https://dados.portovelho.ro.gov.br/dataset/api-contratos`
- `https://dados.portovelho.ro.gov.br/en/dataset/api-licitacoes`
- `https://api.portovelho.ro.gov.br/docs/api#/`
- `https://api.portovelho.ro.gov.br/api/v1/contratos`
- `https://api.portovelho.ro.gov.br/api/v1/licitacoes`

A documentação oficial anuncia `https://api.portovelho.ro.gov.br/api/v1` como base de produção e Bearer Auth como mecanismo para recursos protegidos. Isso **não significa que toda rota exija token**: a exigência deve ser registrada por rota observada.

Três famílias de rota pública já foram observadas diretamente:

- `GET /api/v1/atas/{ata_id}/requisicao/{requisicao_id}`;
- `GET /api/v1/contratos`;
- `GET /api/v1/licitacoes`.

O dataset CKAN `Contratos` documenta formalmente `endpoint_path: /contratos`, método `GET`, resposta paginada de `ContratoResource` e os parâmetros `ano`, `secretaria`, `modelo`, `vigencia`, `classificacao`, `por-pagina`, `contratante`, `situacao` e `categoria`. A resposta viva observada em 3 de setembro de 2026 confirmou acesso público sem Bearer nessa consulta e expôs, entre outros campos, `valor`, `valor_executado`, `numero_processo`, `contratante`, `fornecedor`, `licitacao`, `arquivos`, `empenhos`, `itens` e timestamps.

O dataset CKAN `Licitações` documenta `endpoint_path: /licitacoes`, método `GET`, resposta paginada de `LicitacaoResource`, ordenação por `id`, `data_publicacao`, `data_validade` ou `created_at` e filtros nomeados para título, objeto, processo, edital, datas, ano, tipo, modalidade, classificação e situação. A rota pública foi igualmente observada respondendo sem Bearer.

Essas observações confirmam rotas concretas; não autorizam inferir por analogia outros paths de contratos ou despesas. Cada nova rota continua exigindo documentação ou resposta observada.

## Conectores

O módulo `ovigia_dados.connectors.porto_velho` oferece:

- `PortoVelhoCkanClient`: Action API CKAN (`package_list`, `package_search`, `package_show`, `datastore_search`);
- `PortoVelhoApiClient`: cliente GET para a base `/api/v1`, com Bearer opcional;
- `PortoVelhoApiClient.list_contracts(...)`: conexão tipada apenas para os filtros documentados de `GET /contratos`;
- `PortoVelhoApiClient.list_licitations(...)`: conexão tipada para `GET /licitacoes`, rejeitando filtros não documentados.

Credenciais nunca devem ser persistidas no repositório. Rotas públicas funcionam sem token quando o serviço assim permitir; token Bearer só deve ser injetado em tempo de execução quando uma operação concreta exigir.

## Uso para reconciliação financeira

Para investigar contratos e execução financeira, a sequência desejada é:

`instrumento contratual -> dataset CKAN -> PMPV API -> licitação -> empenho -> liquidação -> pagamento -> superfície do Portal da Transparência`

Cada camada deve preservar os identificadores necessários para demonstrar que os registros se referem ao mesmo objeto. Não inferir identidade apenas por semelhança textual.

No caso de divergência de valor:

- se contrato, empenho e dados de origem concordam e apenas uma página agregada diverge, localizar a anomalia na camada derivada sem afirmar qual componente de software a introduziu;
- se a divergência já aparece no dataset/API de origem, investigar a semântica do campo e o sistema produtor antes de atribuir erro ao Portal;
- testar recorrência em múltiplos registros antes de descrever padrão sistêmico.

### Caso de teste prioritário: Contrato 027/PGM/2026

O caso deve permanecer como teste de integração porque já oferece identificadores independentes para reconciliação:

- contrato: `027/PGM/2026`;
- processo: `019.000710/2026-88`;
- PNCP: `05903125000145-2-000076/2026`;
- empenho: `0001504/2026`.

A superfície pública do Portal mostra R$ 1.368.000.000,00 como valor global do contrato, enquanto o instrumento assinado registra R$ 1.368.000,00 e o empenho registra R$ 1.040.000,00. O objetivo do cruzamento CKAN/API é localizar em qual camada aparecem os três zeros adicionais; esses fatos, isoladamente, **não demonstram que o sistema contábil de origem aceitou um empenho bilionário**.

### Novo sinal de recorrência na API

Na resposta pública de `GET /contratos` observada em 3 de setembro de 2026, o `ContratoResource` de id `4285`, referente à aquisição de uma ambulância pela SEMUSA, apresentou:

- `valor.value`: `341869` (R$ 341.869,00);
- arquivo do contrato com `valor.value`: `341869`;
- licitação associada com `valor_estimado.value`: `385780`;
- a mesma licitação com `valor_contratado.value`: `341869000` (R$ 341.869.000,00).

O fator é novamente exatamente **1.000** entre o valor do contrato e o `valor_contratado` aninhado da licitação. Isso é evidência de um segundo caso de divergência numérica em uma superfície oficial, suficiente para abrir investigação de recorrência, mas ainda insuficiente para atribuir uma causa técnica única, afirmar que o sistema contábil registra esse valor ou qualificar o problema como fraude/irregularidade.

A próxima falsificação deve consultar `GET /licitacoes` pelo processo `005.002970/2026-47`, comparar o registro individual da licitação com o instrumento assinado e eventual empenho e procurar outras ocorrências do mesmo fator. O filtro de processo está documentado pelo CKAN; portanto esse cruzamento não depende de rota inventada.

## Inventário de endpoints

O inventário específico da PMPV API deve ser gerado apenas a partir da documentação oficial, especificação OpenAPI/Swagger quando disponível ou respostas observadas. Registrar para cada rota:

- método e path;
- parâmetros;
- formato de retorno;
- necessidade ou não de Bearer;
- entidade administrativa representada;
- chave de ligação com datasets CKAN, quando demonstrada;
- data da observação.

Não inventar endpoints por analogia de nomes. A base `/api/v1` é estável como raiz observada, mas cada path concreto precisa de evidência própria.

## Evidência e WikiSkill

Execuções reais que produzam informação material devem preservar evidência imutável em `raw/`; aprendizados estáveis sobre schema, paginação, campos, limites e falhas devem ser consolidados nesta wiki ou em página especializada. Se um padrão virar procedimento repetível, promovê-lo a skill com teste correspondente.

## Limites editoriais

Esses conectores produzem evidência técnica e dados reproduzíveis. Eles não transformam divergência em acusação. Qualificações como fraude, superfaturamento ou falha sistêmica exigem evidência adicional e permanecem sob autoridade editorial da Redação.
