# Espacialização de CNPJs — São José dos Campos

Dá um ponto no mapa a **todo CNPJ** do município da base da Receita Federal (que só tem endereço), com o método e a confiança de cada ponto registrados. A localização vem de uma cascata de 15 passos, do mais preciso ao menos preciso, cruzando o endereço da Receita com a base de endereços da Prefeitura (SIRF + lotes) e com o CNEFE do IBGE; o resíduo passa por geocoding (OpenStreetMap / Nominatim) e, por fim, pelo centro do bairro ou do município. Usos: densidade, zoneamento e o app **Monitor de Negócios**.

Projeto no padrão de `docs/manual_padrao_projetos.md`.

## Fontes (detalhes em `docs/fontes.md`)

| Fonte | Pasta em `01_dados_brutos/` |
|---|---|
| Receita Federal: estabelecimentos, empresas, Simples/MEI e os arquivos de descrição de códigos (natureza jurídica, motivo da situação, país, CNAE) | `receita_federal/` |
| CNEFE (IBGE, Censo 2022), recorte do município | `cnefe/` |
| Tabela de CNAE 2.3 (subclasses, IBGE) | `cnae/` |
| Base de CEPs dos Correios (2018) | `correios/` |
| SIRF (cadastro imobiliário, um CSV por setor) — **dado interno** | `sirf/` |
| Lotes e limite municipal (exportados do banco pelo QGIS) — **dado interno** | `geosanja/` |
| Cadastro municipal (`cadastro_v2.xlsx`) — **dado interno** | `cadastro_municipal/` |

**Pastas de dados:** `01_dados_brutos/`, `02_dados_editados/`, `03_processamento/` e `04_entrega/` vêm no `git clone` só com um `LEIAME.md` cada; o conteúdo é ignorado pelo Git (`.gitignore`). Os dados não vêm: num computador novo, crie as subpastas listadas em `01_dados_brutos/LEIAME.md` e coloque nelas os arquivos originais (tabela acima). `03_processamento` e `04_entrega` são preenchidas pelos notebooks. O `02_dados_editados/geocoding_nominatim.jsonl` (cache do geocoding) também não está no Git: sem ele o 06 refaz as consultas ao serviço, e é lento. Guarde uma cópia fora do computador.

## Fluxo

| Nº | Notebook | Entradas | Saídas (`03_processamento/NN_<etapa>/`, salvo indicação) |
|---|---|---|---|
| 01 | `01_carregar_receita` | brutos da Receita | `df_estab`, `df_empresas`, `df_simples` |
| 02 | `02_carregar_bases_publicas` | CNEFE, CNAE, Correios | `df_cnefe`, `df_cnae`, `df_base_cep` |
| 03 | `03_carregar_bases_prefeitura` | SIRF, `lotes.gpkg`, `limite_municipal.gpkg`, cadastro; `df_estab` | `df_sirf`, `df_lotes`, `df_lotes_descartados`, `df_limite`, `df_cadastro` |
| 04 | `04_base_enderecos_prefeitura` | `df_sirf`, `df_lotes` | `ref_pref`, `sirf_vias` |
| 05 | `05_cascata_espacializacao` | `df_estab`, `df_cnefe`, `df_base_cep`, `ref_pref`, `sirf_vias` | `df_espacial` (passos 1–12), `aux_estab`, `ref_cnefe`, `base_cep`, `ceps_nao_confiaveis` |
| 06 | `06_geocoding_nominatim` | `df_espacial`, `aux_estab`, `df_lotes`; `02_dados_editados/geocoding_nominatim.jsonl` | `df_espacial` (passo 13); acrescenta respostas ao `.jsonl` (com backup) |
| 07 | `07_completar_e_ajustar_pontos` | `df_espacial`, `aux_estab`, `ref_cnefe`, `base_cep`, `ceps_nao_confiaveis`, `ref_pref`, `df_limite` | `df_espacial` final (passos 14–15, limite, CEP corrigido) |
| 08 | `08_montar_base_final` | `df_espacial`, `df_estab`, `df_empresas`, `df_simples`, `df_cnae`, `df_cadastro`; arquivos de descrição da Receita | `df_cnpj_espacial` (com descrições dos códigos e datas de abertura e encerramento) |
| 09 | `09_exportar_entregas` | `df_cnpj_espacial` | `04_entrega/`: `cnpj_espacial.gpkg`, `cnpj_espacial.xlsx`, `cnpjs_monitor.parquet`, `cnpjs_monitor_meta.json` |
| 10 | `10_exportar_aberturas_encerramentos` | `df_cnpj_espacial` | `04_entrega/aberturas_encerramentos_saldo.xlsx` (duas abas: por mês/ano e por ano) |

Fora do fluxo (`scripts/exploratorio/`): `indicadores_gerais` (ativas, abertas e extintas no ano) e `comparar_versao_antiga` (conferência da conversão).

Código comum em `scripts/src/` (ver `scripts/src/__init__.py`); `enderecos.py` e `cascata.py` são só deste projeto. Caminhos e parâmetros: `config.yaml`.

## Como rodar

```
conda env create -f environment.yml      (ou: pip install -r requirements.txt)
conda activate espacializacao_cnpjs
python executar_tudo.py                  # tudo, do 01 ao 10
python executar_tudo.py --de 05          # do 05 em diante
python executar_tudo.py --listar         # só mostra as etapas
```

## Descrições dos códigos e datas (notebook 08)

Ao lado de cada código da Receita, o 08 acrescenta uma coluna `<campo>_nome`: `situacao_nome`, `porte_nome`, `matriz_filial_nome`, `motivo_situacao_nome`, `natureza_juridica_nome`, `pais_nome`, `cnae_principal_nome`, `cnae_secundaria_nome` (lista `código – descrição` separada por ` | `), `opcao_simples_nome` e `opcao_mei_nome` (Sim, Não ou Outros). As descrições vêm dos arquivos da Receita em `01_dados_brutos/receita_federal/` (`*NATJUCSV`, `*MOTICSV`, `*PAISCSV`, `*CNAECSV`; código na 1ª coluna, descrição na 2ª, padrões e dígitos em `parametros.descricoes_receita`) e do layout da Receita (`parametros.legendas_receita`). Esses arquivos precisam estar na pasta; ao atualizar a Receita, troque-os junto com os demais. Código sem descrição aparece como `(código fora da tabela)` e é contado no log.

As datas da Receita viram **datas de verdade**. Para analisar aberturas e encerramentos há `data_abertura`, `ano_abertura` e `ano_mes_abertura` (`AAAA-MM`), e `data_encerramento`, `ano_encerramento` e `ano_mes_encerramento`, estas só para estabelecimentos **Baixados** (a data da baixa é a `data_situacao`). O 10 resume isso em `04_entrega/aberturas_encerramentos_saldo.xlsx`: aberturas, encerramentos e **saldo** (estabelecimentos abertos no fim do período; no último período, até a data da base, a última data com registro). O saldo é reconstruído da base atual da Receita, então tende a subestimar os anos antigos.

## Cache dos notebooks 01 a 03

Cada tabela lida (`df_estab`, `df_cnefe`, `df_sirf` etc.) é gravada em `03_processamento/<notebook>/` como Parquet + manifesto (`.manifesto.json`). Na rodada seguinte, o notebook só relê os brutos se o cache **não valer**. Ele vale quando os dois arquivos existem e, em relação ao momento da gravação, estes itens são iguais:

- **Arquivos de origem** (nome, tamanho e data de modificação, na pasta de `01_dados_brutos`).
- **Parâmetros** do `config.yaml` que afetam a leitura (separador, colunas, município etc.).
- **Versão da lógica** (`parametros.cache.versao_logica`; some 1 quando mudar o código da leitura).
- **Tabela da qual depende** (empresas e Simples dependem dos CNPJs do `df_estab`).

Pontos de atenção:

- **Os brutos precisam continuar na pasta.** Sem eles, a lista de origem fica vazia, o cache não vale e o notebook tenta reler arquivos que não existem. Cache não substitui o bruto.
- **Mover mantém a data; copiar pode mudar.** Se a data de modificação mudar, o notebook relê uma vez e regrava o cache.
- **Atualizou a Receita?** Basta trocar os arquivos em `01_dados_brutos/receita_federal/`: o nome, o tamanho ou a data mudam, o cache é descartado e a Receita é relida (é a etapa mais demorada). As tabelas que dependem do `df_estab` são refeitas em cadeia.
- **Qual o motivo?** O log mostra, por tabela, "Usando o cache" ou "Cache não usado (motivo)".
- **Forçar a releitura:** `parametros.cache.forcar_reprocessar` no `config.yaml` (ex.: `["df_lotes"]` ou `["todos"]`). Para limitar a idade: `parametros.cache.idade_maxima_dias` (ex.: `{df_cadastro: 30}`).
- **O cache é regenerável** (fica em `03_processamento`, fora do Git). O do geocoding é diferente: fica em `02_dados_editados/` e não deve ser apagado (ver abaixo).

## Ciclo do geocoding

O 06 faz no máximo `parametros.geocoding.max_consultas` consultas por rodada (1 por segundo). Depois de cada rodada:

```
python executar_tudo.py --ciclo          # 06, 07, 08, 09 e 10
```

As respostas ficam em `02_dados_editados/geocoding_nominatim.jsonl` (nunca são perguntadas de novo; backup datado em `_backup/` antes de cada rodada com consultas novas). Para rodar sem consultar o serviço: `parametros.geocoding.ativo: false`.

## Entrega

`04_entrega/` (fora do Git, **dados internos da Prefeitura**): GeoPackage e Excel com todos os CNPJs, o Excel de aberturas, encerramentos e saldo, e o Parquet do Monitor de Negócios (copiar `cnpjs_monitor.parquet` e `cnpjs_monitor_meta.json` para o projeto `monitor_negocios`).

**Pontos fora do limite municipal:** todo ponto fora do município vai para o ponto mais próximo dentro do limite (`ajuste_limite`); os que estavam a mais de 1.000 m (`parametros.limite.ajuste_dist_conferir_m`) ficam marcados para conferência manual, com a coordenada original em `lat_original` e `lon_original`. Eles mantêm o método e a confiança originais.
