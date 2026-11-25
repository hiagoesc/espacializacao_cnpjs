"""Bloco padrão de validação de tabelas (nulos, duplicados, perda de registros)."""
import logging

import numpy as np                                   # cálculos com números
import pandas as pd                                  # tabelas

log = logging.getLogger("validacao")


def validar_tabela(nome, df, chave=None, obrigatorias=None, linhas_entrada=None):
    """Registra no log: linhas, perda vs. entrada, nulos/vazios nas colunas obrigatórias e duplicados na chave."""
    log.info("Validando %s...", nome)
    log.info("  linhas: %d", len(df))
    if linhas_entrada is not None:
        perda = linhas_entrada - len(df)
        log.info("  perda vs. entrada: %d (%.2f%%)", perda, (perda / linhas_entrada * 100) if linhas_entrada else 0.0)
    for col in (obrigatorias or []):
        vazios = int((df[col].isna() | (df[col].astype(str).str.strip() == "")).sum())
        (log.info if vazios == 0 else log.warning)("  '%s': %d nulos/vazios", col, vazios)
    if chave:
        dup = int(df.duplicated(chave).sum())
        (log.info if dup == 0 else log.warning)("  duplicados na chave %s: %d", chave, dup)
    log.info("Validação de %s concluída!", nome)


def diagnosticar_repeticoes(nome, df, chave, colunas_coordenadas, metros_por_grau=111_320.0, tolerancia_m=0.5, max_exemplos=10):
    """Diz se as linhas de mesma chave também têm a mesma coordenada (repetição inofensiva) ou coordenadas diferentes.

    colunas_coordenadas: (coluna da latitude, coluna da longitude). Distâncias em metros, aproximadas
    (1 grau de latitude ~ 111 km; a longitude é corrigida pelo cosseno da latitude).
    Só gera WARNING quando há chave repetida com coordenadas diferentes.
    """
    log.info("Diagnosticando as chaves repetidas de %s (chave %s)...", nome, chave)
    repetidas = df[df.duplicated(chave, keep=False)]
    if repetidas.empty:
        log.info("  nenhuma chave repetida!")
        return
    col_lat, col_lon = colunas_coordenadas
    tabela = pd.DataFrame({
        "chave": repetidas[chave].to_numpy(),
        "lat": pd.to_numeric(repetidas[col_lat], errors="coerce").to_numpy(),
        "lon": pd.to_numeric(repetidas[col_lon], errors="coerce").to_numpy(),
    })
    grupos = tabela.groupby("chave")
    # Quanto as coordenadas variam dentro de cada chave (maior menos menor), em graus.
    dif_lat = grupos["lat"].max() - grupos["lat"].min()
    dif_lon = grupos["lon"].max() - grupos["lon"].min()
    # Em metros: a longitude encolhe com o cosseno da latitude.
    cos_lat = np.cos(np.radians(grupos["lat"].mean()))
    dist_m = np.hypot(dif_lat * metros_por_grau, dif_lon * metros_por_grau * cos_lat)
    sem_coordenada = dist_m.isna()
    mesma = (dist_m <= tolerancia_m)
    diferente = (dist_m > tolerancia_m)
    log.info("  linhas em chaves repetidas: %d | chaves repetidas: %d", len(repetidas), len(dist_m))
    log.info("  chaves com a MESMA coordenada (repetição inofensiva): %d", int(mesma.sum()))
    (log.info if int(diferente.sum()) == 0 else log.warning)(
        "  chaves com coordenadas DIFERENTES (mais de %.1f m): %d", tolerancia_m, int(diferente.sum()))
    if int(sem_coordenada.sum()):
        log.warning("  chaves repetidas sem coordenada para comparar: %d", int(sem_coordenada.sum()))
    if int(diferente.sum()):
        log.info("  maior distância entre repetidas da mesma chave: %.1f m", float(dist_m.max()))
        for codigo, metros in dist_m[diferente].sort_values(ascending=False).head(max_exemplos).items():
            log.info("    %s: %.1f m", codigo, metros)
    log.info("Diagnóstico de %s concluído!", nome)
