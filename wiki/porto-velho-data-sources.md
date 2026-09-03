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
- `https://api.portovelho.ro.gov.br/docs/api#/`

A documentação oficial anuncia `https://api.portovelho.ro.gov.br/api/v1` como base de produção e Bearer Auth como mecanismo para recursos protegidos. Isso **não significa que toda rota exija token**: a exigência deve ser registrada por rota observada.

Uma rota concreta pública foi observada diretamente na própria API em respostas indexáveis no formato `/api/v1/atas/{ata_id}/requisicao/{requisicao_id}`. Esse fato demonstra que a raiz `/api/v1` serve recursos públicos reais, mas **não autoriza inferir por analogia** caminhos de contratos ou despesas. O inventário de cada rota continua exigindo documentação ou resposta observada.

## Conectores

O módulo `ovigia_dados.connectors.porto_velho` oferece:

- `PortoVelhoCkanClient`: Action API CKAN (`package_list`, `package_search`, `package_show`, `datastore_search`);
- `PortoVelhoApiClient`: cliente GET genérico para a base `/api/v1`, com Bearer opcional e sem codificar rotas ainda não observadas.

Credenciais nunca devem ser persistidas no repositório. Rotas públicas funcionam sem token quando o serviço assim permitir; token Bearer só deve ser injetado em tempo de execução quando uma operação concreta exigir.

## Uso para reconciliação financeira

Para investigar contratos e execução financeira, a sequência desejada é:

`instrumento contratual -> dataset CKAN -> PMPV API -> empenho -> liquidação -> pagamento -> superfície do Portal da Transparência`

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
