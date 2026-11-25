# Manual do Padrão de Projetos de Análise de Dados

Versão 1.4 — 25/11/2026

Padrão para os projetos de dados urbanos (espacialização de CNPJs, vazios urbanos, RAIS, registro de imóveis, Cadastro Único etc.). Serve para **criar projetos novos** e para **converter projetos existentes**. Inclua este arquivo (e o `docs/handoff/STATUS.md` do projeto) no início de cada conversa com o Claude.

---

## 1. Princípios

1. **Reprodutível:** com os mesmos dados em `01_dados_brutos` e `02_dados_editados`, rodar os scripts em ordem gera sempre o mesmo `03_processamento` e o mesmo `04_entrega`. Dados atualizados entram com o mesmo nome e o processo roda de novo.
2. **Bruto é intocável:** nada grava em `01_dados_brutos`.
3. **Editado tem prioridade:** se existe a versão editada à mão (`02_dados_editados`), ela é usada; senão, gera-se a versão inicial a partir do bruto (uma única vez).
4. **Nada editado à mão é sobrescrito:** antes de qualquer gravação em `02_dados_editados`, cópia datada em `_backup/`.
5. **Processamento é descartável:** `03_processamento` pode ser apagado e regerado a qualquer momento.
6. **Tudo registrado:** cada execução mostra o log na tela **e** grava em arquivo.
7. **Tudo validado:** toda etapa crítica termina com bloco de validação (nulos, duplicados, perda de registros).
8. **Lógica antes do código:** a lógica de cada etapa é confirmada antes de o código ser escrito.

---

## 2. Estrutura de pastas

Todos os projetos ficam em `D:\Users\hiago.cardoso\Documents\projetos_analise_de_dados\<nome_projeto>\`.

```
<nome_projeto>/                      ← raiz = repositório Git
├── README.md                        ← objetivo, fluxo, como rodar
├── config.yaml                      ← caminhos (relativos à raiz) + parâmetros
├── environment.yml                  ← ambiente Anaconda
├── requirements.txt                 ← ambiente Python puro (pip)
├── .gitignore
├── executar_tudo.py                 ← roda os notebooks em ordem
│
├── 01_dados_brutos/                 ← fontes originais (só leitura)            [fora do Git]
│   └── <fonte>/                     ← uma subpasta por fonte: geosanja/, correios/, cnefe/...
├── 02_dados_editados/               ← curadoria manual (nunca sobrescrita)       [fora do Git]
│   └── _backup/                     ← cópias datadas automáticas
├── 03_processamento/                ← intermediários regeneráveis              [fora do Git]
│   ├── 01_<etapa>/ … NN_<etapa>/    ← uma subpasta por notebook, mesmo número
│   ├── notebooks_executados/        ← cópia de cada notebook já rodado (com saídas)
│   └── logs/                        ← AAAA-MM-DD_HHMM_<notebook>.log
├── 04_entrega/                      ← produto final interno (GPKG, Excel, .qgz) [fora do Git]
│
├── scripts/                         ← código (sem número: é o que move os dados entre as pastas)
│   ├── 01_<etapa>.ipynb … NN_<etapa>.ipynb   ← fluxo oficial, na ordem de execução
│   ├── 01_<etapa>.py                          ← variação em script, quando fizer mais sentido
│   ├── exploratorio/                          ← diagnósticos e testes (fora do fluxo)
│   └── src/                                   ← funções comuns (cópia em cada projeto)
│       ├── __init__.py
│       ├── config.py        ← lê config.yaml, acha a raiz, resolve caminhos
│       ├── registro.py      ← logging (tela + arquivo), padrão "..." / "!"
│       ├── validacao.py     ← nulos, duplicados, perda de registros
│       ├── texto.py         ← normalização de nomes (acentos, abreviações, títulos)
│       ├── geo.py           ← tipos compatíveis com GPKG, CRS, distâncias
│       ├── fontes.py        ← leitura com prioridade editado → bruto, backups
│       ├── planilha.py      ← formatação de abas do Excel
│       ├── cache.py         ← cache de leitura de bases pesadas (Parquet + manifesto)
│       └── <modulo_do_projeto>.py             ← funções só deste projeto (não copiar para outros)
│
└── docs/
    ├── manual_padrao_projetos.md    ← cópia deste manual
    ├── fontes.md                    ← origem, data de obtenção e colunas de cada dado bruto
    ├── decisoes.md                  ← decisões de método (regras, limiares), com data
    └── handoff/
        ├── STATUS.md                ← estado atual do projeto
        └── AAAA-MM-DD_<assunto>.md  ← histórico de cada sessão
```

| Pasta | O que guarda | Quem grava | Pode apagar? | Git |
|---|---|---|---|---|
| `01_dados_brutos` | fontes como vieram (download, exportação) | você | não | não |
| `02_dados_editados` | camadas/tabelas corrigidas à mão | você + notebook (só a versão inicial e backups) | não | não |
| `03_processamento` | intermediários, logs, notebooks executados | notebooks | sim | não |
| `04_entrega` | produtos finais | notebooks (+ `.qgz` feito por você) | sim (regerável) | não |
| `scripts` | notebooks, scripts, `src/` | você / Claude | — | **sim** |
| `docs` | manual, fontes, decisões, handoff | você / Claude | — | **sim** |

Um projeto sem curadoria manual mantém `02_dados_editados` vazia; a estrutura é sempre a mesma.

**Pastas de dados no Git:** o Git não guarda pasta vazia. Por isso cada pasta de dados (`01` a `04`) leva um `LEIAME.md` (o que guarda e, na `01`, as subpastas esperadas), e o `.gitignore` ignora o conteúdo mas mantém o LEIAME (`01_dados_brutos/*` + `!01_dados_brutos/LEIAME.md`). Assim a estrutura existe ao clonar, sem dados. Ignorar a pasta inteira (`01_dados_brutos/`) impede a exceção: use `pasta/*`. Num computador novo, crie as subpastas da `01` e coloque os dados originais.

**Fonte em banco de dados** (ex.: PostGIS da Prefeitura): o notebook não conecta no banco. A camada é exportada pelo QGIS (GeoPackage, todas as feições, CRS original) para `01_dados_brutos/<fonte>/`, e a data da exportação vai para `docs/fontes.md`. Para atualizar, exporta-se de novo com o mesmo nome.

---

## 3. Nomes

- **Tudo em minúsculas, sem acento e sem espaço** (`snake_case`): `logradouros_cep.gpkg`, não `Logradouros CEP.gpkg`.
- **Notebooks do fluxo:** `NN_verbo_objeto.ipynb` (`03_base_logradouros_cep.ipynb`). O número é a ordem de execução.
- **Subpasta em `03_processamento`:** mesmo nome do notebook que a gera (`03_processamento/05_classificar_rais_cep/`).
- **Camadas GPKG:** nome da camada = nome do arquivo, quando houver uma só.
- **Backups:** `<nome>_AAAAMMDD_HHMMSS.<ext>` em `_backup/`.
- **Logs:** `AAAA-MM-DD_HHMM_<notebook>.log`.

---

## 4. Fluxo de dados e prioridade editado → bruto

```
01_dados_brutos ──► scripts ──► 03_processamento ──► scripts ──► 04_entrega
                       ▲  │
                       │  └─► 02_dados_editados (versão inicial, só se não existir)
                       └───── 02_dados_editados (você edita; o fluxo lê daqui)
```

Regra (função `fontes.caminho_editado`):

1. Existe o arquivo em `02_dados_editados`? → **usa ele** (log: "usando versão editada").
2. Não existe? → o notebook que gera a versão inicial grava em `02_dados_editados` e o fluxo segue com ela (log: "versão inicial criada a partir do bruto").
3. Notebook que precisa **regravar** algo em `02_dados_editados` (ex.: cache de API) **faz backup antes** em `_backup/` e **preserva** linhas marcadas como manuais.

O caminho de cada arquivo editado e da sua fonte original fica no `config.yaml` (seção `editados`).

### 4.1 Cache de leitura (`src/cache.py`)

Bases pesadas (ex.: os ~20 GB da Receita) são lidas uma vez e gravadas em `03_processamento/<notebook>/` como Parquet + manifesto (`.manifesto.json`). Na rodada seguinte, o notebook só relê o bruto se o cache **não valer**: ele vale quando os dois arquivos existem e são iguais ao momento da gravação os **arquivos de origem** (nome, tamanho e data de modificação), os **parâmetros** do `config.yaml` que afetam a leitura e a **versão da lógica** (`parametros.cache.versao_logica`; some 1 quando mudar o código da leitura). Tabela que depende de outra (ex.: empresas e Simples dependem dos CNPJs do estabelecimento) também é refeita quando a de origem muda.

Avisos:

- **Cache não substitui o bruto.** Os arquivos de `01_dados_brutos` precisam continuar na pasta: sem eles a lista de origem fica vazia, o cache não vale e o notebook tenta reler arquivos que não existem.
- **Mover mantém a data; copiar pode mudar.** Se a data de modificação mudar, o notebook relê uma vez e regrava o cache.
- **Atualizou a fonte?** Troque os arquivos em `01_dados_brutos/<fonte>/`; o cache é descartado sozinho e as tabelas dependentes são refeitas em cadeia.
- **O log diz o motivo:** "Usando o cache" ou "Cache não usado (motivo)", por tabela.
- **Forçar a releitura:** `parametros.cache.forcar_reprocessar` (ex.: `["df_lotes"]` ou `["todos"]`); para limitar a idade, `parametros.cache.idade_maxima_dias`.
- **O cache é regenerável** (fica em `03_processamento`, fora do Git). O que **não** é regenerável (ex.: respostas de API) fica em `02_dados_editados/`, com backup, e não se apaga.

---

## 5. `config.yaml`

Um por projeto, na raiz. Caminhos **relativos à raiz** (nunca `D:\Users\...` no código). Exemplo:

```yaml
projeto:
  nome: espacializacao_rais
  municipio_ibge7: "3549904"
  crs_metrico: "EPSG:31983"      # SIRGAS 2000 / UTM 23S
  crs_graus: "EPSG:4674"         # SIRGAS 2000 (graus)

pastas:                          # padrão; só mude se o projeto for diferente
  brutos: 01_dados_brutos
  editados: 02_dados_editados
  backup: 02_dados_editados/_backup
  processamento: 03_processamento
  logs: 03_processamento/logs
  entrega: 04_entrega

brutos:                          # arquivos de entrada originais
  geosanja:
    arquivo: 01_dados_brutos/geosanja/logradouros.gpkg
    camada: logradouros
  cnefe: 01_dados_brutos/cnefe/3549904_SAO_JOSE_DOS_CAMPOS.csv

editados:                        # arquivos mantidos à mão (prioridade sobre o bruto)
  logradouros_cep:
    arquivo: 02_dados_editados/logradouros_cep.gpkg
    camada: logradouros_cep
    gerado_por: 03_base_logradouros_cep

processamento:                   # intermediários usados por etapas seguintes
  rais_consolidada: 03_processamento/01_consolidar_rais/rais_estab_sjc_consolidado.parquet

entrega:                         # produtos finais
  rais_pontos:
    arquivo: 04_entrega/rais_estab_pontos.gpkg
    camada: rais_pontos

parametros:                      # regras do método, agrupadas por etapa (ver docs/decisoes.md)
  classificacao:                 # 05
    limite_extensao_m: 1000
  pareamento:                    # 02
    limiar_fuzzy: 90

execucao:
  ciclo: ["05", "06"]            # etapas a rodar após uma rodada de correção manual
```

Leitura nos notebooks: `cfg = config.carregar()` (acha a raiz subindo pelas pastas até o `config.yaml`) e depois:

- `cfg.caminho("brutos.geosanja")` → caminho absoluto (aceita texto ou dicionário com `arquivo`);
- `cfg.camada("brutos.geosanja")` → nome da camada do GeoPackage (ou `None`);
- `cfg.parametro("classificacao.limite_extensao_m")` → valor em `parametros` (aceita um valor padrão);
- `cfg.projeto("crs_metrico")` → valor da seção `projeto`;
- `cfg.pasta("logs")` → pasta padrão, criada se não existir;
- `cfg.pasta_etapa("05_classificar_rais_cep")` → subpasta da etapa em `03_processamento`, criada se não existir.

---

## 6. Notebooks

### 6.1 Estrutura padrão de um notebook do fluxo

1. **Cabeçalho (markdown):** objetivo · entradas · saídas · como rodar · estrutura (seções).
2. **Célula de preparação:** importa `src`, carrega o `config.yaml`, inicia o log (tela + arquivo), mostra quais entradas existem.
3. **Seções numeradas:** cada uma com um markdown curto explicando *o quê* e *por quê*, seguido do código.
4. **Validação ao fim de cada etapa crítica** (seção 9).
5. **Resumo final:** números principais, arquivos gerados, avisos.

### 6.2 Regras de código

- **Comentários para leigos**, linha a linha quando possível.
- **Logs de andamento:** início de etapa termina com `...`, fim com `!` (ex.: `Carregando o CNEFE...` / `CNEFE carregado!`). Nada de `print()` solto: usar `log.info` / `log.warning` / `log.error`.
- **Operações vetorizadas** (`pandas`/`geopandas`); evitar `iterrows`. Laços só quando limitados por rede ou sobre poucos valores distintos.
- **Docstring** em toda função.
- **Sem caminho fixo**: tudo via `config.yaml`.
- Parâmetros de método (limiares, CRS, ano de referência) **no `config.yaml`**, não espalhados no código.

### 6.3 Notebook ou script `.py`?

- **Notebook** (padrão): etapas que se beneficiam de ver tabelas, mapas e logs.
- **Script `.py`**: tarefas longas, em lote ou agendadas; mesmo número, mesma estrutura de log e validação.
- **`scripts/exploratorio/`**: diagnósticos, testes e análises pontuais. Sem número, fora do `executar_tudo.py`, nunca são entrada de outra etapa.

### 6.4 `executar_tudo.py`

Roda os notebooks numerados em ordem (via `jupyter nbconvert --execute`), salva cada um já executado em `03_processamento/notebooks_executados/` e para no primeiro erro.

```
python executar_tudo.py                # tudo, do 01 ao último
python executar_tudo.py --de 05        # do 05 em diante
python executar_tudo.py --de 02 --ate 04
python executar_tudo.py --ciclo        # só as etapas de execucao.ciclo do config.yaml
python executar_tudo.py --listar       # só mostra as etapas encontradas
```

---

## 7. `scripts/src/` — funções comuns

Copiado em cada projeto (o repositório é autossuficiente). Ao melhorar uma função num projeto, atualize a cópia nos outros quando for convertê-los.

| Módulo | Funções principais |
|---|---|
| `config.py` | `carregar()` → objeto com `caminho`, `camada`, `parametro`, `projeto`, `pasta`, `pasta_etapa`, `raiz` (seção 5) |
| `registro.py` | `iniciar_log(nome_etapa, cfg)` → logger que escreve na tela e em `03_processamento/logs/`; `formatar_tempo(segundos)` |
| `validacao.py` | `validar_tabela(nome, df, chave, obrigatorias, linhas_entrada)` |
| `texto.py` | `normalizar(serie)`, `tirar_tipo(texto)`, dicionários de abreviações/títulos |
| `geo.py` | `para_gpkg` (tipos compatíveis com GeoPackage), `checar_crs`, `distancia_metros` |
| `fontes.py` | `caminho_editado(cfg, chave, obrigatorio=True)` (usa o editado ou para indicando o notebook que o cria), `existe_editado`, `backup`; `ler_processamento(cfg, chave)` / `gravar_processamento(cfg, chave, df)` (intermediários em Parquet de `processamento.<chave>`; a leitura para indicando o notebook que gera o arquivo) |
| `planilha.py` | `formatar_excel(escritor, aba)` (openpyxl; para planilhas muito grandes, usar o xlsxwriter direto no notebook) |
| `cache.py` | leitura de bases pesadas com cache em `03_processamento`: só relê o bruto quando arquivo de origem, parâmetro ou versão da lógica mudam |

**Módulos só de um projeto** (ex.: `enderecos.py` e `cascata.py` na espacialização de CNPJs) também ficam em `src/`, com nome que não se confunda com os comuns, e **não são copiados** para outros projetos. Se uma função dele passar a servir a vários projetos, ela é levada para o módulo comum correspondente.

---

## 8. Logs

- Cada notebook chama `iniciar_log("<NN_nome>", cfg)` na primeira célula.
- O mesmo texto vai para a tela e para `03_processamento/logs/AAAA-MM-DD_HHMM_<NN_nome>.log`.
- Formato: `HH:MM:SS | NÍVEL | mensagem`.
- `WARNING` = algo a conferir; `ERROR` = resultado não confiável (a etapa deve parar ou avisar claramente).

---

## 9. Validação

Ao fim de cada etapa crítica, `validar_tabela(...)` registra:

- número de linhas e **perda em relação à entrada** (quantidade e %);
- **nulos/vazios** nas colunas obrigatórias;
- **duplicados** na chave;
- conferências de soma quando houver (ex.: vínculos antes = depois).

Resultado inesperado vira `WARNING`/`ERROR` no log; `assert` quando a continuação geraria dado errado (ex.: junção que muda o número de linhas).

---

## 10. Ciclos de correção manual

Projetos com curadoria (ex.: CEPs da base de logradouros) rodam em ciclos:

1. Rodar o fluxo completo uma vez.
2. Ver as pendências (Excel/camada gerados para isso).
3. Corrigir em `02_dados_editados` (QGIS, editor de texto).
4. Rodar só as etapas afetadas: `python executar_tudo.py --ciclo` (ou `--de NN`).
5. Conferir o resumo; repetir.

Nunca rodar de novo o notebook que **cria a versão inicial** de um editado esperando que ele “atualize”: ele não sobrescreve (por desenho).

---

## 11. Entrega

- Formatos usuais: **GPKG** (camadas), **Excel** (tabelas, listas de pendências), **`.qgz`** (projeto QGIS com estilos e camadas virtuais/consultas SQL).
- O `.qgz` fica em `04_entrega/` e usa **caminhos relativos** (Projeto → Propriedades → Geral → Salvar caminhos: relativos), para continuar funcionando se a pasta mudar de lugar.
- A entrega é **interna da Prefeitura** e pode conter os dados completos.

---

## 12. Ambiente

- `environment.yml` (Anaconda) e `requirements.txt` (pip) com as mesmas bibliotecas.
- Criar: `conda env create -f environment.yml` **ou** `pip install -r requirements.txt`.
- Pacotes base: `pandas`, `geopandas`, `pyogrio`, `shapely`, `pyarrow`, `openpyxl`, `pyyaml`, `rapidfuzz`, `requests`, `jupyter`, `nbconvert`.

---

## 13. Git

Vai para o Git: `scripts/`, `docs/`, `README.md`, `config.yaml`, `environment.yml`, `requirements.txt`, `.gitignore`, `executar_tudo.py`.
**Nunca:** dados (`01`–`04`, exceto o `LEIAME.md` de cada pasta), entregas, logs, notebooks executados.

`.gitignore` padrão:

```
01_dados_brutos/*
02_dados_editados/*
03_processamento/*
04_entrega/*
!01_dados_brutos/LEIAME.md
!02_dados_editados/LEIAME.md
!03_processamento/LEIAME.md
!04_entrega/LEIAME.md
*.gpkg
*.gpkg-wal
*.gpkg-shm
*.parquet
*.xlsx
*.xls
*.csv
*.qgz
*.qgs
*.zip
*.7z
*.COMT
*.txt
!requirements.txt
.ipynb_checkpoints/
__pycache__/
*.pyc
.env
.idea/
~$*
```

**Notebooks no Git sem saídas** (limpar as saídas antes do commit: *Kernel → Restart & Clear Output*), para não vazar dado em tabela impressa.

---

## 14. Dados sensíveis

- Cadastro Único, registro de imóveis e similares têm **dados pessoais**: nunca no Git, nunca em log que vá para o Git, nunca colados em conversa fora do necessário.
- Para conversas com o Claude: enviar **estrutura** (nomes de colunas, contagens, amostras sem identificação), não registros identificados.
- A entrega interna pode conter os dados completos.

---

## 15. Documentação

- **`README.md`:** objetivo, fontes (resumo), fluxo (tabela de notebooks: nº, nome, entradas, saídas), como rodar, ciclo de correção, onde está a entrega.
- **`docs/fontes.md`:** para cada dado bruto: origem/URL, data de obtenção, formato, CRS, colunas usadas.
- **`docs/decisoes.md`:** decisões de método com data e motivo (ex.: “limiar fuzzy 90: abaixo disso surgiam pares errados”).

---

## 16. Handoff entre sessões

Cada projeto é tocado em várias conversas. O handoff garante que a próxima comece de onde a anterior parou.

- **`docs/handoff/STATUS.md`** — sempre atualizado; é o que se anexa no início de uma conversa nova.
- **`docs/handoff/AAAA-MM-DD_<assunto>.md`** — registro de cada sessão (opcional, para histórico).
- **Quando atualizar:** ao fim de cada sessão de trabalho, ou quando pedir “gere o handoff”.

Modelo de `STATUS.md`:

```markdown
# STATUS — <nome do projeto>
Atualizado em: AAAA-MM-DD

## Objetivo
<uma ou duas frases>

## Estado atual
- Etapas prontas: 01–06 (rodadas em AAAA-MM-DD)
- Números principais: <ex.: 85,6% dos vínculos espacializados (2025)>

## Última sessão
- O que foi feito
- O que foi decidido (detalhe em docs/decisoes.md)

## Pendências
- [ ] <pendência> — <por que / quem>

## Próxima ação
<uma ação concreta>

## Arquivos-chave
- Editados: 02_dados_editados/<...>
- Entrega: 04_entrega/<...>
```

**Início de uma conversa nova:** anexar `manual_padrao_projetos.md` + `STATUS.md` (+ o log ou arquivo do que se quer tratar).

---

## 17. Converter um projeto existente

1. Criar a estrutura de pastas (seção 2) numa pasta nova.
2. Mover os dados originais para `01_dados_brutos/<fonte>/`.
3. Mover o que foi editado à mão para `02_dados_editados/`.
4. Inventariar os notebooks/scripts: quais fazem parte do fluxo, quais são exploratórios (`scripts/exploratorio/`), quais estão obsoletos (descartar).
5. Renumerar o fluxo na ordem real de execução; desfazer dependências circulares.
6. Trocar caminhos fixos pelo `config.yaml`; trocar funções repetidas por `src/`.
7. Ajustar saídas: intermediários em `03_processamento/NN_<etapa>/`, produto final em `04_entrega/`.
8. Rodar `executar_tudo.py` e comparar os números com a versão antiga (devem bater).
9. Escrever `README.md`, `docs/fontes.md`, `docs/decisoes.md`, `docs/handoff/STATUS.md`.
10. `git init`, conferir o `.gitignore`, primeiro commit.

## 18. Checklist de projeto novo

- [ ] Estrutura de pastas criada
- [ ] `LEIAME.md` em cada pasta de dados (na `01`, com a lista das subpastas) e `.gitignore` com a exceção `!pasta/LEIAME.md`
- [ ] `config.yaml` com caminhos e parâmetros
- [ ] `scripts/src/` copiado do projeto mais recente
- [ ] `environment.yml` e `requirements.txt`
- [ ] `.gitignore` padrão
- [ ] `docs/fontes.md` preenchido ao baixar cada dado
- [ ] `docs/handoff/STATUS.md` criado
- [ ] Cada notebook: cabeçalho, log em arquivo, validação, resumo
