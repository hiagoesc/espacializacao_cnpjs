# STATUS — espacializacao_cnpjs
Atualizado em: 2026-11-25

## Objetivo
Dar um ponto no mapa a todo CNPJ de São José dos Campos da base da Receita Federal, com método e confiança registrados, para análises de densidade e zoneamento e para o Monitor de Negócios.

## Estado atual
- Projeto no padrão (manual v1.3): 10 notebooks (01 a 10), `src/`, `config.yaml`, documentação.
- O fluxo 01 a 09 rodou completo com os dados da Receita de novembro de 2026 (322.684 CNPJs, todos com coordenada, sem erros, 1.553 s). A comparação com a versão antiga foi pulada de propósito (a base da Receita mudou).
- **25/11/2026:** rodada do 07 ao 10 com os dados reais concluída e conferida (logs sem erro, todas as conferências "confere"): descrições dos códigos e datas de abertura e encerramento no 08, ajuste ao limite (07), notebook 10 (Excel de aberturas, encerramentos e saldo) e rótulo do Monitor 2026-11. Saldo final 168.576 = 322.684 − 154.108 baixados.
- Decididos na conferência: os 3 CNPJs do endereço a 1.227 m do limite (`-23.006144, -45.903244`) ficam com o ajuste ao ponto mais próximo e a marca de conferência; o motivo de situação 32 (36 CNPJs, ausente do arquivo `MOTICSV`) fica como "(código fora da tabela)".
- **Pastas de dados:** `01_dados_brutos/` a `04_entrega/` não vêm no `git clone` (`.gitignore`). Num computador novo, criar `01_dados_brutos/<fonte>/` e colocar os originais (lista no README); o `02_dados_editados/geocoding_nominatim.jsonl` também não está no Git e precisa de cópia própria.
- Git: em 25/11/2026 o repositório do GitHub (`hiagoesc/espacializacao_cnpjs`) foi apagado e recriado como **público**, com um commit único (sem o histórico antigo). Pastas de dados mantidas por `LEIAME.md` + `.gitignore` (padrão do `espacializacao-rais`). O histórico antigo ficou só na branch local `backup_historico`.

## Última sessão (2026-11-25, descrições, datas e saldo)
- Detalhes em `docs/decisoes.md` (seção de 25/11/2026). Novos módulos: `src/descricoes.py`, `src/datas.py` e `src/saldo.py`; novo notebook `10_exportar_aberturas_encerramentos`.
- Config novo: `parametros.descricoes_receita`, `parametros.legendas_receita`, `parametros.saldo`, `parametros.limite.ajuste_dist_conferir_m` (substitui `ajuste_dist_max_m`) e `entrega.saldo`.

## Sessão anterior (2026-11-24, conversão para o padrão)
- Divisão do notebook único em 9 notebooks; funções em `src/enderecos.py` e `src/cascata.py`; cache em `src/cache.py`.
- Lotes e limite municipal passam a vir de GeoPackages exportados pelo QGIS; cache do geocoding em `02_dados_editados/`.
- Manual atualizado para a v1.2 (detalhes em `docs/decisoes.md`).

## Pendências
- [ ] Validar os limiares da cascata (`parametros.cascata`).
- Descartado em 25/11/2026: rodada 2 pelo endereço do cadastro municipal (teto de 1.129 CNPJs; ver `docs/decisoes.md`); conferência do Monitor de Negócios (não é mais prioridade). Conferidos e fechados: acentos das descrições, `docs/fontes.md` preenchido. Sem necessidade no momento: ver no mapa os 3 CNPJs a 1.227 m do limite.

## Próxima ação
Decidir sobre a validação dos limiares da cascata (`parametros.cascata`).

## Arquivos-chave
- Editados: `02_dados_editados/geocoding_nominatim.jsonl`
- Entrega: `04_entrega/cnpj_espacial.gpkg`, `cnpj_espacial.xlsx`, `cnpjs_monitor.parquet`, `cnpjs_monitor_meta.json`, `aberturas_encerramentos_saldo.xlsx`
