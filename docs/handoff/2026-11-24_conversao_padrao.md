# 2026-11-24 — Conversão para o padrão de projetos

## O que foi feito
- Notebook único (`espacializacao_cnpjs.ipynb`, 37 blocos) dividido em 9 notebooks:

| Notebook | Blocos antigos |
|---|---|
| 01_carregar_receita | 2, 3, 4 |
| 02_carregar_bases_publicas | 5, 9, 10 |
| 03_carregar_bases_prefeitura | 6, 7, 8, 11 |
| 04_base_enderecos_prefeitura | 13 |
| 05_cascata_espacializacao | 14 a 26 |
| 06_geocoding_nominatim | 27 |
| 07_completar_e_ajustar_pontos | 28 a 33 |
| 08_montar_base_final | 34 |
| 09_exportar_entregas | 35, 36, 37 |
| exploratorio/indicadores_gerais | bloco sem número (indicadores de 2026) |

- Bloco 1 (configuração) → `config.yaml`; funções do bloco 1 → `src/cache.py`; bloco 12 → `src/enderecos.py` (e `distancia_metros` → `src/geo.py`); funções do bloco 14 → `src/cascata.py`.
- `print` → `log.info` / `log.warning` (tela + `03_processamento/logs/`). O texto das mensagens não mudou.
- As funções da cascata que mexem no resultado passaram a receber as tabelas explicitamente: `selecionar_pendentes(df_espacial, aux_estab, ...)`, `gravar_resultado(df_espacial, ...)`, `resumo_passo(df_espacial, ...)`, `rodar_cadeia_nucleo(GRUPOS_NUCLEO, ...)`.
- Leitura do banco (lotes e limite) trocada pela leitura dos GeoPackages exportados pelo QGIS. O cálculo do ponto e as conferências não mudaram.
- Novas funções comuns: `fontes.ler_processamento` / `fontes.gravar_processamento` e `registro.formatar_tempo`.
- Histórico do Git limpo com `git filter-branch`: saídas e contadores de execução tirados de todos os notebooks, `.ipynb_checkpoints/` e `~$cnpj_espacial.xlsx` retirados.

## Para onde vão os arquivos da pasta antiga
| Pasta antiga | Pasta nova |
|---|---|
| `Documents\Receita_federal\` (ESTABELE, EMPRECSV, SIMPLES) | `01_dados_brutos/receita_federal/` |
| `Documents\IBGE\3549904_SAO_JOSE_DOS_CAMPOS.csv` | `01_dados_brutos/cnefe/` |
| `Documents\IBGE\CNAE_Subclasses_2_3_Estrutura_Detalhada.xlsx` | `01_dados_brutos/cnae/` |
| `Documents\SIRF\csv_setores_sirf\setor_*.csv` | `01_dados_brutos/sirf/` |
| `Documents\Correios\TB_CEP_BR_2018.csv` | `01_dados_brutos/correios/` |
| `Documents\PMSJC\cadastro v2.xlsx` | `01_dados_brutos/cadastro_municipal/cadastro_v2.xlsx` |
| banco: camadas de lotes e de limite municipal | `01_dados_brutos/geosanja/lotes.gpkg` / `limite_municipal.gpkg` (exportar pelo QGIS) |
| `cache/geocoding_nominatim.jsonl` | `02_dados_editados/` |
| `cache/df_estab`, `df_empresas`, `df_simples` (`.parquet` + `.manifesto.json`) | `03_processamento/01_carregar_receita/` |
| `cache/df_cnefe`, `df_cnae`, `df_base_cep` | `03_processamento/02_carregar_bases_publicas/` |
| `cache/df_sirf` | `03_processamento/03_carregar_bases_prefeitura/` |
| `cache/df_lotes*`, `df_limite`, `df_cadastro` | não precisam ir (são refeitos: os lotes e o limite vêm dos GeoPackages, e o cadastro muda de nome) |
| `dados_monitor/cnpjs_monitor.parquet` | `03_processamento/versao_antiga/` (para a comparação) |

Mover (não copiar) mantém a data de modificação, de que o cache depende.

## Validação feita
- Todo nome usado em cada notebook é definido antes (conferência estática); todos os módulos do `src` importam.
- Cascata antiga x nova (notebooks 04 a 07) em 3.000 CNPJs sintéticos, com a ida e volta pelo Parquet simulada: resultado idêntico em `ref_pref`, `ref_cnefe`, `aux_estab` e `df_espacial`. Ficaram de fora do teste o ajuste ao limite (precisa de geopandas), o 08 e o 09.
- Os parâmetros dos manifestos de cache antigos batem com os do `config.yaml` (caches reaproveitáveis).
