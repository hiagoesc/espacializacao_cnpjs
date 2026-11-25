# Decisões de método

Decisões com data e motivo. As anteriores à conversão foram tomadas durante a construção do notebook único (outubro/2026); o dia exato não foi registrado.

## Antes da conversão (out/2026)

- **Bases de referência:** a base da Prefeitura (SIRF + lotes) é a mais confiável e é tentada antes do CNEFE, que também é oficial e preciso. A Receita é a base tratada: CEP, nome da via e digitação podem estar errados, então uma divergência de CEP ou de nome de via é considerada erro da Receita.
- **Método e confiança:** cada método tem uma única confiança e um nome claro (nenhum método com vários níveis de confiança).
- **Todo CNPJ tem ponto** (exigência do projeto e da chefia), mesmo com precisão baixa, registrada em método e confiança. O resíduo passa por geocoding (Nominatim, em Python no próprio fluxo) e, por último, pelo centro do bairro e pelo centro do município.
- **Ponto do lote:** ponto garantido dentro do polígono (`representative_point`); se a mesma inscrição tem mais de um desenho válido, fica o de maior área. Regra da "área maior": o último bloco da inscrição vira `0000`.
- **CEP não confiável** (CEP "genérico", como o 12227788): regra reutilizável, não lista fixa. É não confiável o CEP com pelo menos 20 CNPJs, concordância entre CEP e via declarada abaixo de 40% e pelo menos 15 nomes de via diferentes declarados. Esses CEPs nunca são usados sozinhos para localizar.
- **CEP corrigido:** para os CNPJs com CEP da Receita não confiável, é guardado o CEP certo achado pelo nome da via.
- **CNAE:** só o principal; o código `8888888` (sem atividade informada) vira "Não informado".
- **Pontos fora do limite municipal:** vão para o ponto mais próximo dentro do limite (1 m para dentro). (Alterado em 25/11/2026: antes, os que estavam a mais de 1.000 m iam para o centro do município.)
- **Cadastro municipal:** traz `Estabelecido`, `Tipo` e `Reg. Tributário`; os dois CNAEs (o do cadastro e o da Receita) são mantidos, sem sobrescrever. Até 24/11/2026 só o código do motivo da situação era guardado (faltava o arquivo de motivos da Receita; ver a decisão de 25/11/2026).
- **Limiares da cascata** (`parametros.cascata` do `config.yaml`): escolhidos na construção e **ainda não validados**.

## 24/11/2026 — Conversão para o padrão de projetos

- **Fluxo em 9 notebooks** (01 a 09), no lugar do notebook único de 37 blocos. A lógica de cada bloco não mudou.
- **Lotes e limite municipal** passam a vir de GeoPackages exportados do banco pelo QGIS (`01_dados_brutos/geosanja/`), e não mais da conexão ao banco dentro do notebook. Motivo: fluxo reprodutível, roda fora da rede da Prefeitura e sem digitar credenciais. A versão da lógica dessas tabelas no cache passou para 2.
- **Cache de leitura** (Parquet + manifesto) mantido, agora em `src/cache.py` e gravando em `03_processamento`. Motivo: evita reler os ~20 GB da Receita a cada rodada.
- **Cache do geocoding** em `02_dados_editados/` (não é regenerável sem refazer milhares de consultas), com backup datado antes de cada rodada com consultas novas.
- **Normalização de endereços** da cascata em `src/enderecos.py` (só deste projeto), e não no `texto.py` comum, que tem outra regra (a da RAIS) e mudaria os resultados.
- **Conferência no 08:** antes de juntar `df_espacial` e `df_estab` pela numeração das linhas, confere se o CNPJ é igual linha a linha.

## 25/11/2026 — Descrições dos códigos, datas, saldo e ajuste ao limite

- **Descrições ao lado dos códigos (notebook 08):** colunas `<campo>_nome` para situação, porte, matriz/filial, motivo da situação, natureza jurídica, país, CNAE principal e secundária, Simples e MEI. Os nomes de situação, porte e matriz/filial usam a escrita que o Monitor já tinha (Ativa, Baixada, Microempresa...); os dicionários passaram do 09 para o `config.yaml` (`parametros.legendas_receita`). Motivo: um só lugar para os textos, usados por todas as entregas.
- **CNAE da Receita para os nomes:** `cnae_principal_nome` e `cnae_secundaria_nome` vêm do arquivo `*CNAECSV` da Receita, por ser mais preciso que o do IBGE. A tabela do IBGE continua só para a seção e a divisão (`cnae_secao`, `cnae_divisao`).
- **CNAE secundária:** texto `código – descrição` separado por ` | `; só nas entregas completas (GeoPackage e Excel), não no Monitor.
- **Simples e MEI:** S = Sim, N = Não, registro com o campo em branco = Outros; CNPJ sem registro no arquivo do Simples fica vazio.
- **Código sem descrição:** recebe `(código fora da tabela)` (ou `(código fora do layout)`, nos nomes do layout) e é contado no log; código vazio fica sem nome.
- **Datas de verdade no 08:** as datas da Receita (`AAAAMMDD`) são convertidas no 08, e não mais só no 09; `00000000` vira vazio. Novas colunas: `data_abertura`, `ano_abertura`, `ano_mes_abertura` e, só para Baixados (situação 8), `data_encerramento`, `ano_encerramento` e `ano_mes_encerramento` (a data da baixa é a `data_situacao`).
- **Arquivo de saldo (notebook 10):** Excel com aberturas, encerramentos e saldo, por mês/ano e por ano. **Saldo** = estabelecimentos abertos no fim do período (abertos até a data, em qualquer ano, menos baixados até a data); suspensos, inaptos e nulos contam como abertos. O último período vai até a data da base (a maior data dos registros). Conta todos os estabelecimentos (matriz e filial). Encerramento anterior à abertura (data com erro) vale como a data da abertura no saldo; estabelecimento sem data de abertura fica fora. Limite: o saldo é reconstruído da base atual e subestima os anos antigos (quem saiu do município ou deixou de constar não aparece).
- **Ajuste ao limite municipal:** sempre o ponto mais próximo dentro do limite; os que estavam a mais de `parametros.limite.ajuste_dist_conferir_m` (1.000 m) ficam marcados em `ajuste_limite` ("conferir manualmente"). Método, passo e confiança originais são mantidos (a coluna `ajuste_limite_m` e as colunas `*_original` permitem filtrar esses casos).
- **Monitor:** recebe as descrições e as colunas de abertura e encerramento, menos `cnae_secundaria_nome` e `pais_nome` (como os códigos correspondentes, que já ficavam de fora). O rótulo da base passou para "Receita Federal – 2026-11".
- **Diagnósticos no log:** o 02 separa as repetições de `COD_UNICO_ENDERECO` do CNEFE em mesma coordenada (inofensivas) e coordenadas diferentes; o 03 lista a inscrição e a coordenada dos lotes descartados e dos pontos fora do próprio lote (só aparece quando os lotes são relidos: `forcar_reprocessar: ["df_lotes", "df_lotes_descartados"]`); o 07 mostra, por CEP não confiável, quantos CNPJs tiveram o CEP corrigido.

- **Conferência da rodada real (25/11/2026):** os 3 CNPJs a mais de 1.000 m do limite (mesmo endereço) ficam como estão: ponto mais próximo dentro do limite, com a marca de conferência. O motivo de situação 32, ausente do arquivo da Receita, fica como "(código fora da tabela)".
- **Documentação (25/11/2026):** o manual passou para a v1.3, com os avisos do cache (seção 4.1) e das pastas de dados fora do Git; o README ganhou o aviso das pastas de dados e do cache do geocoding.

- **Rodada 2 (endereço do cadastro municipal) fora do fluxo (25/11/2026):** não será implementada. Diagnóstico (`scripts/exploratorio/diagnostico_rodada2_cadastro.ipynb`): dos 29.275 CNPJs de confiança baixa ou muito baixa, 4.327 têm cadastro (14,8%; entre os 15.748 baixados só 30), 1.497 têm endereço diferente do da Receita e 1.129 têm endereço diferente e utilizável (3,9% do grupo, 0,35% da base). Esse é o teto: o cadastro abrevia o tipo da rua em ~4,6% das linhas (`AV`, `AVN`, `R`), o que infla a contagem, e o ganho real de confiança seria menor. Motivo: ganho pequeno para o custo de implementar e validar. A seção 3 do notebook 07 continua só avisando que não foi implementada.
- **Repositório público, recriado (25/11/2026):** o repositório foi apagado e recriado com o mesmo nome, público e com um commit único, para não carregar o histórico antigo (saídas de notebook, checkpoint e a versão com a leitura do banco no notebook). Mantidos de propósito: o e-mail de contato no `user_agent` do Nominatim, o nome de usuário do Windows no manual e a menção de que existem bases internas da Prefeitura. Retirados os nomes das tabelas do banco da Prefeitura (as camadas vêm dos GeoPackages).
- **Pastas de dados no Git:** cada pasta (`01` a `04`) tem um `LEIAME.md`, e o `.gitignore` ignora o conteúdo mas mantém o LEIAME (padrão do `espacializacao-rais`). Manual v1.4.
