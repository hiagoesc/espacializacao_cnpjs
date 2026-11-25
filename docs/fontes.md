# Fontes

Uma seção por dado bruto (`01_dados_brutos/<fonte>/`). As datas de modificação vêm dos manifestos de cache do notebook original.

## receita_federal/
- **Origem:** Receita Federal (base de CNPJ). URL: https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9.
- **Arquivos:** 10 `K3241.K03200Y*.D61114.ESTABELE`, 10 `K3241.K03200Y*.D61114.EMPRECSV`, `F.K03200$W.SIMPLES.CSV.D61114` e os 4 arquivos de descrição de códigos (abaixo).
- **Base:** novembro de 2026 (sufixo `D61114`; última data com registro: 15/11/2026). Rótulo usado no Monitor: "Receita Federal – 2026-11".
- **Arquivos de descrição** (`F.K03200$Z.D61114.*`; sem linha de títulos, código na 1ª coluna e descrição na 2ª, separados por `;` e com aspas; lidos em UTF-8, com latin-1 como alternativa): `NATJUCSV` (natureza jurídica, 92 códigos), `MOTICSV` (motivo da situação cadastral, 63), `PAISCSV` (país, 255) e `CNAECSV` (CNAE, 1.359; inclui o código `8888888`, atividade não informada). Usados no notebook 08; os padrões de nome ficam em `parametros.descricoes_receita` do `config.yaml`.
- **Formato:** texto separado por `;`, sem linha de títulos, codificação latin-1. Layout das colunas em `parametros.receita` do `config.yaml`.
- **Recorte:** estabelecimentos com `cod_municipio_rf = 7099`; empresas e Simples filtrados pelos CNPJs básicos desses estabelecimentos.
- **Colunas usadas:** todas as do layout; o Monitor não leva CNAE secundário, contatos, país e situação especial.
- **Legendas do layout** (situação cadastral, porte, matriz/filial, opção pelo Simples e pelo MEI): `parametros.legendas_receita` do `config.yaml`.

## cnefe/
- **Origem:** IBGE, Cadastro Nacional de Endereços para Fins Estatísticos (Censo 2022), recorte do município. URL e caminho: https://www.ibge.gov.br/estatisticas/downloads-estatisticas.html > Cadastro_Nacional_de_enderecos_para_Fins_Estatisticos > Censo_Demografico_2022 > Arquivos_CNEFE > CSV > Municipio > 35_SP > 3549904_SAO_JOSE_DOS_CAMPOS.zip.
- **Arquivo:** `3549904_SAO_JOSE_DOS_CAMPOS.csv` (modificado em 17/05/2024).
- **Formato:** CSV separado por `;`, UTF-8. Coordenadas em `LATITUDE`/`LONGITUDE`, tratadas como SIRGAS 2000 (EPSG:4674) — **a conferir**.
- **Colunas usadas:** `CEP`, `NOM_TIPO_SEGLOGR`, `NOM_TITULO_SEGLOGR`, `NOM_SEGLOGR`, `NUM_ENDERECO`, `LATITUDE`, `LONGITUDE`.

## cnae/
- **Origem:** IBGE / Concla, CNAE 2.3 — estrutura detalhada das subclasses. URL: https://cnae.ibge.gov.br/classificacoes/download-concla/8265-download.
- **Arquivo:** `CNAE_Subclasses_2_3_Estrutura_Detalhada.xlsx` (modificado em 15/10/2026), aba `Estrutura Det. CNAE Subclass2.3`.
- **Colunas usadas:** subclasse (7 dígitos), denominação, seção e divisão.

## correios/
- **Origem:** base de CEPs do Brasil, versão 2018. URL: https://data.mendeley.com/datasets/g97jb8fp57/1.
- **Arquivo:** `TB_CEP_BR_2018.csv` (modificado em 14/10/2026). CSV separado por `;`, UTF-8 com BOM.
- **Recorte:** UF `SP`, cidade `São José dos Campos`.
- **Colunas usadas:** `CEP`, `LOGRADOURO`, `BAIRRO`.

## sirf/ (dado interno da Prefeitura)
- **Origem:** SIRF (cadastro imobiliário), exportado em CSV, um arquivo por setor.
- **Arquivos:** 70 `setor_NN.csv` (exportados em 15/10/2026). CSV separado por `;`, codificação cp1252.
- **Colunas descartadas na leitura (dados pessoais):** `Código Pessoa`, `Nome`, `CPF`, `CNPJ`.
- **Colunas usadas:** `Inscrição` (formato `00.0000.0000.0000` = setor.quadra.lote.unidade), `Logradouro` (tipo abreviado no início: R, AV, PCA...), `Número Imóvel`, `CEP`.

## geosanja/ (dado interno da Prefeitura)
- **Origem:** banco geográfico da Prefeitura (PostGIS), exportado pelo QGIS em GeoPackage (todas as feições, CRS original).
- **`lotes.gpkg`** (camada `lotes`): exportada do banco da Prefeitura. Coluna usada: `rotulo` (inscrição imobiliária) + desenho. Data da exportação: **a preencher**. CRS de origem (em metros): **a preencher**.
- **`limite_municipal.gpkg`** (camada `limite_municipal`): exportada do banco da Prefeitura. Só o desenho. Data da exportação: **a preencher**.

## cadastro_municipal/ (dado interno da Prefeitura)
- **Origem:** exportação do cadastro municipal (sem edição). Nome original: `cadastro v2.xlsx` (modificado em 19/10/2026), renomeado para `cadastro_v2.xlsx`.
- **Colunas usadas:** `Insc. Mun.`, `CNPJ/CPF`, `Endereço`, `Rua`, `Bairro`, `CEP`, `Cidade`, `CNAE principal`, `Descrição CNAE principal`, `Estabelecido`, `Tipo`, `Reg. Tributário`. `Contribuinte` é descartado na leitura (dado pessoal).

## Dado editado: 02_dados_editados/geocoding_nominatim.jsonl
- Respostas do Nominatim (OpenStreetMap), uma por linha, acrescentadas pelo notebook 06. Dados © colaboradores do OpenStreetMap (licença ODbL).
