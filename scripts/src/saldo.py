"""Aberturas, encerramentos e saldo (estabelecimentos abertos) por mês e por ano.

Definições (confirmadas com o usuário):
- abertura: data de início da atividade do estabelecimento;
- encerramento: data da situação, só para os estabelecimentos Baixados;
- saldo: quantos estabelecimentos permanecem abertos no FIM do período = abertos até a data
  (em qualquer ano) menos baixados até a data. Estabelecimentos suspensos, inaptos ou nulos contam como abertos.
Para o último período (o mês ou o ano ainda em andamento), o "fim" é a data da base (última data com registro).
"""
import pandas as pd                                  # tabelas e datas

ROTULO_ABERTURAS = "Aberturas"
ROTULO_ENCERRAMENTOS = "Encerramentos"
ROTULO_SALDO = "Saldo (estabelecimentos abertos no fim do período)"


def _rotulo(periodo, frequencia):
    """Texto do cabeçalho de um período: '03/2024' para mês, '2024' para ano."""
    if frequencia == "M":
        return f"{periodo.month:02d}/{periodo.year}"
    return str(periodo.year)


def tabela_por_periodo(abertura, encerramento, data_base, frequencia, ano_inicial=None):
    """Monta a tabela de um tipo de período (frequencia 'M' = mês, 'Y' = ano).

    Linhas: aberturas, encerramentos e saldo. Colunas: um período cada, do mais antigo ao mais novo.
    O último período leva no cabeçalho a data da base (ex.: '2026 (até 15/11/2026)').
    O saldo é calculado com TODA a história (inclusive antes de ano_inicial), que só limita as colunas mostradas.
    """
    data_base = pd.Timestamp(data_base)
    if not abertura.index.equals(encerramento.index):
        raise ValueError("abertura e encerramento precisam ter a mesma numeração de linhas (um estabelecimento por linha).")
    aberturas_validas = abertura.dropna()
    encerramentos_validos = encerramento.dropna()
    # Para o SALDO, um encerramento só conta a partir da abertura do mesmo estabelecimento:
    # - encerramento anterior à abertura (data com erro) vale como se fosse na data da abertura;
    # - estabelecimento sem data de abertura não entra no saldo (não dá para saber desde quando existe).
    encerramento_no_saldo = encerramento.where(~(encerramento < abertura), abertura).where(abertura.notna()).dropna()
    if (aberturas_validas > data_base).any() or (encerramentos_validos > data_base).any():
        raise ValueError("Há datas depois da data da base: a data da base precisa ser a maior data dos registros.")

    # Do primeiro registro até o período da data da base, sem pular nenhum período (os vazios contam zero).
    primeira = min(aberturas_validas.min(), encerramentos_validos.min() if len(encerramentos_validos) else data_base)
    periodos = pd.period_range(primeira.to_period(frequencia), data_base.to_period(frequencia), freq=frequencia)

    # Quantos registros caem em cada período.
    aberturas = aberturas_validas.dt.to_period(frequencia).value_counts().reindex(periodos, fill_value=0)
    encerramentos = encerramentos_validos.dt.to_period(frequencia).value_counts().reindex(periodos, fill_value=0)
    fechados_no_saldo = encerramento_no_saldo.dt.to_period(frequencia).value_counts().reindex(periodos, fill_value=0)
    # Saldo no fim de cada período: tudo que abriu até ali menos tudo que fechou até ali.
    saldo = aberturas.cumsum() - fechados_no_saldo.cumsum()

    # Só mostra os períodos a partir do ano inicial, se ele foi pedido.
    mostrar = pd.Series(True, index=periodos) if ano_inicial is None else pd.Series(periodos.year >= ano_inicial, index=periodos)
    rotulos = [_rotulo(p, frequencia) for p in periodos]
    rotulos[-1] = f"{rotulos[-1]} (até {data_base:%d/%m/%Y})"

    tabela = pd.DataFrame([aberturas.to_numpy(), encerramentos.to_numpy(), saldo.to_numpy()],
                          index=[ROTULO_ABERTURAS, ROTULO_ENCERRAMENTOS, ROTULO_SALDO], columns=rotulos)
    return tabela.loc[:, mostrar.to_numpy()].astype("int64")
