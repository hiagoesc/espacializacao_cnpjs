"""Datas da Receita Federal: texto AAAAMMDD vira data de verdade, e colunas de ano e de mês.

A Receita grava as datas como texto de 8 dígitos (ex.: 20240315). Quando não há data, grava 0 ou 00000000.
Aqui essas datas viram datas reais; "sem data" vira vazio (NaT), sem inventar nenhuma data.
"""
import pandas as pd                                  # tabelas e datas


def para_data(serie):
    """Texto AAAAMMDD vira data. Vazio, zeros (0 / 00000000) e datas impossíveis viram vazio (NaT).

    Se a coluna já for de datas, só devolve (assim a função pode ser chamada mais de uma vez).
    """
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie.astype("datetime64[ns]")
    # Tudo como texto limpo: vazio vira "" e espaços nas pontas saem.
    texto = serie.fillna("").astype(str).str.strip()
    # Só vale o texto com exatamente 8 dígitos; o resto vira vazio antes da conversão.
    so_oito_digitos = texto.where(texto.str.fullmatch(r"\d{8}"))
    # errors="coerce": uma data impossível (ex.: 20241345) vira vazio em vez de dar erro.
    return pd.to_datetime(so_oito_digitos, format="%Y%m%d", errors="coerce").astype("datetime64[ns]")


def ano_da_data(serie_data):
    """Ano da data como número inteiro que aceita vazio (Int64)."""
    return serie_data.dt.year.astype("Int64")


def ano_mes_da_data(serie_data):
    """Ano e mês da data como texto 'AAAA-MM' (ordena certo em ordem alfabética). Sem data, fica vazio."""
    texto = serie_data.dt.strftime("%Y-%m").astype(object)
    # Onde não há data, o texto vem como vazio (NaN); deixa explícito como None.
    return texto.where(serie_data.notna(), None)
